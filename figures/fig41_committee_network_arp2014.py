"""Figure 41 — Committee co-membership network, 2014–2019 chamber.

The fourth panel of figures 14–16, and the one that was missing until this
chamber's committee pages were recovered from the Internet Archive. It completes
the committee panel across the whole democratic period, which the mandate panel
already spanned.

**Read this graph more sceptically than the other three.** Two properties of the
source make its ties weaker evidence of co-work than they look:

* **The tie unions the whole term.** 985 memberships spread across 23 committees
  and 231 members means a committee has, on average, 43 distinct members over
  five years — roughly double its size at any one moment. Membership churned
  hard in this chamber, and a co-membership tie joins anyone who sat on the same
  committee at overlapping *recorded* times, which after that much churn is a
  looser relation than in a chamber whose committees held still.
* **Most of the dates are bracketed.** 803 of the 985 spells have boundaries
  falling in a gap between web captures rather than on a published date, and the
  recorded span is the outer bound. Bracketing can only ever *add* overlap, so
  some of these ties join people who were never on the committee together.

Both push density up, and density is 0.449 here against 0.138–0.214 in the other
three chambers. Do not read that as this chamber being unusually collegial; read
it as a coarser instrument.

**What survives the caveat is the finding the panel exists for.** Bloc
assortativity is −0.015: committee assignment does not track bloc lines, the same
negative result as 2011 (−0.03), 2019 (−0.04) and 2023 (−0.07). And it survives
in the hardest case — the chamber whose governing coalition fragmented, where 108
of 246 members changed bloc mid-term. If committee seats were being traded along
bloc lines anywhere in this dataset, this is the chamber where it would show.

**The shape differs from the other three in a way worth naming.** Radius is the
number of committees a deputy sits on, so the node mass here is pulled hard
toward the centre: 219 of 231 deputies bridge committees, at an average of 4.3
each, against 151 of 194 at 2.3 each in 2011. Almost nobody in this chamber sat
on one committee only. Whether that is a chamber that spread its members thin or
an artefact of unioning five years of churn into one graph, this figure cannot
separate — but the direction is the same either way.

Only ties of weight ≥ 4 are drawn, where figures 14–16 draw weight ≥ 2. At the
usual threshold this graph puts 4,296 lines through 231 nodes and the centre
renders as solid ink; 344 is the same order as figure 14's 382, so the panels
stay comparable as *drawings*. Density and assortativity are still computed over
all 11,940 ties, and the companion CSV carries every one of them.

Colour is bloc — the member's last recorded bloc, since many held several —
position is committee portfolio, exactly as in figures 14–16, so the four panels
are directly comparable.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _network as NET  # noqa: E402

if __name__ == "__main__":
    NET.draw(
        "ARP-2014",
        "fig41_committee_network_arp2014",
        "Nearly every deputy bridges committees; bloc explains none",
        note=("Recovered from web captures: most spells are bracketed, so ties "
              "are over- rather than under-counted."),
        # Figures 14-16 draw every tie of weight >= 2, which for them is a few
        # hundred lines. Here it is 4,296 over 231 deputies and the centre
        # renders as solid black. Weight >= 4 draws 344 — the same order as
        # figure 14's 382, so the four panels stay comparable as drawings.
        # Density and assortativity in the subtitle are still computed over all
        # 11,940 ties, and the CSV carries every one of them.
        min_weight=4,
    )
