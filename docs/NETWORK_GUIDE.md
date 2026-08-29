# Network analysis guide

The relational tables in `data/processed` are the dataset. The files in
`data/networks` are a convenience layer built from them by
`python -m parliamentarians_tn.networks`. This guide explains what each layer
means substantively, what the projection choices are, and where the traps are.

## Files

| File | Shape | Rows | What a tie means |
| --- | --- | --- | --- |
| `nodes.csv` | node attributes | 856 | one parliamentarian |
| `bipartite_person_committee.csv` | incidence | 1,129 | this person sat on this committee |
| `bipartite_person_bloc.csv` | incidence | 1,116 | this person belonged to this bloc |
| `edges_committee_comembership.csv` | projection | 8,687 | co-served on a committee, same chamber, overlapping in time |
| `edges_bloc_comembership.csv` | projection | 20,805 | belonged to the same bloc, same chamber |
| `edges_shared_constituency.csv` | projection | 2,978 | returned by the same constituency, same chamber |
| `edges_shared_organisation.csv` | projection | 37 | passed through the same outside organisation (any period) |
| `edges_question_cosignature.csv` | projection | 1,663 | co-signed a written question (ARP-2023) |
| `edges_amendment_cosponsorship.csv` | projection | 9,361 | co-sponsored a constitutional amendment (NCA-2011) |
| `edges_vote_agreement.csv` | weighted dyads | 23,337 | share of contested divisions voted the same way (NCA-2011) |

## Start from the bipartite files

The projections are provided because they are useful immediately, but every
projection destroys information and embeds someone else's weighting decision. If
your argument depends on tie strength, build your own projection from the
incidence files. `igraph` and `networkx` both do this in one call, and you keep
control of the weighting.

## Three rules the projections follow

**1. Edges never cross chambers.** Two deputies on the finance committee in 2011
and 2023 respectively did not co-serve. Every projection is computed within a
chamber-term and carries `assembly_id`. Pooling across chambers is a decision
you make explicitly, by ignoring that column.

The one deliberate exception is `edges_shared_organisation`, where
`assembly_id` is empty: sharing a trade union or a ministry twenty years apart is
precisely the tie that elite-circulation arguments are about, so this layer is
cross-temporal by design.

**2. Spells must overlap in time.** Where both memberships carry dates, an edge
exists only if the intervals intersect — someone who left a committee in 2020
never sat with someone who joined in 2021. Where a source publishes no dates,
membership is assumed to span the chamber and the edge is flagged
`dates_assumed=true`. Filter on that column if the assumption matters:

```r
edges <- subset(edges, dates_assumed == "false")
```

For committee co-membership all 8,687 edges are date-verified. For bloc
co-membership most are not, because the 2011 and 2019 sources publish
end-of-term snapshots rather than histories.

**3. Group size is recorded, not hidden.** A 53-member bloc generates 1,378
dyads on its own and will dominate any unweighted centrality measure — Ennahdha's
2019 bloc alone accounts for a large share of `edges_bloc_comembership`. Each
edge therefore carries:

- `weight` — number of shared groups (the naive count);
- `weight_newman` — the same, corrected by 1/(n−1) per group, so a tie formed
  inside a small committee counts for more than one formed inside a large bloc;
- `group_size` — the size of each group that produced the tie.

Use `weight_newman` for centrality unless you have a reason not to. If you use
`weight`, say so, because in this dataset the two give materially different
rankings.

## What each layer supports, and what it does not

**Committee co-membership** is the workhorse. It is date-verified, it covers
three chambers (NCA-2011, ARP-2019, ARP-2023) — not ARP-2014, whose committee
pages were not recovered from the Archive — and committee assignment is
plausibly consequential for legislative behaviour. It is also partly endogenous
to bloc: blocs negotiate committee seats, so committee ties and bloc ties are
correlated by construction. Control for co-bloc membership before claiming a
committee effect.

**Bloc co-membership** is dense and near-block-diagonal — it is close to a
partition, not a network. It is most useful as a *covariate* (are these two in
the same bloc?) rather than as an object of analysis.

For *defection*, the picture is now uneven in a way worth knowing precisely.
Switching is observable for **ARP-2014** (108 of 246 members changed bloc,
reconstructed by diffing monthly web captures) and for **ARP-2023** (44 members,
from dates the chamber publishes itself). It is *not* observable for NCA-2011 or
ARP-2019, whose sources publish a single end-of-term snapshot — so a zero there
means "not measured", not "did not happen". Filter ARP-2014 spells on
`dates_bracketed` if exact timing matters: those boundaries are located to the
interval between two captures, not to the day.

