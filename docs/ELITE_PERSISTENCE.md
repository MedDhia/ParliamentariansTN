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
unevenly and the unevenness is not random: **it is the single-party era that is
missing.** Six chamber-terms have a roster and thirteen do not.

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

**No Tunisian party membership roll is public**, so nothing in this file speaks
to party membership at large. It is the same people as `layer_legislators.csv`,
cut by the party they sat for.

## Schema

Shared with ElectionsTN and GovMembersTN. Surnames are written as
**candidates**, longest first, rather than resolved, because only the register
can say whether `بن سالم` is a family in its own right or a patronymic, and
this repository does not hold the register.

`layer, person_id, name_raw, script, surname_candidates, spine_candidates,
period, subgroup` in both files, plus `assembly_id, coverage_status,
entry_mode, gender` in the legislators and `party_id, party_name, evidence` in
the affiliations. `period` is the chamber's own `regime_period`;
EliteNetworksTN maps it onto its five shared periods.

## What the comparison found

Parliament is where the displacement of the old notability is most complete.
250 surnames the genealogies record, rare enough that a surname tags a lineage,
are **3.1 times** more common among the 968 people here than in the electoral
register (26 holders, 95% CI 2.1–4.4) — and the chamber is shedding them faster
than any other institution measured:

| 1956 + 1959–87 | ADV-2005 | 2011–21 chambers | ARP-2023 |
|---:|---:|---:|---:|
| **7.2×** (7/111) | 4.9× (5/117) | 2.3× (12/597) | **1.5×** (2/155) |

That is a half-life of **26 years** and a per-generation persistence rate of
**b = 0.31**, the lowest in the build; by the 2023 chamber the interval no
longer excludes parity. The cabinet over a comparable span halves every 40
years, and the listed-company boards do not decay at all.

A second measure is sharper still. Of the notable surnames sitting in one
period's chamber, **none** returns in the next — 0 of 7, 0 of 5, 0 of 9 — where
redrawing from the same pool would have returned a few. Listed boards re-select
the same houses at 2.6–2.8× chance and the cabinet at 2.1–8.2×. Parliamentary
presence, for these families, is a one-shot event.

Full results, figures and limitations: `docs/FINDINGS-persistence.md` in
EliteNetworksTN.
