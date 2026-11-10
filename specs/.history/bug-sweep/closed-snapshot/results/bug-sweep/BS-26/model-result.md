# BS-26 model result: no-op

`specs/current` and `specs/desired_program_model` are unchanged. This ticket changes
the test-graph SDK's attempt-closure format and validator, which are not modelled
behaviour of the program under `specs/`. No `open ticket`, `close ticket`,
`close_tickets.py` or `--accept-new` was run (the epic owns the model).

Regression proof (#226):
- regression-base-red.txt: (a) base sources with this branch's tests do not compile,
  because the base has no persisted mode to pass. (b) This branch with only the
  validator's use of the mode removed: 5 tests fail with the original closure error.
- regression-branch-green.txt: the full build-logic test task on the branch.
- e2e-red-continue-run.txt, e2e-red-resume.txt: the scratch graph before the fix, with
  only the logging change applied. The continue run logs the real closure exception,
  and the resume is refused.
- e2e-green.txt: the scratch graph with the fix. The closure exists, r.b reruns on
  resume, and the control run (no continue mode) still resumes.
- graph-cliWorkflow.txt, graph-effectProviderExamples.txt, local-signal.txt.
