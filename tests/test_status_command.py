import os
import shutil
from io import StringIO

import pretix
from django.core.management import call_command

from pretix_fontsloader import scanner
from pretix_fontsloader.management.commands import fontsloader_status

OPEN_SANS = os.path.join(os.path.dirname(pretix.__file__), "static", "fonts")


def run(monkeypatch, directory):
    scanner._cache.clear()
    monkeypatch.setattr(fontsloader_status, "get_font_directory", lambda: directory)
    monkeypatch.setattr("pretix_fontsloader.signals.get_font_directory", lambda: directory)
    out = StringIO()
    call_command("fontsloader_status", stdout=out)
    return out.getvalue()


def test_status_missing_directory(tmp_path, monkeypatch):
    out = run(monkeypatch, str(tmp_path / "nope"))
    assert "MISSING" in out
    assert "No fonts are loaded" in out


def test_status_lists_fonts(tmp_path, monkeypatch, settings):
    shutil.copy(os.path.join(OPEN_SANS, "OpenSans-Regular.ttf"), tmp_path / "OpenSans-Regular.ttf")
    (tmp_path / "broken.ttf").write_bytes(b"not a font")
    settings.STATICFILES_DIRS = list(settings.STATICFILES_DIRS) + [("pretix_fontsloader/fonts", str(tmp_path))]
    out = run(monkeypatch, str(tmp_path))
    assert "(exists)" in out
    assert "Static files dir: registered" in out
    assert "OpenSans-Regular.ttf: Open Sans / regular" in out
    assert "broken.ttf: skipped:" in out
    assert "Open Sans: regular=OpenSans-Regular.ttf" in out
