import os
import shutil

import pretix
from django.contrib.staticfiles import finders

from pretix.presale.style import get_fonts

from pretix_fontsloader import scanner, signals
from pretix_fontsloader.apps import add_static_dir

OPEN_SANS = os.path.join(os.path.dirname(pretix.__file__), "static", "fonts")


def test_fonts_registered_via_signal(tmp_path, monkeypatch):
    scanner._cache.clear()
    shutil.copy(os.path.join(OPEN_SANS, "OpenSans-Regular.ttf"), tmp_path / "Dropped.ttf")
    monkeypatch.setattr(signals, "get_font_directory", lambda: str(tmp_path))
    fonts = get_fonts(pdf_support_required=True)
    assert fonts["Open Sans"]["regular"]["truetype"] == "pretix_fontsloader/fonts/Dropped.ttf"


def test_missing_directory_registers_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(signals, "get_font_directory", lambda: str(tmp_path / "nope"))
    assert signals.fontsloader_fonts(sender=None) == {}


def test_directory_resolvable_by_finders(tmp_path, settings):
    shutil.copy(os.path.join(OPEN_SANS, "OpenSans-Regular.ttf"), tmp_path / "Dropped.ttf")
    # assign through the fixture so the change is reverted after the test
    settings.STATICFILES_DIRS = list(settings.STATICFILES_DIRS)
    add_static_dir(str(tmp_path))
    finders.get_finder.cache_clear()
    try:
        assert finders.find("pretix_fontsloader/fonts/Dropped.ttf") == str(tmp_path / "Dropped.ttf")
    finally:
        finders.get_finder.cache_clear()
