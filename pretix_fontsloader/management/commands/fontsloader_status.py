import os

from django.conf import settings
from django.core.management.base import BaseCommand

from ... import __version__, scanner
from ...apps import STATIC_PREFIX, get_font_directory
from ...signals import fontsloader_fonts


class Command(BaseCommand):
    help = "Show which fonts pretix-fontsloader loads, and why files are skipped"

    def handle(self, *args, **options):
        directory = os.path.abspath(get_font_directory())
        exists = os.path.isdir(directory)
        registered = any(
            isinstance(d, (tuple, list)) and d[0] == STATIC_PREFIX and os.path.abspath(d[1]) == directory
            for d in settings.STATICFILES_DIRS
        )
        check_manifest = not settings.DEBUG

        self.stdout.write("pretix-fontsloader {}".format(__version__))
        self.stdout.write("Directory:        {} ({})".format(directory, "exists" if exists else "MISSING"))
        self.stdout.write("Static files dir: {}".format("registered" if registered else "NOT registered"))
        self.stdout.write("Mode:             {}".format(
            "production, fonts must be collected with 'pretix rebuild'" if check_manifest else "debug"
        ))
        if not exists:
            self.stdout.write(self.style.ERROR("No fonts are loaded, the directory does not exist in this environment."))
            return
        if not registered:
            self.stdout.write(self.style.ERROR(
                "The directory was created after pretix started, restart pretix (and rebuild static files)."
            ))

        self.stdout.write("")
        self.stdout.write("Files:")
        report = []
        scanner.logger.disabled = True
        try:
            scanner._scan(directory, STATIC_PREFIX, check_manifest, report)
        finally:
            scanner.logger.disabled = False
        if not report:
            self.stdout.write("  (no .ttf or .otf files)")
        for name, result in report:
            style = self.style.WARNING if result.startswith("skipped") or "variable" in result else self.style.SUCCESS
            self.stdout.write("  {}: {}".format(name, style(result)))

        self.stdout.write("")
        self.stdout.write("Fonts available in PDF layouts:")
        fonts = fontsloader_fonts(sender=None)
        if not fonts:
            self.stdout.write(self.style.ERROR("  none"))
        for family, styles in sorted(fonts.items()):
            cuts = ", ".join("{}={}".format(s, os.path.basename(f["truetype"])) for s, f in styles.items())
            self.stdout.write("  {}: {}".format(family, cuts))
