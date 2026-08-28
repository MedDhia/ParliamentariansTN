"""Shared figure infrastructure: palette, chart chrome, and output contract.

Every figure script imports from here so the whole set reads as one system. Three
things are worth knowing before writing a new figure.

**The palette is validated, not chosen by eye.** The categorical slots below are
a documented, colour-vision-deficiency-tested order. Two rules follow from the
validation and are enforced by :func:`categorical`:

* forms where any two marks can end up adjacent — scatter plots, network node
  colours, choropleths — are capped at **three** slots. Past three, fold the tail
  into "Other" or facet. (With all pairs in play the fourth slot puts yellow
  beside orange, which fails the separation floor.)
* forms where only neighbouring marks touch — stacked bars and areas, grouped
  bars, lines — may use up to eight, and direct labels become mandatory at four.

Three light-mode slots sit below 3:1 contrast against the surface. The
documented relief for that is visible labels *or* a table view; this module
ships both — every figure writes a companion CSV.

**Every figure emits a table.** :func:`save` writes ``figNN_name.png`` and
``figNN_name.csv`` side by side. The CSV is the accessible twin of the chart and,
for a research repository, the thing a reader actually needs in order to check a
claim or re-plot it. A figure that cannot state its own numbers as a table is
usually a figure that has not decided what it is about.

**Arabic is never rendered.** Matplotlib draws Arabic unshaped and
left-to-right, which is not a rendering of Arabic so much as a corruption of it.
Rather than ship that, :func:`label` refuses to pass Arabic through and raises,
so a missing gloss fails the build instead of appearing as broken text. The
Arabic strings stay authoritative in the data; the glosses in ``_labels.py`` are
display-only.
"""

from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(parents=True, exist_ok=True)

DARK = os.environ.get("FIGURES_DARK", "").lower() in {"1", "true", "yes"}
WANT_PDF = os.environ.get("FIGURES_PDF", "").lower() in {"1", "true", "yes"}

# ---------------------------------------------------------------------------
# Palette (see the dataviz reference palette; both modes are selected, not
# flipped — the dark column is the same eight hues re-stepped for a dark surface)
# ---------------------------------------------------------------------------

_CATEGORICAL_LIGHT = (
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 green
    "#4a3aa7",  # 7 violet
    "#e34948",  # 8 red
)
_CATEGORICAL_DARK = (
    "#3987e5", "#d95926", "#199e70", "#c98500",
    "#d55181", "#008300", "#9085e9", "#e66767",
)

# Sequential: one hue, light -> dark. Ordinal use starts no lighter than step 250
# on light / no darker than step 600 on dark, so the lightest mark still reads.
_SEQ_BLUE = (
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
    "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
    "#184f95", "#104281", "#0d366b",
)
_ORDINAL_LIGHT_FLOOR = 3   # index of step 250
_ORDINAL_DARK_CEIL = 10    # index of step 600

CHROME = {
    "surface": "#1a1a19" if DARK else "#fcfcfb",
    "text_primary": "#ffffff" if DARK else "#0b0b0b",
    "text_secondary": "#c3c2b7" if DARK else "#52514e",
    "muted": "#898781",
    "grid": "#2c2c2a" if DARK else "#e1e0d9",
    "axis": "#383835" if DARK else "#c3c2b7",
    # de-emphasis fill for the "rest" in an emphasis chart, and for "no data"
    "deemph": "#4a4a47" if DARK else "#d7d6cf",
}

CATEGORICAL = _CATEGORICAL_DARK if DARK else _CATEGORICAL_LIGHT

# Forms where any two marks may sit side by side are capped at three slots.
ALL_PAIRS_CAP = 3
ADJACENT_CAP = 8


