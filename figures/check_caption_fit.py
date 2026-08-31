"""Fail if a figure's caption has one line much longer than its siblings.

    python figures/check_caption_fit.py

Captions here are hand-wrapped with explicit newlines, and figures are saved
with ``bbox_inches="tight"``. That combination hides a mistake: an overlong
line is not clipped and does not wrap — the canvas simply grows to fit it, so
the PNG comes out far wider than the plot with one caption line stretching
across the extra space. It looks deliberate at a glance and is only obvious
next to the figure's predecessor.

This happened twice in one sitting, once from a re-wrapped caption and once
from a batch of rewritten titles. Both times the give-away was the same: one
line 1.5 to 2 times the length of the rest of the block.

So the check is on the text, not the render — for every multi-line caption,
compare the longest line against the block's median line. Uneven wrapping is
the defect; the absolute width is a house-style choice and is left alone.
"""

from __future__ import annotations

import importlib
import re
import statistics
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import _network as NET  # noqa: E402
import _style as S  # noqa: E402

# A caption line may run this much longer than its block's median before the
# wrapping counts as uneven. Set from the set's own spread: the well-wrapped
# captions sit under 1.25 and both regressions came in above 1.6.
TOLERANCE = 1.45
# Below this a "line" is a fragment — a trailing clause or a short last line —
# and comparing it to anything is noise.
MIN_LINE = 45

findings: list[tuple[str, str, int, int, str]] = []


def blocks(fig) -> list[str]:
    out = []
    for ax in fig.axes:
        for attr in ("title", "_left_title", "_right_title"):
            artist = getattr(ax, attr, None)
            if artist is not None and artist.get_text().strip():
                out.append(artist.get_text())
        out.extend(t.get_text() for t in ax.texts if t.get_text().strip())
    out.extend(t.get_text() for t in fig.texts if t.get_text().strip())
    return out


def inspect(fig, slug, table=None, **kwargs) -> None:
    for block in blocks(fig):
        lines = [ln.strip() for ln in block.split("\n") if len(ln.strip()) >= MIN_LINE]
        if len(lines) < 3:
            continue
        lengths = [len(ln) for ln in lines]
        median = statistics.median(lengths)
        longest = max(lines, key=len)
        if median and len(longest) > median * TOLERANCE:
            findings.append((slug, longest, len(longest), int(median), block[:40]))


def main() -> int:
    S.save = inspect
    NET.S.save = inspect
    for path in sorted(HERE.glob("fig*.py")):
        module = importlib.import_module(path.stem)
        if hasattr(module, "main"):
            module.main()
        else:
            # The committee networks are thin wrappers that call NET.draw at
            # import guard level rather than defining main().
            call = re.search(r"NET\.draw\((.*?)\n\s*\)", path.read_text(), re.S)
            exec(f"NET.draw({call.group(1)})", {"NET": NET})  # noqa: S102
        plt.close("all")

    if not findings:
        print(f"caption wrapping is even in all {len(list(HERE.glob('fig*.py')))} figures")
        return 0
    print(f"{len(findings)} caption block(s) wrap unevenly "
          f"(longest line more than {TOLERANCE:g}× the block median):\n")
    for slug, longest, n, median, head in findings:
        print(f"  {slug}\n    median line {median}, this one {n}: {longest[:100]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
