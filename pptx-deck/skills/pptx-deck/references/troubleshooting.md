# Tool traps

Each of these cost real time in a real session. None of them is obvious from the
error message.

## Shell

**zsh aborts a command chain on an unmatched glob.** `rm -f build/*.png && next-step`
dies with `no matches found` and `next-step` never runs. The `-f` does not help,
because the shell fails before `rm` is called. Use
`find DIR -maxdepth 1 -name '*.png' -delete`.

**One generation per tool call.** A single Bash call that loops several image
generations through a shell function gets refused. Issue them one at a time.

**Credential handling is blocked, correctly.** Fetching a key over password SSH is
refused. Ask the user to run the one command themselves with a `!` prefix, and look
locally first: a key may already sit in the environment or in a provider file.

## Rendering

**LibreOffice substitutes a missing font silently.** Copy the deck's font into
`/Applications/LibreOffice.app/Contents/Resources/fonts/truetype` before the first
render, or every line break you check is fiction.

**A bold with no Bold file is drawn by stroking the Regular.** The widths stay the
Regular's, so `check_layout.py` and `fix_orphans.py` measure that bold with the
Regular file. For a fixed-pitch family that is exact everywhere. For a proportional
one it matches this render only, and they say so with a WARN, because a machine
with the real Bold sets it up to about 7 percent wider. Install the Bold to clear it.

**Hidden slides shift the page index.** `render_real.py` renders hidden slides, so
there page N is slide N. Any export that leaves them out, `--skip-hidden`, PowerPoint
or a plain `soffice --convert-to pdf`, has fewer pages than slides, so page N is not
slide N. Print the map. Exporting hidden slides from the command line needs
LibreOffice 7.4 or newer, and Ubuntu 22.04 and Debian 11 ship older ones. On those,
`render_real.py` warns that the hidden slides were left out and falls back to the
map.

**Which LibreOffice renders is printed, and you can choose it.** `render_real.py`
prints the `soffice` it used, and `preflight.py` shows it. The search takes
`$PPTX_DECK_SOFFICE` or `$SOFFICE` first, then PATH, then the usual install
locations, then `/opt/libreoffice*` and `~/.local/opt/libreoffice*`, newest
version first. On a machine where an old distro `/usr/bin/soffice` is too old
for hidden slides, put a newer one first on PATH or name it in the variable.

**A render older than the deck is not evidence.** Check mtimes before reporting.
A stale PNG showing a title that no longer exists has been reviewed as current.

**PowerPoint holds the file while it is open.** A `~$deck.pptx` in the folder means
an open handle. If the user cannot save, or your extraction is missing their last
edit, compare the file mtime against PowerPoint's autorecover copy under
`~/Library/Containers/com.microsoft.Powerpoint/.../AutoRecovery/`. If autorecover is
newer, their work is not on disk yet.

## Images

**A free tier can report quota `limit: 0`.** That means the model is not available
on that tier at all, not that you should wait. Retrying burns about 90 seconds per
attempt and never succeeds. Test one cheap generation before planning a set.

**Trimming changes the aspect ratio.** Anything placed by height must be recomputed
after a trim, or its caption lands on the block below. Keep originals in their own
folder and always trim from them, so the step is idempotent.

## Icons

**Lucide lives at `lucide-icons/lucide`.** The obvious guess, `lucide/lucide`,
returns nothing and a bare `curl` writes an empty file. Simple Icons is on the
`develop` branch. Treat a download under 50 bytes as a failure.

**Lucide's default `stroke-width="2"` reads heavy** next to body text at small
sizes. Drop it to about 1.6 when recolouring.

## LaTeX

**BasicTeX has no `standalone.cls`.** Use `article` with `\pagestyle{empty}` and a
wide `\textwidth`, then trim on the alpha channel.

**`pdflatex` is not on PATH on macOS.** It is at `/Library/TeX/texbin/pdflatex`.

## python-pptx

**Autoshapes inherit theme fill and a shadow.** Remove the `p:style` element and set
`shadow.inherit = False`, or the deck quietly grows an accent colour it does not
have.

**There is no API for highlight runs.** Write the `a:highlight` element yourself,
and put it before `a:latin` in the run properties or PowerPoint drops it.

**Row heights are a request, not a fact.** A cell that wraps one line further makes
PowerPoint grow the row, and everything below the table moves.

**A digit inside an oval does not centre the same way in LibreOffice and
PowerPoint.** Rasterise numbered markers as PNGs and place them as pictures.
