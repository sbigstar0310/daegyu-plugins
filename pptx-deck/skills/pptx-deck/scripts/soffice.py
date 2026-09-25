# -*- coding: utf-8 -*-
"""Find LibreOffice's soffice, for render_real.py and preflight.py alike.

The order, first hit wins:

  1. $PPTX_DECK_SOFFICE, then $SOFFICE: what the user named. A set variable that
     names no executable is an error, never a reason to look elsewhere.
  2. PATH: soffice, then libreoffice. Ahead of the fixed paths, so a newer build the
     user put first beats an old distro /usr/bin/soffice.
  3. The usual install locations.
  4. The versioned installs: the official Linux packages in /opt, and a .deb
     extracted under ~/.local/opt with no root. The newest version wins.

Standard library only: preflight.py imports this to report that PIL or python-pptx
is missing, so it must import without them.
"""
import glob
import os
import re
import shutil

VARIABLES = ("PPTX_DECK_SOFFICE", "SOFFICE")

DEFAULT_FIXED = [
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "~/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/usr/bin/soffice", "/usr/local/bin/soffice", "/snap/bin/libreoffice",
]
DEFAULT_GLOBS = [
    "/opt/libreoffice*/program/soffice",
    "~/.local/opt/libreoffice*/**/program/soffice",
]
# Module level so a test can empty them.
FIXED = list(DEFAULT_FIXED)
GLOBS = list(DEFAULT_GLOBS)

INSTALL = ("    brew install --cask libreoffice        # macOS\n"
           "    sudo apt-get install -y libreoffice    # Debian or Ubuntu\n")


class NotFound(Exception):
    """The message says where the search looked, or which variable is wrong."""


def _runnable(path):
    return os.path.isfile(path) and os.access(path, os.X_OK)


def _version(path):
    """(26, 2) for .../libreoffice26.2/program/soffice. The last versioned directory
    counts, since an extracted .deb nests one inside a plain "libreoffice"."""
    found = re.findall(r"libreoffice(\d+(?:\.\d+)*)", path)
    return tuple(int(x) for x in found[-1].split(".")) if found else ()


def locate():
    """The path of soffice, or NotFound with a message for the user."""
    for var in VARIABLES:
        named = os.environ.get(var)
        if not named:
            continue
        if _runnable(named):
            return named
        raise NotFound(
            "%s is set to %s, which is not an executable file.\n"
            "Point it at LibreOffice's program/soffice, or unset it to search the\n"
            "usual places.\n" % (var, named))
    on_path = shutil.which("soffice") or shutil.which("libreoffice")
    if on_path:
        return on_path
    for p in FIXED:
        p = os.path.expanduser(p)
        if _runnable(p):
            return p
    for pattern in GLOBS:
        hits = [p for p in glob.glob(os.path.expanduser(pattern), recursive=True)
                if _runnable(p)]
        if hits:
            return max(hits, key=_version)
    tried = ["$%s" % v for v in VARIABLES] + ["PATH (soffice, libreoffice)"] + FIXED + GLOBS
    raise NotFound(
        "LibreOffice (soffice) was not found. Looked in:\n%s"
        "If it is installed somewhere else, point at it:\n"
        "    export PPTX_DECK_SOFFICE=/path/to/program/soffice\n"
        "If it is not, install it:\n%s"
        % ("".join("    %s\n" % t for t in tried), INSTALL))


def find_soffice():
    """The path of soffice, or None. explain() says why it is None."""
    try:
        return locate()
    except NotFound:
        return None


def explain():
    """The message for a failed find_soffice(), or None if it succeeds."""
    try:
        locate()
    except NotFound as e:
        return str(e)
    return None
