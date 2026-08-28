"""Render every figure, in order.

    python figures/make_all.py            # all figures
    python figures/make_all.py 11 12      # only figures 11 and 12
    FIGURES_PDF=1 python figures/make_all.py    # also write PDFs
    FIGURES_DARK=1 python figures/make_all.py   # dark-surface variants

Each figure is a standalone script, so this only discovers and runs them. It
executes each in a subprocess rather than importing them: a figure that fails
should not take the rest of the set with it, and matplotlib state should not leak
between figures.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def scripts(selection: list[str]) -> list[Path]:
    found = sorted(HERE.glob("fig*.py"))
    if not selection:
        return found
    wanted = {s.zfill(2) for s in selection}
    return [p for p in found
            if (m := re.match(r"fig(\d+)", p.name)) and m.group(1).zfill(2) in wanted]


def main() -> int:
    selected = scripts(sys.argv[1:])
    if not selected:
        print("no figure scripts matched", file=sys.stderr)
        return 1

    failures: list[tuple[str, str]] = []
    started = time.monotonic()
    for path in selected:
        print(f"→ {path.name}", file=sys.stderr)
        result = subprocess.run(
            [sys.executable, str(path)], capture_output=True, text=True
        )
        sys.stderr.write(result.stderr)
        if result.returncode != 0:
            failures.append((path.name, result.stderr.strip().splitlines()[-1]
                             if result.stderr.strip() else "unknown error"))

    elapsed = time.monotonic() - started
    print(f"\n{len(selected) - len(failures)}/{len(selected)} figures rendered "
          f"in {elapsed:.1f}s", file=sys.stderr)
    for name, message in failures:
        print(f"  FAILED {name}: {message}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
