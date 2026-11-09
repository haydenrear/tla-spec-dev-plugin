# BS-01 goal signal

- GOAL-BS-BUGS (direct). local_signal `pytest tests -q -k 'close or complexity_ledger or ledger'`
  ran as part of the repository_unit superset (`... or retirement`): branch
  9 failed / 285 passed / 2 errors, base 9 failed / 265 passed / 2 errors. The
  failing set is the same, and the +20 passes are the new tests/test_close_records.py.
  Per issue (regression-on-base.txt vs regression-on-branch.txt), red on base
  and green on branch: #187, #172, #134, #173, #174, #177, #72, #143 SF-007/009,
  #143 SF-045. #143 SF-042b is green on BOTH: design/ is already archived under
  `<entry>/ticket/design` on the base, so there is nothing to fix.
  Classification: **moved as expected**. 8 issues proven, plus #143's close items.
- GOAL-BS-SUITE (guard). The targeted subset and spec-unit show no new failures
  (spec-unit: 11 failures, the same set as baseline/spec-unit-failures.txt).
  The full `pytest tests` was not run to completion: about 7% after 15 minutes
  under graph load, so it was stopped. Classification: **no measurable movement**
  on the measured subset.
- GOAL-BS-EVALS / GOAL-BS-MANUAL: N/A (BS-17 / BS-18).

Graph specWorkflow: 7 of 9 PASS, including spec.workflow.close.
spec.workflow.failure_cleanup_probe ERRORED twice ("node launcher exited with
live descendants"; lap 1 full run, lap 2 resumed from that node). It is a
nested-Gradle process-ownership residue, and BS-01's Python close code does not
reach it. Two laps used; recorded as stayed red.
