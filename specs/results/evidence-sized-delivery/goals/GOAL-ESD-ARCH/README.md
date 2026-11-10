# GOAL-ESD-ARCH — verdict (ESD-06)

**Metric:** confirmed validation-origin failure families from ESD-01 that the ESD-03 review
guidance (`skills/test-graph/references/graph-architecture-review.md`) flags vs misses.
**Baseline:** unmeasured. **Target:** report-only (owner set no threshold). **Verdict: measured
(no threshold to be met or missed); see reading below.**

Instrument run: the merged checklist applied by a delegated reader who did NOT open ESD-03's files,
the reviews or ESD-06's declaration (`holdout-application.md`, method section). Single pass, not tuned.

## 1. Hold-out (rows ESD-03 did not score)

117 inventory rows − 40 author-scored = 77; 21 excluded as product-origin and 8 as unattributed /
not an instrument (each with a reason in `holdout-application.md`) → **n = 48**.

| | F flagged | P partial | M missed |
| --- | --- | --- | --- |
| hold-out, all 48 | 10 (21%) | 24 (50%) | 14 (29%) |
| defect inside a node or its support code (21) | 10 | 6 | 5 |
| defect outside any node (27) | 0 | 18 | 9 |

Two F rows are borderline (SI-18-DF-01 via C4, DEF-310/411 via H1): strict F = 8/48 (17%).
35 rows needed the primary record; 13 were decided from the row text.

Compare the author's self-application (ESD-03 `local-signal.md`): 17 F / 13 P / 6 M of 36 (47% F).

## 2. Independent re-score of a fixed sample of ESD-03's own rows (every third row, n = 12)

| Row | ESD-03 (author) | Blind | |
| --- | --- | --- | --- |
| RP-07-DF-01 | F | F | = |
| #241 / E02-R11 | P | P | = |
| DEF-154 | P | P | = |
| missing-rung (REACH) / SI-25-DF-06 | F | F (that instance only) | = |
| SM402-ISOLATION family | P | P | = |
| EA-DF-15 → #248 | F | P | author higher |
| E10-OWNER-GRAPH-STARTUP-001 | M | P | author lower |
| DEF-503 | F | P | author higher |
| DEF-124 | F | P (record: spec-unit CLI run by hand, not a node) | author higher |
| DEF-110 | M | M | = |
| #226 / BS-HP-05 | P | P | = |
| SI-19-DF-05 | M | M | = |

Agreement 8/12. Author F 5 → blind F 2 in the sample; all three disagreements on F were
downgrades. This confirms the wave-3 review's suspicion that the self-applied table is biased toward
"flagged". Scaling the sample naively, ESD-03's 17/36 F is closer to ~7/36 under a blind reader
(uncertainty large: n = 12).

## 3. Reading

- The checklist is **effective inside a graph node** (10 F / 6 P / 5 M of 21 hold-out node
  defects; strong on vacuous gates H1/H2, home/identity fall-through B1, nested fixed budgets D2,
  shared fixture state A1/E2, Gradle daemon ownership E1/C3).
- It **does not reach validation-origin defects outside a node** — eval harnesses and graders,
  sandboxes, pytest/JUnit suites, CLIs, providers and homes, CI triggers, sweep aggregation:
  0 F of 27. Many are P because rules C1/C2/H4/D2/B1 name the mechanism but are scoped to nodes.
- Named miss patterns (from `holdout-application.md`): verdict arithmetic/parsing errors;
  stale behavioural assertions after a contract change (only an un-numbered preamble sentence);
  instruments that can never go green (H1 asks for a red control, nothing asks for a green one);
  questions above one node (which graphs reach a surface, CI triggers); inter-node / fixture
  coupling; telemetry noise.
- "Most validation-origin families flagged" (ESD-03's local-signal reading) **does not hold under
  blind application** at row level: 21% F (17% strict), 71% F+P. At family level the node-resident
  families (F1 node contracts, F3 vacuous gates, F5 shared state) are reached; F7 (eval) and the
  non-node halves of F2/F6 are not.

Sample size 48 + 12, one reader, one pass; inter-rater uncertainty is shown by the 8/12 agreement.
False greens of the instrument: the author's F on EA-DF-15, DEF-503, DEF-124. Escapes: none
measurable (retrospective).

Deferred: `ESD-06-DF-03` (scope gap: non-node instruments; candidate numbered rules).
