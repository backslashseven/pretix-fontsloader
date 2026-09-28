import logging
import os

from django.apps import AppConfig
from django.conf import settings

from . import __version__

logger = logging.getLogger(__name__)

# Static path prefix under which files from the font directory are served
STATIC_PREFIX = "pretix_fontsloader/fonts"


def get_font_directory():
    return settings.CONFIG_FILE.get(
        "pretix_fontsloader", "directory",
        fallback=os.path.join(settings.DATA_DIR, "fonts"),
    )


def add_static_dir(directory):
    # pretix resolves font paths through the staticfiles finders (PDF rendering)
    # and static() (layout editor), so the font directory has to be a static dir.
    # FileSystemFinder reads STATICFILES_DIRS on first use, which is after ready().
    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        logger.warning(
            "Fonts directory %s does not exist, no fonts will be loaded. Set it with "
            "[pretix_fontsloader] directory in pretix.cfg or PRETIX_PRETIX_FONTSLOADER_DIRECTORY.",
            directory,
        )
        return False
    settings.STATICFILES_DIRS = list(settings.STATICFILES_DIRS) + [(STATIC_PREFIX, directory)]
    logger.info("Loading fonts from %s", directory)
    return True


class PluginApp(AppConfig):
    name = "pretix_fontsloader"
    verbose_name = "Fonts loader"

    class PretixPluginMeta:
        name = "Fonts loader"
        author = "Zwischenraum"
        description = "Makes fonts dropped into a folder available for PDF layouts"
        visible = False
        version = __version__
        compatibility = "pretix>=4.16.0"

    def ready(self):
        add_static_dir(get_font_directory())

        from . import signals  # NOQA
