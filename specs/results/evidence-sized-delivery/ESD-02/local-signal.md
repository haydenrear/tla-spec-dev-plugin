# ESD-02 local signal (GOAL-ESD-ARCH, contribution: enabling)

Assignment `local_signal`: *trace each worked example back to an ESD-01 row; record
origin/channel separation and before/after finding conservation by hand.* Run once, by hand,
by the ticket agent on `feature/236-attribution-anchors`. It decides nothing (ESD-06 decides
GOAL-ESD-ARCH).

## 1. Every worked example traces to an ESD-01 row

All rows are in `specs/results/evidence-sized-delivery/ESD-01/inventory.yaml`. Each was
re-opened, and the fields the example uses were checked against the row (and against the primary
record where noted).

| Example (`bug_attribution.md`) | ESD-01 row | Row fields used | Primary record re-opened |
|---|---|---|---|
| §7e 1: product failure caught by Test Graph | `ATTR-234-28` | origin, anchor `UNMODELED/server-fact-path`, channel `test-graph`, class product bug | no: CDC is not checked out here, so the row is cited as written |
| §7e 2: defect in a graph node | `RP-07-DF-01` | origin, anchor `UNMODELED/test-graph-process-ownership`, channel `test-graph`, disposition (general half carried) | `specs/results/deferred_findings_final.yaml` (RP-07-DF-01 summary/reproduction) |
| §7e 3: invalid red from the environment | `SM eval round 2026-09-07 (instrument rows, incl. EV-I-08 TMPDIR)` | origin, anchor `UNMODELED/eval-sandbox`, channel `eval`, consequence "false red: the score said the skill could not create a worktree" | no (skill-manager repo); this is the same round §6a already cites |
| §7e 4: blind green | `DEF-110` | origin, anchor `UNMODELED/surface-parity`, channel `manual-final-testing`, consequence "123,132 spec-unit + 3,724 external cases all green" | no (meta-harness repo) |
| §7e 5: unresolved attribution | `OBS-EOF-HISTORICAL-UNRESOLVED / polymarket #49` | origin, anchor, channel `test-graph`, class unresolved, cause_confidence inferred | no (polymarket repo) |
| §6a *Resolved*: the false-red record shape | `BS-07-DF-05` | recurrence "13 runs / 7 tickets", consequence, cause_confidence inferred | yes: `specs/results/bug-sweep/deferred-ledger.yaml` (BS-07-DF-05), `BS-12/specWorkflow/VERDICT.txt`, `BS-02/README.md`, `review/wave-3/review.md` §3, `review/wave-5/review.md` |
| §6a *Resolved* item 4: the supersession precedent | `BS-10-DF-01` | channel independent-review, disposition "superseded by BS-11-DF-03; both batched" | the row only |
| §7b migration-map illustration | `#226 / BS-HP-05`, `#233 fixture` | both anchored `UNMODELED/test-graph-resume`, with different origins (product vs fixture) | the rows only |
| §4.3 effect is not origin | ESD-01 `local-signal.md` rows `SI-27-DF-06`, `SI-19-DF-04`, `EL #163` | the 3 of 10 class disagreements | the ESD-01 file |
| §4.3 / §7d: origin depends on the repository | `DEF-124 (with DEF-032, DEF-112)` | anchor `UNMODELED/spec-unit-runner` in MH; disposition "promoted upstream to tla-spec-dev-plugin" | `specs/program_model/TlaSpecDevCli.tla` (`SpecUnitTestsRequireMeasuredCorpus`, `RunSpecUnitTests`) |

**Traced: 5 of 5 required examples, plus 4 supporting citations.** No example is invented, and
none uses a row that does not exist. Four of the five example rows live in other repositories,
so their primary records were not re-opened from this worktree. They rely on ESD-01's
spot-check (ESD-01 `README.md`, *Completeness*).

## 2. Origin and channel are kept apart in every example

| Example | Channel | Origin | Same thing? |
|---|---|---|---|
| 1 | test-graph | CDC CLI (product) | no |
| 2 | test-graph | a graph node and the executor contract (validation) | no. The channel *names* Test Graph, but the origin is the node's nested build. The row is filed under a validation bin, not under Test Graph product. |
| 3 | eval | the eval sandbox (validation) | no |
| 4 | manual-final-testing | MH frontend (product) | no |
| 5 | test-graph | UNDECIDED | no: the origin is held as UNDECIDED, and the channel was not substituted for it |

**Origin confused with channel: 0 of 5.** This matches ESD-01's 0 of 10. The effect is written
as a third column in all five examples: faithful, false red, false red, blind, UNDECIDED. In no
example is the effect used as the origin.

## 3. Conservation by hand: before and after this ticket's re-reading

"Before" is the ESD-01 classification of the five example rows plus BS-07-DF-05. "After" is the
attribution `bug_attribution.md` now prescribes.

| Row | Before (ESD-01 class) | After: origin area / effect | Product total | Validation total | UNDECIDED |
|---|---|---|---|---|---|
| ATTR-234-28 | product bug | product / faithful | 1 | | |
| RP-07-DF-01 | graph … defect | validation bin / false red | | 1 | |
| SM eval instrument rows | package/provider/environment | validation bin / false red | | 1 | |
| DEF-110 | product bug (+ BLIND consequence) | product / blind (BLIND on the suites, an annotation, not a 2nd finding) | 1 | | |
| OBS-EOF … #49 | unresolved | UNDECIDED / UNDECIDED | | | 1 |
| BS-07-DF-05 | graph … defect (consequence: false red) | validation bin / false red, recurrence 13 runs on 7 tickets | | 1 | |
| **Totals** | **6 findings** | **6 findings** | **2** | **3** | **1** |

- **Findings before: 6. Findings after: 6.** No row was dropped or merged, and no row was split.
- The 13 BS-07-DF-05 reds contribute **0** to any product anchor, both before and after. They
  were never product findings. The correction lives in the instrument row, and the 7 tickets'
  original VERDICT/README reds are unedited.
- The §7b illustration (`#226` and `#233` under a hypothetical resume action) is also conserved:
  2 rows before and 2 after.

## 4. Against `expected_effect`

`expected_effect`: *none, enabling only. Gives validation infrastructure an explicit attribution
area, so that ESD-03 guidance and ESD-04 sizing do not count instrument faults as product risk.*

**Classification: no measurable movement.** This is the expected outcome for an enabling
ticket: there is no metric to move here. Three things are now in place for ESD-03 and ESD-04:

- the validation area (§7d);
- the effect axis (§4.3);
- the false-red record shape (§6a).

Over the six rows above, the prescribed attribution puts 3 findings in validation bins, 2 in
product and 1 in UNDECIDED. Only ESD-06's held-out application can measure whether ESD-03's
guidance uses this split.
