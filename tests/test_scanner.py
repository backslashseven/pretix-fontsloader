import os
import shutil

import pretix
import pytest

from pretix_fontsloader import scanner
from pretix_fontsloader.scanner import scan_fonts

OPEN_SANS = os.path.join(os.path.dirname(pretix.__file__), "static", "fonts")
PREFIX = "pretix_fontsloader/fonts"


def add(directory, *names):
    for name in names:
        shutil.copy(os.path.join(OPEN_SANS, name), os.path.join(directory, name))


@pytest.fixture(autouse=True)
def clear_cache():
    scanner._cache.clear()


def test_groups_family_by_metadata(tmp_path):
    add(tmp_path, "OpenSans-Regular.ttf", "OpenSans-Bold.ttf", "OpenSans-Italic.ttf", "OpenSans-BoldItalic.ttf")
    fonts = scan_fonts(str(tmp_path), PREFIX)
    assert fonts == {
        "Open Sans": {
            "regular": {"truetype": PREFIX + "/OpenSans-Regular.ttf"},
            "bold": {"truetype": PREFIX + "/OpenSans-Bold.ttf"},
            "italic": {"truetype": PREFIX + "/OpenSans-Italic.ttf"},
            "bolditalic": {"truetype": PREFIX + "/OpenSans-BoldItalic.ttf"},
        }
    }


def test_style_detection_ignores_file_name(tmp_path):
    shutil.copy(os.path.join(OPEN_SANS, "OpenSans-Bold.ttf"), tmp_path / "whatever.ttf")
    fonts = scan_fonts(str(tmp_path), PREFIX)
    assert fonts["Open Sans"]["bold"] == {"truetype": PREFIX + "/whatever.ttf"}


def test_missing_cuts_fall_back(tmp_path):
    add(tmp_path, "OpenSans-Regular.ttf")
    styles = scan_fonts(str(tmp_path), PREFIX)["Open Sans"]
    assert all(styles[s] == {"truetype": PREFIX + "/OpenSans-Regular.ttf"} for s in scanner.STYLES)


def test_missing_regular_is_filled(tmp_path):
    add(tmp_path, "OpenSans-Bold.ttf", "OpenSans-Italic.ttf")
    styles = scan_fonts(str(tmp_path), PREFIX)["Open Sans"]
    assert styles["regular"]["truetype"] == PREFIX + "/OpenSans-Bold.ttf"
    assert styles["bolditalic"]["truetype"] == PREFIX + "/OpenSans-Bold.ttf"
    assert styles["italic"]["truetype"] == PREFIX + "/OpenSans-Italic.ttf"


def test_web_formats_attached(tmp_path):
    add(tmp_path, "OpenSans-Regular.ttf")
    (tmp_path / "OpenSans-Regular.woff2").write_bytes(b"x")
    styles = scan_fonts(str(tmp_path), PREFIX)["Open Sans"]
    assert styles["regular"] == {
        "truetype": PREFIX + "/OpenSans-Regular.ttf",
        "woff2": PREFIX + "/OpenSans-Regular.woff2",
    }


def test_unsupported_files_skipped(tmp_path, caplog):
    add(tmp_path, "OpenSans-Regular.ttf")
    # CFF-flavoured OpenType starts with "OTTO", which reportlab can't embed
    (tmp_path / "Postscript.otf").write_bytes(b"OTTO" + b"\0" * 64)
    (tmp_path / "broken.ttf").write_bytes(b"not a font")
    (tmp_path / "readme.txt").write_text("hi")
    fonts = scan_fonts(str(tmp_path), PREFIX)
    assert list(fonts) == ["Open Sans"]
    assert "Postscript.otf" in caplog.text
    assert "broken.ttf" in caplog.text


def test_duplicate_cut_first_wins(tmp_path, caplog):
    add(tmp_path, "OpenSans-Regular.ttf")
    shutil.copy(os.path.join(OPEN_SANS, "OpenSans-Regular.ttf"), tmp_path / "ZZ.ttf")
    fonts = scan_fonts(str(tmp_path), PREFIX)
    assert fonts["Open Sans"]["regular"]["truetype"] == PREFIX + "/OpenSans-Regular.ttf"
    assert "ZZ.ttf" in caplog.text


def test_scanned_once_per_process(tmp_path):
    # pretix registers fonts with reportlab once per process, so later additions
    # must not show up before a restart
    add(tmp_path, "OpenSans-Regular.ttf")
    first = scan_fonts(str(tmp_path), PREFIX)
    add(tmp_path, "OpenSans-Bold.ttf")
    assert scan_fonts(str(tmp_path), PREFIX) is first
    assert first["Open Sans"]["bold"]["truetype"] == PREFIX + "/OpenSans-Regular.ttf"


def test_manifest_check_skips_uncollected(tmp_path, monkeypatch, caplog):
    add(tmp_path, "OpenSans-Regular.ttf", "OpenSans-Bold.ttf")
    monkeypatch.setattr(scanner, "_in_manifest", lambda path: path.endswith("Regular.ttf"))
    styles = scan_fonts(str(tmp_path), PREFIX, check_manifest=True)["Open Sans"]
    assert styles["bold"]["truetype"] == PREFIX + "/OpenSans-Regular.ttf"
    assert "rebuild" in caplog.text
