"""Figure 14 — Committee co-membership network, 2011 Constituent Assembly.

Two deputies are tied when they sat on the same committee at overlapping times.
The 2011 chamber is the densest of the three (density 0.21), which is itself
informative: it ran two parallel committee systems — six constituent committees
drafting the constitution and a set of legislative committees for ordinary
business — so members accumulated more shared assignments than in a normal term.

Read the structure with the endogeneity in mind: blocs negotiate committee seats,
so a committee tie is partly a bloc tie by construction. Any claim that committee
co-service *causes* something needs to control for co-bloc membership.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _network as NET  # noqa: E402

if __name__ == "__main__":
    NET.draw(
        "NCA-2011",
        "fig14_committee_network_nca2011",
        "Committee co-membership: 2011 Constituent Assembly",
        note="This chamber ran constituent and legislative committees in parallel.",
    )