def categorical(n: int, all_pairs: bool = False) -> list[str]:
    """Return the first ``n`` categorical slots, in fixed order.

    ``all_pairs=True`` for scatter, network node colour, choropleth and small
    multiples — anything where non-neighbouring categories can end up adjacent.
    Raises rather than cycling or generating a hue, because a generated ninth
    colour is indistinguishable from an existing slot under CVD.
    """
    cap = ALL_PAIRS_CAP if all_pairs else ADJACENT_CAP
    if n > cap:
        raise ValueError(
            f"{n} categorical series requested but the cap is {cap} for this form. "
            "Fold the tail into 'Other', facet into small multiples, or encode with "
            "hue x shape — never generate another hue."
        )
    return list(CATEGORICAL[:n])


def sequential(n: int, ordinal: bool = False) -> list[str]:
    """``n`` steps of the single-hue blue ramp, light -> dark.

    ``ordinal=True`` for discrete ordered marks (periods, tiers): the step
    nearest the surface is held back so the lightest mark still clears contrast.
    """
    if n < 1:
        return []
    steps = _SEQ_BLUE
    if ordinal:
        steps = steps[:_ORDINAL_DARK_CEIL] if DARK else steps[_ORDINAL_LIGHT_FLOOR:]
        if DARK:
            steps = tuple(reversed(steps))
    if n == 1:
        return [steps[len(steps) // 2]]
    idx = [round(i * (len(steps) - 1) / (n - 1)) for i in range(n)]
    return [steps[i] for i in idx]


# ---------------------------------------------------------------------------
# Chart chrome
# ---------------------------------------------------------------------------

def apply_rc() -> None:
    """Thin marks, hairline recessive grid, generous padding, one sans face."""
    plt.rcParams.update({
        "figure.facecolor": CHROME["surface"],
        "axes.facecolor": CHROME["surface"],
        "savefig.facecolor": CHROME["surface"],
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica", "sans-serif"],
        "font.size": 9,
        "axes.titlesize": 11.5,
        "axes.titleweight": "bold",
        "axes.titlepad": 10,
        "axes.labelsize": 9,
        "axes.labelcolor": CHROME["text_secondary"],
        "axes.edgecolor": CHROME["axis"],
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": CHROME["grid"],
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",          # never dashed: dashing reads as threshold
        "axes.axisbelow": True,
        "xtick.color": CHROME["muted"],
        "ytick.color": CHROME["muted"],
        "xtick.labelcolor": CHROME["text_secondary"],
        "ytick.labelcolor": CHROME["text_secondary"],
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "legend.frameon": False,
        "legend.fontsize": 8,
        "legend.handlelength": 1.1,
        "legend.handleheight": 1.1,
        "lines.linewidth": 2.0,         # 2px lines
        "lines.markersize": 5,
        "text.color": CHROME["text_primary"],
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.28,
    })


apply_rc()


def frame(ax: plt.Axes, x_grid: bool = False, y_grid: bool = True) -> None:
    """Strip the box down to what carries information."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(CHROME["axis"])
    ax.grid(axis="y", visible=y_grid)
    ax.grid(axis="x", visible=x_grid)
    ax.set_axisbelow(True)


_SUBTITLE_LINE_PT = 11.0
_SUBTITLE_GAP_PT = 7.0


def titles(ax: plt.Axes, title: str, subtitle: str = "", ylabel: str = "",
           xlabel: str = "") -> None:
    """Title in primary ink, subtitle beneath it in secondary.

    The subtitle is where n, coverage and caveats live, so it is part of the
    chart rather than a caption someone may not carry with the image.

    The title's pad is computed from the subtitle's line count so the two never
    overlap: matplotlib anchors the axes title just above the axes, so a subtitle
    placed at a *larger* offset would sit on top of it.
    """
    lines = subtitle.count("\n") + 1 if subtitle else 0
    pad = 10 + (lines * _SUBTITLE_LINE_PT + _SUBTITLE_GAP_PT if subtitle else 0)
    ax.set_title(title, loc="left", color=CHROME["text_primary"], pad=pad)
    if subtitle:
        ax.annotate(
            subtitle, xy=(0, 1), xycoords="axes fraction",
            xytext=(0, _SUBTITLE_GAP_PT), textcoords="offset points",
            ha="left", va="bottom", fontsize=8.2, color=CHROME["text_secondary"],
            linespacing=1.35,
        )
    if ylabel:
        ax.set_ylabel(ylabel)
    if xlabel:
        ax.set_xlabel(xlabel)


def source_note(fig: plt.Figure, text: str, y: float = 0.002) -> None:
    """Provenance line. Pass a negative ``y`` to clear a legend placed below the axes."""
    fig.text(
        0.005, y, text, ha="left", va="bottom",
        fontsize=7.2, color=CHROME["muted"],
    )


def integer_axis(ax: plt.Axes, axis: str = "y") -> None:
    getattr(ax, f"{axis}axis").set_major_locator(MaxNLocator(integer=True))


# ---------------------------------------------------------------------------
# Arabic guard
# ---------------------------------------------------------------------------

_ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")


def has_arabic(text: str) -> bool:
    return bool(_ARABIC.search(str(text)))


def label(text: str, context: str = "") -> str:
    """Gate every string that will be drawn.

    Matplotlib has no Arabic shaping or bidi, so Arabic would be drawn as
    disconnected letters in reversed order. That is worse than an error, because
    it looks like a rendering rather than a bug. Missing glosses therefore fail
    the build.
    """
    text = str(text)
    if has_arabic(text):
        raise ValueError(
            f"refusing to render Arabic text in a figure: {text!r}"
            + (f" (context: {context})" if context else "")
            + ". Add a display gloss in figures/_labels.py — matplotlib cannot "
              "shape Arabic, so it would render as broken glyphs."
        )
    return text


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------

def load(name: str) -> list[dict[str, str]]:
    """Load a processed or derived table by bare name."""
    for sub in ("processed", "networks", "reference"):
        path = DATA / sub / f"{name}.csv"
        if path.exists():
            with path.open(encoding="utf-8-sig", newline="") as fh:
                return list(csv.DictReader(fh))
    raise FileNotFoundError(f"no table named {name!r} under {DATA}")


def assemblies_in_order() -> list[dict[str, str]]:
    """Chamber-terms in chronological order.

    Falls back to ``end_date`` for the Chamber of Advisors, whose first sitting
    is not established: sorting an empty start to the end of the sequence would
    put a 2005-2011 chamber after the sitting one.
    """
    rows = load("assemblies")
    return sorted(rows, key=lambda r: r.get("start_date") or r.get("end_date") or "9999")


def num(value: str, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------

def save(fig: plt.Figure, slug: str, table: Sequence[Mapping[str, Any]] | None = None,
         columns: Sequence[str] | None = None) -> None:
    """Write the figure and its companion table.

    The CSV is not optional decoration: it is the table view that discharges the
    contrast relief rule, and it is how a reader checks the chart against the
    data without re-deriving it.
    """
    suffix = "_dark" if DARK else ""
    png = OUT / f"{slug}{suffix}.png"
    fig.savefig(png)
    if WANT_PDF:
        fig.savefig(OUT / f"{slug}{suffix}.pdf")
    plt.close(fig)

    if table:
        cols = list(columns) if columns else list(table[0].keys())
        csv_path = OUT / f"{slug}.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore",
                                    lineterminator="\n")
            writer.writeheader()
            for row in table:
                writer.writerow(row)
        print(f"  wrote {png.name} + {csv_path.name}", file=sys.stderr)
    else:
        print(f"  wrote {png.name}", file=sys.stderr)


def fold_to_other(counts: Mapping[str, float], keep: int,
                  other_label: str = "Other") -> list[tuple[str, float]]:
    """Keep the ``keep`` largest categories, sum the rest into one bucket.

    This is the sanctioned answer to "too many series" — never another hue.
    """
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    head = ordered[:keep]
    tail = ordered[keep:]
    if tail:
        head.append((other_label, sum(v for _, v in tail)))
    return head


def figsize(width: float = 7.4, height: float = 4.4) -> tuple[float, float]:
    return (width, height)