**Shared constituency** exists only where districts are multi-member. Under the
2011-2019 list system a constituency returned several deputies; the 2023 chamber
is single-member, so **this layer is empty for ARP-2023 by construction, not by
omission**. Do not read that as a finding.

**Shared organisation** is the elite-circulation layer and the thinnest one: 37
edges, built from career rows extracted from narrative biographies by rule. An
organisation matched on a normalised name string may be two different bodies.
Filter on `careers.confidence` and treat this layer as a lead for hand-coding
rather than as evidence. It is the layer most worth investing in.

**Question co-signature** is a behavioural relational layer, and it exists for
ARP-2023 only, from 6,332 written questions of which 78 were jointly signed.
Weights run up to 15. Note the group-size problem is acute here: some questions
carry 20+ signatories, so `weight_newman` matters more than usual.

**Amendment co-sponsorship** is its NCA-2011 counterpart and the larger of the
two: 9,361 ties from 251 constitutional amendments. Same group-size caution — an
amendment carrying 58 sponsors manufactures 1,653 dyads on its own.

**Vote agreement is different in kind from every other layer here, and mixing it
in with them will produce nonsense.** Three differences matter:

- **It is revealed, not assigned or chosen.** A committee seat is given to a
  member and a co-sponsorship is an act they perform; an agreement tie exists
  because two voting records correlate, whether or not either member knew or
  intended it. Two opponents who both back an uncontroversial motion are "tied"
  in exactly the sense two allies are. Do not read it as cooperation.
- **It is near-complete, not sparse.** 23,337 of the 23,436 possible pairs carry
  a score, so it is a weighted graph and not an edge list of events. Anything
  that assumes sparsity — most centrality measures, most community detection —
  needs a threshold applied first, and the threshold is an analytical choice the
  file deliberately does not make for you. Figures 34–37 use 0.75 and show what
  moves when that changes.
- **`weight` is a rate, not a count.** Every other layer's weight counts events;
  this one is a proportion in [0, 1], and `weight_newman` is empty because there
  is no group size to correct for.

It is built on **contested divisions only** — near-unanimous ones excluded, the
same filter figure 21 uses — because agreement on a vote nobody opposed is
agreement with the whole chamber. Leaving them in pushes every pair to about
0.84 and compresses exactly the differences the layer exists to show. A pair
needs 30 jointly-cast divisions to be scored, and only NCA-2011 has a roll-call
record at all, so this layer covers one chamber.

## Node attributes for homophily

`nodes.csv` carries the attributes the priority layer was built for:
`gender`, `birth_year`, `birth_governorate_id`, `governorate_id`, `region`,
`littoral`, `party_family_last`, `occupation_raw`, `career_sectors`,
`n_mandates`, and behavioural rates.

Regional homophily is better computed from these attributes than from an edge
list — an assortativity coefficient on `region` or `littoral` answers the
question directly, and the coastal/interior cleavage is the one most likely to
be substantively interesting. Watch the missingness: `birth_governorate_id` is
present for only 68 of 856 people, whereas `governorate_id` (the constituency's
governorate, not the person's origin) is present for 705. **These are different
variables.** Constituency governorate is where someone was elected; birth
governorate is where they are from. Conflating them will produce a confident
finding about the wrong thing.

## Worked examples

`examples/example_python.py` and `examples/example_r.R` load the tables, build
one projection from the incidence file, and report degree, density and
assortativity for a chosen chamber. Both run on the committed data with no
network dependency beyond `igraph` (R) or `networkx` (Python), and both print
their missingness before reporting any statistic.

## Cautions worth repeating

- **Coverage is not random.** Five chambers have person-level data; eleven have
  only their speaker. Any network claim about "Tunisian parliamentarians" is a
  claim about 1956, 2011-2014, 2014-2019, 2019-2021 and 2023-present unless you
  say otherwise.
- **The mandate panel is continuous across the democratic period**
  (NCA-2011 → ARP-2014 → ARP-2019 → ARP-2023): 84 people appear in more than one
  chamber and 16 in three or more. But ARP-2014 has no committee data, so a
  committee-network panel still has a hole in the middle where the mandate panel
  does not — check which layer your design actually needs.
- **`n_mandates` counts only mandates in this dataset.** Someone who served in
  1994 and again in 2011 will show `n_mandates = 1`, because the 1994 chamber has
  no roster. Re-election and elite-persistence measures are therefore biased
  downward for anyone whose earlier service falls in the undocumented era, and
  the bias is systematic rather than noisy.
