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

Writes three files to `data/processed/elite_persistence/`:

| file | rows | what |
|---|---:|---|
| `layer_legislators.csv` | 1,072 | one row per member per chamber, over 968 people |
| `layer_party_affiliations.csv` | 1,969 | one row per member per party, over 850 people |
| `names_bilingual.csv` | 968 | each member's name in the Assembly's Arabic and Latin columns, for the surname crosswalk |

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
that, by the same particle rules ElectionsTN applies to the register and
GovMembersTN to the ministers.

Because both this layer and the register are Arabic, no cross-script
transliteration is involved here, and 99.0% of members resolve to a registered
surname.

The same run writes `names_bilingual.csv`, every member's name in the Arabic
and the Latin columns the Assembly gives; for 952 of the 968 the Latin column
is in Latin letters. EliteNetworksTN's Arabic-Latin surname crosswalk learns
Tunisian spelling from those 952, and is tested on them:
held out of the build five folds at a time, 94.2% of these members have their
Latin surname read as the Arabic surname their own Arabic name carries.

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

`layer, person_id, name_raw, script, surname_candidates, period, subgroup`
in both files, plus `assembly_id, coverage_status,
entry_mode, gender` in the legislators and `party_id, party_name, evidence` in
the affiliations. `period` is the chamber's own `regime_period`;
EliteNetworksTN maps it onto its five shared periods.

## What the comparison found

Parliament is where the displacement of the old notability is most complete.
The 469 surnames the genealogies place in Tunisia before independence in 1956
are 3.3 times more common among these
968 people than in the 2024 electoral register (49 holders, 95% CI 2.5–4.3),
and the chamber sheds them faster than any other institution measured.

### In the contemporary window

Restricted to 2011–2023, with each member counted once, 742 people sat and
26 carried such a surname. A bearer is 2.3 times more likely (95% CI
1.6–3.4, p = 0.0003) to be a member of parliament than someone who is not —
17.3 per 100,000 bearers against 7.5 per 100,000 of everyone else.

That is the smallest multiplier of any position in the build, and the gap
widens once the ratio is converted into the units that compare across
institutions of different selectivity. The chamber's implied status gap is
+0.21 SD, against +0.44 for the cabinet, +0.37 for a listed board and
+0.42 for a co-shareholder of a listed company — about half of any of
them.

### Over the whole span

| | Bourguiba | Ben Ali | transition | Saied |
|---:|---:|---:|---:|---:|
| ratio | 7.0× | 6.1× | 2.3× | 2.1× |
| implied status gap | 0.50 SD | 0.44 SD | 0.21 SD | 0.17 SD |

an intergenerational correlation of b = 0.53 (0.23–1.25) per 30-year
generation. The cabinet over a comparable span comes out at 0.77 — the rate
Clark finds almost everywhere — and the public administration at 0.79. The
chamber is the one institution in the build where the old notability regresses
to the population substantially faster than that benchmark, in point estimate:
on four periods its interval is wide enough to contain both. Elected office
does not transmit.

A second measure is sharper still. Of the notable surnames sitting in one
period's chamber, almost none returns in the next — 1 of 12, 1 of 11, 0 of 17 —
about what redrawing from the same pool would return. Listed boards re-select
the same houses at 2.1–3.6× chance and the cabinet at 2.8–11.4×. Parliamentary
presence, for these families, is a one-shot event.

### The caveat that matters most for these rows

The post-1956 placebo cannot be tested against this roster: 38 surnames over
0.13% of the register predict 0.97 holders in a chamber of 742, so the four
observed there are too few to separate any hypothesis from another.

The control can be, and it is the more informative test. The 45,679 equally
rare surnames the genealogies never recorded hold 166 of the 968
parliamentarians, a ratio of 0.90× [0.78–1.03] — at parity. Against
that the chamber's 3.3× is a factor of 3.7, so the parliamentary advantage is
real and is about a fifth of the cabinet's eighteenfold gap over the same
control. Parliament is the weakest of the elite rosters in the build, not a
null one.

Full results, figures and limitations: `docs/FINDINGS-persistence.md` in
EliteNetworksTN.
