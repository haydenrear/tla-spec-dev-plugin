# BS-21 evidence (#203)

- `red-on-base.txt`: tests/test_close_missing_result.py on origin/epic/bug-sweep (d9c20ee4): 6 failed, 6 passed
- `green-on-branch.txt`: same file on the branch: 12 passed
- `repo-unit.txt` / `repo-unit-base.txt`: `pytest tests -q -k 'close or result or retirement'`: 6 failed / 243 passed on branch; the same 6 fail on the base (231 passed there; +12 new)
- `local-signal.txt`: `pytest tests -q -k 'close and result'`: 15 passed
- `specWorkflow-outcome.json`, `specWorkflow-nodes.txt`: 7 passed, failure_cleanup_probe errored (known environmental "live descendants"), adapters_resolve not_run behind it
- `model-result.md`: no-op model result
