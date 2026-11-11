# ESD-01 local signals

Both signals are reported as measured. Neither one decides anything: ESD-06 decides both goals
(the assignment's `goals[].decided_by`). Both signals were run once. Nothing was re-run, tuned or
selected.

## (a) GOAL-ESD-ARCH: second reading of a 10-row random sample

**Sample selection.** `inventory.yaml` was assembled first, with 117 rows in file order. Then 10
row indices were drawn with Python `random.seed(235); random.sample(range(117), 10)`. This was an
ad-hoc command and is not committed. The draw gave rows 3, 5, 10, 12, 32, 33, 45, 66, 93 and 99,
numbered 1-based in file order.

**Procedure.** For each sampled row, the primary evidence the row cites was re-opened: the
ledger row, the issue body, the PR body or the run file. Origin class and detection channel were
then classified again from that evidence alone, and compared with the inventory entry.

**Not independent.** The second reader is the same agent that wrote rows 1-45, working in the
same session. Rows 66, 93 and 99 were first written by a delegated reader. For those three rows
this is a genuine second reading. For the other seven it is a re-reading. A reader outside this
session would be the stronger control, and ESD-06 or the epic review is the natural place for
one.

| Row | Inventory id | Inventory class / channel | Second reading (source re-opened) | Class | Channel |
|---|---|---|---|---|---|
| 3 | `#226 / BS-HP-05` | product bug / operator-doing-the-work | Ledger lines 846-856: channel recorded as `operator-doing-the-work`; the fix is in RunReportWriter (the product). | agree | agree |
| 5 | `BS-10-DF-01` | invalid assertion / independent-review | BS-11-DF-03 refutes the claim by **measurement with the real SDK** (`RealSdkFixtureTest.test_describe_errored_graph_is_errored_not_not_run`), not by reading alone. Second-reading channel: `the-suite`. | agree | **disagree** |
| 10 | `BS-01-DF-01` | product bug / the-suite | `BS-01/repository-unit-base.txt`: close-path tests red on the base; the loader cannot parse anchors. Origin is the loader. A reader could also blame the plan writer, but the ledger's own fix text names both. | agree | agree |
| 12 | `BS-08 checkout-dependent test` | false red / the-suite | PR #221: "the newest closed snapshot was picked by directory mtime … a demonstrated checkout-order dependency". | agree | agree |
| 32 | `SI-27-DF-06 / verify.sh BLIND` | false red / the-suite | The ledger summary: checkers walked build output, so five checks went red. Second reading: the **origin** is the checkers' scan scope, which is `invalid assertion`; false red is the effect. | **disagree** | agree |
| 33 | `SI-19-DF-04` | false red / the-suite | The ledger summary: the `.gitignore` rule is spelled `.toolchain/`, and the test asserts `git check-ignore` on a path that may be absent. Second reading: `invalid assertion` (environment-dependent), with false red as the effect. | **disagree** | agree |
| 45 | `#233 fixture` | graph orchestration/node/fixture defect / the-suite | PR #233: "the new executor test initially failed because its synthetic January timestamps fell outside the actual executor interval". | agree | agree |
| 66 | `CDC #390` | package/provider/environment fault / test-graph | Issue body: OTLP absence, machine load, fresh-worktree prerequisites, memory variance. The first item is a JUnit test (`IndexingCliMainTest…`), so at least part was found by the suite. Second-reading channel: mixed `the-suite`/`test-graph`. | agree | **disagree** |
| 93 | `OBS-EVAL-MANAGER-LOCK-001` | package/provider/environment fault / operator-doing-the-work | polymarket `deferred_findings_final.yaml:152`: `channel: operator-doing-the-work`, `channel_class: hand`; the defect is in skill-manager 0.28.2 `sync --lock`. | agree | agree |
| 99 | `EL #163 / #170 / #105` | invalid assertion / test-graph | #163: "This is an outdated validation fixture"; #105: "restore explicit activation and provider setup in graph fixtures". Second reading: `graph orchestration/node/fixture defect`. | **disagree** | agree |

**Result.**

| Measure | Agreement |
|---|---|
| Origin class | **7 / 10** |
| Detection channel | **8 / 10** |
| Both | **5 / 10** |
| Origin component (where the defect lived), ignoring class | **10 / 10** |
| Origin confused with detection channel (a test-graph channel read as a Test Graph defect) | **0 / 10** |

**What the disagreements are.**

- **All three class disagreements sit on the same boundary.** The seven-class list mixes
  *origin* classes with *effect* classes. "False red" is an effect, and "invalid assertion" or
  "fixture defect" is the origin of that effect. A row legitimately belongs to one of each.
  `failure-families.md` (closing section) records this for ESD-03.
- **Both channel disagreements are a single row holding more than one detection event.** In
  BS-10-DF-01 the record was refuted by measurement. CDC #390 bundles several items.

**Against the expected effect.** The goal's `expected_effect` is "none — enabling only; supplies
the confirmed validation-origin failure families ESD-03 turns into review priorities".

The signal shows the families are reproducible at the **component** level (10/10). Classification
under the seven-class list is only partly reproducible (7/10).

Classification: **no measurable movement**. This ticket establishes the inventory and has no
baseline to move from. The 7/10 class agreement is a baseline for ESD-06.

## (b) GOAL-ESD-VELOCITY: cost rows with a primary timestamp source vs unknown

Counted over the 30 cost rows C1-C30 in `cost.md`:

| Classification | Count |
|---|---|
| Cites a primary timestamp/duration source (primary or derived from one) | **23** |
| Inferred (projection only) | **1** (C25) |
| Unknown | **6** (C13, C14, C15, C16, C22, C30) |

**Inside the 23 "primary" rows, coverage is partial in five places:**

- C4: ≥ 11 milestone-1 runs with no duration;
- C5: 7 of 13 probe false-red runs timed;
- C9: no per-run seconds in `compare.json`;
- C12: the 29 h window is known, but its split between wait and work is not;
- C20: 53 of 118 CDC reds carry machine time.

**The decisive gap is uniform across all six repositories.** No record carries the start time of
implementation for any ticket. C13 and C30 are therefore unknown everywhere, and the 10-100×
question in `cost.md` §4 cannot be answered from the records.

**Against the expected effect.** The goal's `expected_effect` is "none — enabling only;
establishes the retrospective cost baseline (or names it unmeasured)". The baseline is
established for:

- instrument execution;
- eval spend;
- phase-separated CDC batches;
- end-to-end elapsed time.

Implementation active time is **named unmeasured**.

Classification: **no measurable movement**. As in (a), there is no prior baseline.
