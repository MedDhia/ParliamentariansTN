"""Figure 15 — Committee co-membership network, 2019–2021 chamber.

The chamber frozen by presidential decree in July 2021. Committee memberships
here carry published joining and leaving dates, so every tie in this graph is
date-verified: two deputies are linked only if their committee spells actually
overlapped, not merely because both served in the term.

Compare the shape with figure 14. This chamber is less dense and visibly more
clustered — nine blocs, no bloc close to a majority, and committee assignments
that track that fragmentation.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _network as NET  # noqa: E402

if __name__ == "__main__":
    NET.draw(
        "ARP-2019",
        "fig15_committee_network_arp2019",
        "Committee co-membership: 2019–2021 chamber",
        note="Every tie is date-verified from published committee spells.",
    )
