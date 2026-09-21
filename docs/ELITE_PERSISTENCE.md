# The parliamentarians as surnames

`src/parliamentarians_tn/elite_persistence.py` exports every member and every
party attachment as a surname, for a comparison assembled in
[EliteNetworksTN](https://github.com/MedDhia/EliteNetworksTN) that asks whether
the families the Tunisian genealogies record hold position out of proportion to
their share of the population. The denominator is the 2024 electoral register,
built in [ElectionsTN](https://github.com/MedDhia/ElectionsTN).

```bash
make elite-persistence      # about a second
```

Writes two files to `data/processed/elite_persistence/`:

| file | rows | what |
|---|---:|---|
| `layer_legislators.csv` | 1,072 | one row per member per chamber, over 968 people |
| `layer_party_affiliations.csv` | 1,969 | one row per member per party, over 850 people |

## What this layer can and cannot carry

Read [`COVERAGE.md`](COVERAGE.md) first. The chambers are covered very
unevenly and the unevenness is not random: it is the single-party era that is
missing. Six chamber-terms have a roster and thirteen do not.

| chamber | members | period | coverage |
|---|---:|---|---|
| ARP-2014 | 246 | second_republic | full |
| NCA-2011 | 217 | transition | full |
| ARP-2019 | 216 | second_republic | full |
| ARP-2023 | 155 | third_republic | full |
| ADV-2005 | 113 | ben_ali | partial |
| ANC-1956 | 108 | protectorate_transition | full |
| the other thirteen | 1–3 each | — | frame_only |

So this layer can set the constituent assembly of 1956 against the chambers of
the transition and the Third Republic, and it can say nothing about the
Neo-Destour and RCD chambers between 1959 and 2009. Anyone who wants those
decades has to take them from the ministers in GovMembersTN, which do cover
them, and accept that ministers and deputies are not the same selection.

The 2005 upper house was one-third presidentially appointed and its coverage is
partial, so its row should not be read as a chamber's composition.

## One row per person per chamber

The question is about persistence, so the unit is the member *in a chamber*: a
deputy returned in 2011 and again in 2014 is evidence about both. Deduplicate
on `person_id` for a headcount of the 968 individuals.

## Which name is read

`persons.csv` gives a split `family_name_ar` for only 154 of the 968 and a full
`name_ar` for all of them, so the surname is found by reading the full name —
the last token plus whatever particles bind onto it. `surname_spine.py` does
that, and it is byte-identical to the file ElectionsTN uses on the register and
GovMembersTN on the ministers; keep them in step with `scripts/vendor_spine.sh`
in EliteNetworksTN.

Because both this layer and the register are Arabic, no cross-script
transliteration is involved here, and 99.8% of members resolve to a registered
surname.

## Parties are a subgroup, not a population

`layer_party_affiliations.csv` pools the three places a party is recorded, and
names which one each row came from:

| evidence | rows |
|---|---:|
| bloc sat in | 1,063 |
| electoral list stood on | 758 |
| affiliation table | 217 |

None is complete alone: the affiliation table covers the 2011 constituent
assembly, the bloc table covers the chambers Al Bawsala observed, and the
electoral list exists only where the mandate came from a list election — which
the 2023 chamber, elected on individual candidacies, has none of. 850 of the
968 members (88%) carry at least one.

No Tunisian party membership roll is public, so nothing in this file speaks
to party membership at large. It is the same people as `layer_legislators.csv`,
cut by the party they sat for.

## Schema

Shared with ElectionsTN and GovMembersTN. Surnames are written as
candidates, longest first, rather than resolved, because only the register
can say whether `بن سالم` is a family in its own right or a patronymic, and
this repository does not hold the register.

`layer, person_id, name_raw, script, surname_candidates, spine_candidates,
period, subgroup` in both files, plus `assembly_id, coverage_status,
entry_mode, gender` in the legislators and `party_id, party_name, evidence` in
the affiliations. `period` is the chamber's own `regime_period`;
EliteNetworksTN maps it onto its five shared periods.

## What the comparison found

Parliament is where the displacement of the old notability is most complete.
The 196 surnames the genealogies place in Tunisia before independence in 1956
are 3.4 times more common among these
968 people than in the 2024 electoral register (24 holders, 95% CI 2.3–5.0),
and the chamber sheds them faster than any other institution measured.

### In the contemporary window

Restricted to 2011–2023, with each member counted once, 742 people sat and
12 carried such a surname. A bearer is 2.2 times more likely (95% CI
1.3–3.9, p = 0.02) to be a member of parliament than someone who is not —
16.8 per 100,000 bearers against 7.6 per 100,000 of everyone else.

That is the smallest multiplier of any position in the build, and the gap
widens once the ratio is converted into the units that compare across
institutions of different selectivity. The chamber's implied status gap is
+0.20 SD, against +0.48 for the cabinet, +0.46 for a listed board and
+0.55 for a co-shareholder of a listed company — less than half of any of
them.

### Over the whole span

| | 1956 + 1959–87 | ADV-2005 | 2011–21 chambers | ARP-2023 |
|---:|---:|---:|---:|---:|
| ratio | 8.6× | 5.8× | 2.3× | 1.8× |
| implied status gap | 0.56 SD | 0.43 SD | 0.21 SD | 0.13 SD |

an intergenerational correlation of b = 0.50 (0.34–0.71) per 30-year
generation. The cabinet over a comparable span comes out at 0.79 — the rate
Clark finds almost everywhere — and the public administration at 0.69. The
chamber is the one institution in the build where the old notability regresses
to the population substantially faster than that benchmark. Elected office
does not transmit.

A second measure is sharper still. Of the notable surnames sitting in one
period's chamber, none returns in the next — 0 of 7, 0 of 5, 0 of 8 — where
redrawing from the same pool would have returned a few. Listed boards re-select
the same houses at 2.4–2.6× chance and the cabinet at 2.0–6.9×. Parliamentary
presence, for these families, is a one-shot event.

### The caveat that matters most for these rows

The post-1956 placebo cannot be tested against this roster: 16 surnames over
0.047% of the register predict 0.35 holders in a chamber of 742, so the
zero observed there is the expected outcome under any hypothesis rather than a
clean null.

The control can be, and it is the more informative test. The 11,456 equally
rare surnames the genealogies never recorded hold 63 of the 968
parliamentarians, a ratio of 1.3× [1.0–1.6] — barely above parity. Against
that the chamber's 3.4× is a factor of 2.6, so the parliamentary advantage is
real and is about a quarter of the cabinet's twelvefold gap over the same
control. Parliament is the weakest of the elite rosters in the build, not a
null one.

Full results, figures and limitations: `docs/FINDINGS-persistence.md` in
EliteNetworksTN.
