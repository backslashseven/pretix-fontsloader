import os

from django.conf import settings
from django.dispatch import receiver
from pretix.presale.style import register_fonts

from .apps import STATIC_PREFIX, get_font_directory
from .scanner import scan_fonts


@receiver(register_fonts, dispatch_uid="fontsloader_fonts")
def fontsloader_fonts(sender, **kwargs):
    directory = os.path.abspath(get_font_directory())
    if not os.path.isdir(directory):
        return {}
    return scan_fonts(directory, STATIC_PREFIX, check_manifest=not settings.DEBUG)
