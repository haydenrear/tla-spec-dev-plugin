# BS-02 evidence (#188)

| file | what |
|---|---|
| regression-base-df48724c.txt | `tests/test_bs02_disposition_improvement_ledger_attribution.py` run against an extract of origin/epic/bug-sweep (df48724c): 13 failed, 2 passed (the 2 passes are the nested-layout controls for #162, which the base already handled) |
| regression-branch.txt | the same file on feature/188-ledger-disposition: 15 passed |
| repository-unit-base-df48724c.txt | `pytest tests -q -k 'disposition or improvement_ledger or attribution'` on the base extract: 2 failed, 34 passed, 1 skipped, 8 errors |
| repository-unit-branch.txt / local-signal-branch.txt | the same on the branch: 1 failed, 50 passed, 1 skipped, 8 errors. The 8 errors (live ledger is `findings: []` mid-epic) and `test_workflow_close_keeps_the_ledger` (close_tickets.py ticket_plan indentation, BS-01's key) are identical on both sides; `test_score_tools::test_history_marks_the_inverted_d5_attribution` failed only in the non-git base extract |
| specWorkflow-run.txt, specWorkflow-20261107-173107-report.md | full specWorkflow: nodes 1-6 pass; `spec.workflow.failure_cleanup_probe` ERRORED "node launcher exited with live descendants" |
| specWorkflow-resume.txt, specWorkflow-20261107-173427-resume-report.md, specWorkflow-resume-lap2.txt | lap 1 and lap 2 resumes from that node: same leak, different PID each time. No node of specWorkflow reads disposition.py, improvement_ledger.py or bug_attribution.md |
| specWorkflow-run-only-adapters_resolve.txt | `--run-only-node spec.reference.adapters_resolve` refused: "replay selected input contains a failed or skipped prefix node" |

Model result: no-op. `specs/current` is unchanged; this ticket changes two advisory scripts and a reference page, none of which is an Internal.tla action, variable or invariant.
