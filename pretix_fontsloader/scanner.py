import logging
import os
import threading

logger = logging.getLogger(__name__)

FONT_EXTENSIONS = (".ttf", ".otf")
WEB_EXTENSIONS = (("woff2", ".woff2"), ("woff", ".woff"))

# TTFontFile.flags as computed by reportlab (PDF font descriptor flags)
FLAG_ITALIC = 1 << 6
FLAG_FORCE_BOLD = 1 << 18

STYLES = ("regular", "bold", "italic", "bolditalic")
# Which existing cuts to fall back to, in order, when a family lacks a cut
FALLBACKS = {
    "regular": ("bold", "italic", "bolditalic"),
    "bold": ("regular", "bolditalic", "italic"),
    "italic": ("regular", "bolditalic", "bold"),
    "bolditalic": ("bold", "italic", "regular"),
}

_cache = {}
_lock = threading.Lock()


def _decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _style_slot(font):
    style_name = _decode(font.styleName or "").lower()
    bold = bool(font.flags & FLAG_FORCE_BOLD) or "bold" in style_name
    italic = bool(font.flags & FLAG_ITALIC) or font.italicAngle != 0 \
        or "italic" in style_name or "oblique" in style_name
    if bold and italic:
        return "bolditalic"
    if bold:
        return "bold"
    if italic:
        return "italic"
    return "regular"


def _in_manifest(path):
    from django.contrib.staticfiles.storage import staticfiles_storage

    if not hasattr(staticfiles_storage, "stored_name"):
        # Not a manifest storage, static() works for any file
        return True
    try:
        staticfiles_storage.stored_name(path)
        return True
    except ValueError:
        return False


def _skip(report, path, message, *args):
    logger.warning("Skipping font file %s: " + message, path, *args)
    report.append((os.path.basename(path), "skipped: " + message % args))


def _scan(directory, prefix, check_manifest, report=None):
    """
    ``report``, if given, is filled with a ``(file name, result)`` tuple per font file.
    """
    from reportlab.pdfbase.ttfonts import TTFontFile

    if report is None:
        report = []
    entries = {e.name: e for e in os.scandir(directory) if e.is_file()}
    families = {}

    for name in sorted(entries):
        stem, ext = os.path.splitext(name)
        if ext.lower() not in FONT_EXTENSIONS:
            continue
        path = entries[name].path
        try:
            font = TTFontFile(path)
        except Exception as e:
            _skip(
                report, path, "%s (only TrueType-outline fonts are supported; "
                "convert CFF-based .otf files to .ttf, e.g. with fontTools' otf2ttf)", e
            )
            continue

        static_path = "{}/{}".format(prefix, name)
        if check_manifest and not _in_manifest(static_path):
            _skip(
                report, path, "not collected into static files yet, "
                "run 'python -m pretix rebuild' (or collectstatic) and restart"
            )
            continue

        family = _decode(font.familyName).strip()
        slot = _style_slot(font)
        styles = families.setdefault(family, {})
        if slot in styles:
            _skip(report, path, "family '%s' already has a %s cut (%s)", family, slot, styles[slot]["truetype"])
            continue

        formats = {"truetype": static_path}
        for fmt, web_ext in WEB_EXTENSIONS:
            for candidate in (stem + web_ext, stem + web_ext.upper()):
                if candidate in entries and (not check_manifest or _in_manifest("{}/{}".format(prefix, candidate))):
                    formats[fmt] = "{}/{}".format(prefix, candidate)
                    break
        styles[slot] = formats

        result = "{} / {}".format(family, slot)
        if "fvar" in font.table:
            # reportlab ignores variation axes and always uses the default instance
            logger.warning(
                "Font file %s is a variable font, only its default instance '%s' is used; "
                "prefer static font files", path, family
            )
            result += " (variable font: only the default instance is used, prefer static font files)"
        report.append((name, result))

    # pretix requires every family to have a regular cut and uses the others if present;
    # fill missing cuts from the closest available one like hand-written font packs do
    result = {}
    for family, styles in families.items():
        complete = {}
        for style in STYLES:
            if style in styles:
                complete[style] = styles[style]
            else:
                source = next(s for s in FALLBACKS[style] if s in styles)
                complete[style] = styles[source]
        result[family] = complete
    return result


def scan_fonts(directory, prefix, check_manifest=False):
    """
    Returns all usable fonts in ``directory`` in the format expected by
    ``pretix.presale.style.register_fonts``, with paths relative to the static root
    under ``prefix``.

    The directory is scanned once per process on purpose: pretix registers fonts with
    reportlab only once per process, so a font picked up later would show up in the
    layout editor but break PDF rendering. Adding fonts requires a restart.
    """
    key = (directory, prefix, check_manifest)
    with _lock:
        if key not in _cache:
            _cache[key] = _scan(directory, prefix, check_manifest)
        return _cache[key]
