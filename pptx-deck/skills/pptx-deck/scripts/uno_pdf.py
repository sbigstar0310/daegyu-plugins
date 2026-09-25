#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export a deck to PDF through LibreOffice's UNO API with Asian/Western autospace
off, and find a python that can run that export.

    <python> scripts/uno_pdf.py <soffice> deck.pptx out.pdf [--hidden]

render_real.py runs this with the python find_python() returns, because only a
python LibreOffice ships or packages can import uno.

LibreOffice widens every gap between Hangul and Latin text (tdf#159934). No other
renderer does, and no profile setting turns it off, so ParaIsCharacterDistance is
cleared on every paragraph before export. Nothing else differs from the command
line export: the same impress_pdf_Export filter, and hidden slides only with
--hidden. A throwaway profile keeps it from handing the job to a LibreOffice the
user has open.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time


def find_python(soffice):
    """A python that can import uno: LibreOffice's own, or the system python3 where
    a distribution packages uno for it (Debian's python3-uno). None if none can."""
    program = os.path.dirname(os.path.realpath(soffice))
    for cand in (os.path.join(program, "python"),                                 # Linux, Windows
                 os.path.join(os.path.dirname(program), "Resources", "python"),   # macOS bundle
                 shutil.which("python3")):
        if cand and os.path.isfile(cand) and subprocess.run(
                [cand, "-c", "import uno"], capture_output=True).returncode == 0:
            return cand
    return None


def paragraphs(shape):
    if shape.supportsService("com.sun.star.drawing.GroupShape"):
        for i in range(shape.getCount()):
            for p in paragraphs(shape.getByIndex(i)):
                yield p
        return
    if shape.supportsService("com.sun.star.drawing.TableShape"):
        model = shape.Model
        for r in range(model.Rows.Count):
            for c in range(model.Columns.Count):
                enum = model.getCellByPosition(c, r).Text.createEnumeration()
                while enum.hasMoreElements():
                    yield enum.nextElement()
        return
    if getattr(shape, "Text", None) is not None:
        enum = shape.Text.createEnumeration()
        while enum.hasMoreElements():
            yield enum.nextElement()


def export(soffice, src, dst, hidden):
    """Returns how many paragraphs had autospace on."""
    import uno
    from com.sun.star.beans import PropertyValue

    def prop(name, value):
        p = PropertyValue()
        p.Name, p.Value = name, value
        return p

    profile = tempfile.mkdtemp(prefix="uno-pdf-")
    pipe = "uno_pdf_%d" % os.getpid()
    proc = subprocess.Popen([soffice, "--headless", "--invisible", "--norestore",
                             "-env:UserInstallation=" + uno.systemPathToFileUrl(profile),
                             "--accept=pipe,name=%s;urp;" % pipe])
    try:
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local)
        for _ in range(120):
            try:
                ctx = resolver.resolve("uno:pipe,name=%s;urp;StarOffice.ComponentContext" % pipe)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("LibreOffice did not answer on its pipe within 60 s")
        desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
        doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(os.path.abspath(src)),
                                           "_blank", 0, (prop("Hidden", True),))
        if doc is None:
            raise RuntimeError("LibreOffice could not load %s" % src)
        changed = 0
        for pages in (doc.DrawPages, doc.MasterPages):
            for i in range(pages.Count):
                page = pages.getByIndex(i)
                for j in range(page.Count):
                    for para in paragraphs(page.getByIndex(j)):
                        if para.ParaIsCharacterDistance:
                            para.ParaIsCharacterDistance = False
                            changed += 1
        args = [prop("FilterName", "impress_pdf_Export")]
        if hidden:
            args.append(prop("FilterData", uno.Any("[]com.sun.star.beans.PropertyValue",
                                                   (prop("ExportHiddenSlides", True),))))
        uno.invoke(doc, "storeToURL", (uno.systemPathToFileUrl(os.path.abspath(dst)), tuple(args)))
        doc.close(True)
        try:
            desktop.terminate()
        except Exception:  # the bridge drops as LibreOffice exits
            pass
        proc.wait(timeout=30)
        return changed
    finally:
        if proc.poll() is None:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    print("autospace off in %d paragraphs" % export(a[0], a[1], a[2], "--hidden" in a[3:]))
