# BS-03 (#175) evidence: errored vs failed

- `base-red.txt`: `test_errored_vs_failed.py` run against `origin/epic/bug-sweep` (68922587/df48724c) scripts. 12 failed, 1 passed (the backward-compat test).
- `branch-tests.txt`: `uvx --with pyyaml --with jinja2 pytest skills/test-graph/scripts/tests -q` on the branch after merging the epic. 65 passed, 30 subtests passed.
- `graph-cliWorkflow.txt`: `python3 test_graph/run-graphs.py --only cliWorkflow`. PASSED, runner_exit=0.
- Model result: no-op. `specs/current` is unchanged because this is a runner-reporting fix with no modeled state machine (issue: "Spec workflow — NOT REQUIRED").
