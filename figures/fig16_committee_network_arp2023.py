"""Figure 16 — Committee co-membership network, chamber elected in 2023.

The sitting chamber, and the one elected under the Third Republic's rules: 161
single-member districts, candidates standing as individuals rather than on party
lists. The blocs in this graph formed *inside* parliament after the election, not
before it, which is a different object from the party blocs of 2011–2019 even
though the schema treats them alike.

This is also the sparsest of the three networks, with fewer committees and a
smaller chamber.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _network as NET  # noqa: E402

if __name__ == "__main__":
    NET.draw(
        "ARP-2023",
        "fig16_committee_network_arp2023",
        "The sparsest committee network, and bloc explains none of it",
        note="Blocs here formed inside parliament, not at the election.",
    )
