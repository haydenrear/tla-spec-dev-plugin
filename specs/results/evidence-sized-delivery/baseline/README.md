# Baseline — epic/evidence-sized-delivery (#234)

Measured on the epic base `a1ff56cf9ebc108aba2e8dd16b8c1eb3aaa0afa3` (origin/main at kickoff, 2026-11-10).

| Instrument | Result | Card |
| --- | --- | --- |
| Doc-contract subset (`validation.repository_unit` of ESD-02..05) | 407 passed, 1 skipped, 44 s | `doc-contracts.txt` |
| `pytest specs/current/tests` (spec-unit) | **2 failed**, 54 passed, 27 s — known red on the base | `spec-unit.txt` |
| TLC `MCsmall.cfg` on `specs/desired_program_model` (identical to `program_model`) | no error; 36 577 distinct states, depth 17 | `tlc-desired-MCsmall.txt` |

Known red on the base (ticket bar is **no new failures**; no ticket in this epic owns them):

- `specs/current/tests/test_tla_spec_dev_binding_reconciliation.py::test_every_model_action_is_bound`
- `specs/current/tests/test_tla_spec_dev_complexity_ledger_adapter.py::test_unfilled_ledger_template_refuses_the_close`

Goal baselines: all four goals are `unmeasured` at kickoff. ESD-01 reconstructs the retrospective
cost/attribution baseline (or names it unknown); ESD-06 measures the eval baseline on the base and
tip in one session. No numeric target was set at kickoff (owner: final review only), so every goal
target is report-only.
