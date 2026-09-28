pretix-fontsloader
==================

A pretix plugin that makes every font file dropped into a folder available for PDF
ticket and badge layouts, without writing a font pack.

Family name and style (regular / bold / italic / bold italic) are read from the font
file itself, so file names don't matter. Missing cuts are filled in from the closest
existing one (e.g. a family with only a Regular file uses it for all four styles).

The plugin is not visible in the event plugin list; installing it activates it globally.

Installation
------------

.. code-block:: bash

    pip install -e .    # or pip install pretix-fontsloader

Configuration
-------------

By default fonts are loaded from ``<pretix data dir>/fonts``. To use another folder,
set it in ``pretix.cfg``:

.. code-block:: ini

    [pretix_fontsloader]
    directory = /var/pretix/fonts

The folder must exist when pretix starts. It is added to Django's static files under
the prefix ``pretix_fontsloader/fonts``.

Supported files
---------------

* ``.ttf`` and ``.otf`` files with **TrueType outlines**.
* ``.otf`` files with PostScript/CFF outlines can't be embedded in PDFs by reportlab and are
  skipped with a warning in the log. Convert them first, e.g. with fontTools::

      pip install fonttools
      fonttools otf2ttf MyFont.otf

* Optionally, put a ``.woff2`` / ``.woff`` file with the same name next to a font file.
  It is then also used for the preview in the layout editor.

Files that can't be read, and duplicate cuts of the same family, are skipped with a
warning in the log.

Adding fonts
------------

Development (``runserver``, ``DEBUG`` on):

1. Copy the font file into the folder.
2. Restart the server.

Production:

1. Copy the font file into the folder.
2. Run ``python -m pretix rebuild`` (or ``python -m pretix collectstatic --noinput``).
3. Restart pretix (web and worker processes).

Why the restart? pretix registers fonts with the PDF engine only once per process.
Until the files are collected into the static files, the plugin leaves them out
(with a warning in the log); otherwise the layout editor and settings pages would fail.

Docker (``pretix/standalone``)
------------------------------

The standalone image runs ``collectstatic`` only while the image is built
(``make production``), and not when the container starts. Fonts in a mounted folder
would never be collected, so bake them into the image before ``make production``:

.. code-block:: dockerfile

    FROM pretix/standalone:stable
    USER root
    RUN DJANGO_SETTINGS_MODULE= pip3 install git+https://github.com/backslashseven/pretix-fontsloader.git
    COPY fonts/ /pretix/fonts/
    ENV PRETIX_PRETIX_FONTSLOADER_DIRECTORY=/pretix/fonts
    USER pretixuser
    RUN cd /pretix/src && make production

The environment variable takes precedence over ``pretix.cfg`` and applies both while
building and at runtime. To add a font, put it into ``fonts/`` and rebuild the image.

Checking the setup
------------------

The plugin is intentionally not listed in the event plugin settings, since it applies to
all events. To see what it is doing, run:

.. code-block:: bash

    python -m pretix fontsloader_status          # plain installation
    docker exec <container> pretix fontsloader_status

It shows the font directory in use, every font file with the family and style it was
recognized as (or why it was skipped), and the fonts available in PDF layouts.

Variable fonts (e.g. ``*-VariableFont_wght.ttf``) are loaded, but only their default
instance is used, which is often the thinnest weight. Use the static font files instead
(Google Fonts downloads contain them in the ``static/`` folder).
