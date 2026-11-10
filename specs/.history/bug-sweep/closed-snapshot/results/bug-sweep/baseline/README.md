# bug-sweep baselines (epic base 68922587)

| Goal | Baseline | Measured on | Evidence |
|---|---|---|---|
| GOAL-BS-BUGS | 0 of 37 in-scope issues proven fixed (no regression tests exist for them) | 68922587 | issue list in ticket_plan.yaml `covers` |
| GOAL-BS-SUITE | 9 failed / 1864 passed / 14 skipped | 350b9ab4 (2 commits before the base: #180 test-graph chained resume, which `tests/` does not exercise) | session run 2026-11-04, 27 min; BS-08 re-measures on the base |
| GOAL-BS-GRAPHS | see graphs-default.txt / graphs-optin.txt | 68922587 | this directory |
| GOAL-BS-EVALS | unmeasured: BS-17 runs base and tip in one session | 68922587 | specs/evals/bug-sweep |
| GOAL-BS-MANUAL | unmeasured | 68922587 | N/A |

Failing tests at 350b9ab4: test_architecture_tags::test_the_same_tag_control_holds;
test_bootstrap_floor_is_declared::test_exactly_one_file_declares_a_floor;
test_corpus_diagnostics::test_cli_passes_on_the_committed_example_corpus;
test_example_drivers_write_inside_spec_tree::test_a_validation_run_does_not_generate_over_a_committed_corpus;
test_instrument_demonstrations::test_every_fast_demonstration_reproduces;
test_negative_corpus_adapter_conformance::test_the_negative_corpus_names_its_arguments_as_the_committed_corpus_does;
test_source_citations [specs/current/spec_manifest.yaml] and [specs/program_model/spec_manifest.yaml];
test_verdict_schema::test_the_corpus_gate_states_its_verdict_as_data.
Checkout-dependent: test_ticket_retirement::test_repository_canonical_delivered_plan_has_matching_close_receipts (newest closed snapshot chosen by mtime).
