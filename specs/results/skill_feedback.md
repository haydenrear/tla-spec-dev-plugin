# Skill feedback — spec-double-compiler / tla-spec-dev

`references/migration.md` Phase 6: a migration is not done when the models
converge. It is done when everything the skill **could not express** has been
turned into a concrete recommendation against the skill repository. The skill
improves only through what real migrations fail to express.

This file is **append-only by convention**. Close-out creates it once and
thereafter only appends. Never rewrite or delete an existing finding — a filled
finding is evidence.

## How to use this file

1. At each close-out the CLI appends a `## Close-out …` entry below.
2. Fill in that entry's `feedback_status`, then record one `### SF-NNN` finding
   per thing the skill could not express.
3. **Turn every finding into a ticket or PR against the spec-double-compiler
   repository** — that is the point of this file, not the record-keeping:

   ```
   gh issue create --repo haydenrear/tla-spec-dev \
     --title "<SF-NNN one-line title>" --body-file <extract of the finding>
   ```

   Then set `recommendation:` to the resulting URL and `status: filed`.
4. If you looked and there was genuinely nothing, set
   `feedback_status: none-found`. **Silence is not an answer** — an unreviewed
   entry is recorded as unresolved in the close history.

## The four prompt categories

- `surviving-mutants` — Surviving mutants
- `unmodelable-effects` — Unmodelable effects
- `budget-and-metric` — Budget adjustments and metric calibration
- `profile-schema-cli` — Profile, schema, and CLI workarounds

## Finding format

Every finding is a `### SF-NNN` heading followed by `- key: value` lines. The
close path parses these, so keep the shape.

Fields required on every finding:

- `category:` one of `surviving-mutants`, `unmodelable-effects`, `budget-and-metric`, `profile-schema-cli`
- `target:` the exact tool surface that proved inadequate — command, script
  path and function, budget key, profile rule, or manifest field. Not "the CLI".
- `observed_on:` the real repository/module/ticket it was run against. A finding
  without a real target is a wish, not evidence.
- `evidence:` a durable path (command output, TLC log, report) — not prose.
- `severity:` one of `blocks-migration`, `silent-data-loss`, `wrong-result`, `manual-workaround`, `friction`
- `root_cause:` one of `tool`, `spec`, `target`, `unknown` — whether the
  tool's code, its specification, or the target under migration was at fault.
  A correct implementation of a wrong spec is `spec`; filing it against the
  code files it in the wrong place.
- `workaround_applied:` what the migration had to do to proceed, or `none`.
- `recommendation:` `ticket <url>` or `PR <url>` against spec-double-compiler / tla-spec-dev
- `status:` `open`, `filed`, or `wontfix`

Category-specific fields, so the common cases are structured rather than prose:

- `surviving-mutants` — `mutant:`, `operator:`, `location:`, `why_unreached:`
  (which generator, strategy, or profile rule could not reach it)
- `unmodelable-effects` — `effect:`, `why_not_port_state:`, `modeled_as:`
  (or `unmodeled`)
- `budget-and-metric` — `budget_key:`, `default_value:`, `value_used:`,
  `gated_quantity:` vs `measured_quantity:` (name both when a gate compares
  quantities that are not commensurable), `metric_blind_spot:` (what a passing
  metric failed to notice)
- `profile-schema-cli` — `surface:`, `forced_workaround:`, `data_loss:`
  (`yes`/`no`)

## Worked examples

These are real findings this epic produced *before* this template existed. They
are the calibration for what a good finding looks like; they are recorded here
as `SF-000x` examples and are excluded from filing status.

### SF-000a — Projected complexity reduction required deleting real behavior
- category: budget-and-metric
- target: scripts/analyze_complexity.py — projected-reduction reporting
- observed_on: tla-spec-dev @ MF-020 (ticket_phase ordinal collapse)
- evidence: specs/.history/modular-fuzzing-epic/ticket-*-MF-020/
- severity: wrong-result
- root_cause: tool
- gated_quantity: distinct reachable states
- measured_quantity: generated states
- metric_blind_spot: deleted self-loops. Reproducing the projected -13.1%
  required tightening a guard from `>= 2` to `= 2`, deleting a legitimate
  idempotent re-fire transition. The distinct-state gate is structurally blind
  to that, so a behavior deletion scored as a re-representation win.
- workaround_applied: projection withdrawn by hand after transition-level diff
- recommendation: ticket (example only)
- status: wontfix

### SF-000b — Promotion destroyed files unique to specs/current
- category: profile-schema-cli
- target: scripts/spec_evolution.py::replace_tree (ticket-close promotion)
- observed_on: tla-spec-dev @ MF-012, MF-020, MF-021
- evidence: tests/test_promotion_preserves_current.py
- severity: silent-data-loss
- root_cause: tool
- surface: `tla-spec-dev close ticket` promotion step
- forced_workaround: restore deleted regression tests from git history
- data_loss: yes
- recommendation: ticket https://github.com/haydenrear/tla-spec-dev/issues/22
- status: filed

### SF-000c — PATH wrapper ran pre-epic code for an entire epic
- category: profile-schema-cli
- target: `tla-spec-dev` PATH wrapper -> ~/.skill-manager/skills/spec-double-compiler
- observed_on: tla-spec-dev @ modular-fuzzing epic (all tickets)
- evidence: specs/desired_program_model/ticket_plan.yaml (toolchain_rule)
- severity: wrong-result
- root_cause: tool
- surface: skill installation / PATH shim
- forced_workaround: pin every lifecycle command to
  `python3 scripts/tla_spec_dev.py --spec-root specs ...`
- data_loss: yes — the stale wrapper is why the promotion defect fired three
  times, including once after its fix had merged
- recommendation: ticket (example only)
- status: wontfix

### SF-000d — Bound gate compared incommensurable quantities
- category: budget-and-metric
- target: scripts/analyze_complexity.py — state-space bound gate
- observed_on: tla-spec-dev @ MF-011
- evidence: specs/.history/modular-fuzzing-epic/ticket-*-MF-011/
- severity: blocks-migration
- root_cause: spec
- budget_key: max_distinct_states
- default_value: 50000
- value_used: new `max_state_space_bound` added (MF-022)
- gated_quantity: static state-space upper bound (1,179,648)
- measured_quantity: actual reachable distinct states (2,923)
- metric_blind_spot: a ~400x over-approximation failed a model 17x *under* its
  own budget; the tool's own recommended optimum still failed the gate.
- workaround_applied: none — gate reported its own failure rather than tuning
- recommendation: ticket https://github.com/haydenrear/tla-spec-dev/issues/28
- status: filed

---

## Close-out ticket MF-017

- close_scope: ticket
- close_id: MF-017
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-18T21:40:12+00:00
- summary: MF-017: close-out emits the migration.md Phase 6 skill-feedback retro into specs/results/skill_feedback.md (four prompt categories, structured findings, filing instructions against spec-double-compiler) and records in the append-only history whether feedback was filed and where. Zero model delta: close-out gains a file effect, not a command (MF-021 precedent).
- feedback_status: items-recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

### SF-001 (filed: https://github.com/haydenrear/tla-spec-dev/issues/105) — scaffolded fixture workflow cannot exercise two consecutive closes
- category: profile-schema-cli
- target: scripts/scaffold_spec_workflow.py — emitted desired_program_model/ticket_plan.yaml
- observed_on: tla-spec-dev @ MF-017 (SkillFeedbackCloseOutAdapter)
- evidence: specs/current/production_adapters.py::SkillFeedbackCloseOutAdapter
- severity: manual-workaround
- root_cause: tool
- surface: `tla-spec-dev scaffold workflow`
- forced_workaround: the adapter hand-appends a second ticket entry to
  ticket_plan.yaml before the second `open ticket`, because the scaffolded plan
  contains exactly one ticket and `close ticket` refuses an id that is not in
  the plan.
- data_loss: no
- note: any behavior that only appears ACROSS closes — accumulation,
  append-only-ness, history sequencing — is untestable against the stock
  fixture without this workaround. That is a class of regression the fixture
  currently cannot catch.
- recommendation: (none yet) — recommend a `--tickets N` option on
  `scaffold workflow`, or a multi-ticket fixture plan, so cross-close behavior
  is testable without hand-editing YAML
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/105

### SF-002 (filed: https://github.com/haydenrear/tla-spec-dev/issues/106) — plan prescribed model state that implementation showed to be wrong
- category: budget-and-metric
- target: specs/desired_program_model/ticket_plan.yaml — per-ticket
  `desired_actions` / `current_increment.model_state`
- observed_on: tla-spec-dev @ MF-017
- evidence: specs/tickets/MF-017/results/complexity-ledger.md
- severity: friction
- root_cause: spec
- gated_quantity: prescribed model state (`skill_feedback`, `EmitSkillFeedback`)
- measured_quantity: actual model delta after implementation (zero)
- metric_blind_spot: the plan fields are written at scheduling time and are
  never reconciled against what implementation proves. MF-011 and MF-020 each
  hit the same shape (a spec-level error with a correct implementation); this
  is the third instance, so it is a pattern, not an accident. Implementing the
  prescription literally would have cost bound 221,184 -> 663,552 to represent
  a document field.
- workaround_applied: implemented at zero delta and recorded an `outcome:` field
  on the plan entry explaining the deviation, for post-merge review
- recommendation: (none yet) — recommend the close path diff prescribed
  `desired_actions`/`model_state` against the promoted model and require an
  explicit `outcome:` when they disagree, rather than leaving the plan silently
  contradicting the accepted model
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/106

### SF-003 (filed: https://github.com/haydenrear/tla-spec-dev/issues/107) — promotion silently discards edits to seeded specs/current files
- category: profile-schema-cli
- target: scripts/spec_evolution.py::promote_current_tree — promotion report
- observed_on: tla-spec-dev @ MF-017 (specs/current/spec_manifest.yaml)
- evidence: specs/tickets/MF-017/results/complexity-ledger.md
- severity: manual-workaround
- root_cause: tool
- surface: `tla-spec-dev close ticket` promotion step
- forced_workaround: reapply the edit to specs/current after close and commit it
  separately
- data_loss: yes — recoverable, but silent
- note: MF-021 made promotion enumerate what it REMOVED and PRESERVED, which is
  why this was caught at all. It does not enumerate what it OVERWROTE. An edit
  made to a seeded specs/current file during a ticket is reverted by promotion
  with no mention in the report, and the close still reports success. The
  overwrite itself is correct (specs/current is a working copy promoted from the
  ticket); the silence is not.
- recommendation: (none yet) — recommend the promotion report also enumerate
  overwritten paths whose content changed, the same way it already enumerates
  removed and preserved paths
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/107

## Close-out ticket MF-014

- close_scope: ticket
- close_id: MF-014
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-18T22:39:57+00:00
- summary: Corpus diagnostics and hard case caps. Case caps are hard gates in the shape of MF-011's state-space bound: over budget reports and exits nonzero, never trims. No code path drops, filters, samples, or truncates a case to fit a budget. Diagnostics report count per (action, label class), dominant and starved strata, and what varies across the redundant group, classified into unconstrained ordering / interchangeable values / action enabled across equivalent states. Labelers repurposed to diagnostic strata; remediation is a recommendation requiring user approval; named regression traces always retained. Accept path is raising the cap in spec_manifest.yaml with a recorded rationale. Model delta: corpus_gate + AnalyzeCorpus, 8->9 vars, 11->12 actions, deviating from the stale DistillCorpus/corpus_distilled plan fields.
- feedback_status: items-recorded

### SF-004 (filed: https://github.com/haydenrear/tla-spec-dev/issues/108) — the minimal YAML fallback parser could not read the repository's own manifests

- category: profile-schema-cli
- target: scripts/extract_spec_manifest.py::_parse_list
- observed_on: tla-spec-dev @ MF-014
- evidence: specs/tickets/MF-014/results/complexity-ledger.md
- severity: silent-wrong-result
- root_cause: tool
- surface: every budget gate, via scripts/budgets.py::load_budgets
- data_loss: no, but every gate read the WRONG thresholds
- note: `_parse_list` raised "unexpected indentation" on a plain-scalar list
  item wrapped onto continuation lines, which `specs/current/spec_manifest.yaml`
  contains. PyYAML is an optional dependency and is absent in this environment
  (`uv run --with pytest python -c "import yaml"` fails), so the fallback parser
  is the ONLY parser. The parse failure was swallowed by
  `budgets._read_manifest`, which returns None on any exception, so
  `load_budgets` fell back to documented defaults with a warning. Net effect: a
  negotiated budget recorded in the manifest was silently ignored by
  `analyze complexity`, case generation, and the adapter runner. This ticket's
  entire "raise the cap with a rationale" accept path would have been a no-op.
- workaround_applied: none — fixed at the source in this ticket by folding
  continuation lines into the scalar, per YAML semantics
- recommendation: (none yet) — the parse bug is fixed, but the SHAPE of the
  defect remains: `_read_manifest` catches bare `Exception` and returns None,
  converting any future parser gap into a silent downgrade to defaults. That is
  the "fall back to default budgets with a warning" degeneracy already named in
  architecture_tractability.md "No Degenerate Escapes". MF-023 absorbed the
  purge of that fallback from the withdrawn MF-024 and should treat a manifest
  that exists but cannot be parsed as a hard failure, distinct from a manifest
  that is absent.
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/108

### SF-005 (filed: https://github.com/haydenrear/tla-spec-dev/issues/109) — a corpus documented in four places as committed is not committed

- category: docs-and-examples
- target: references/examples.md:48, references/edge-cases.md:84,
  references/testgraph_adapters.md:141, examples/distributed_history/README.md:34
- observed_on: tla-spec-dev @ MF-014
- evidence: specs/tickets/MF-014/results/deferred-validations.md
- severity: friction
- root_cause: spec
- gated_quantity: the 732-case ecommerce corpus named as this ticket's primary
  test fixture
- measured_quantity: 4 external traces + 4 external cases + 4 internal cases
  actually committed
- metric_blind_spot: the 732 figure is real but is produced at run time under
  `test_graph/build/validation-reports/<run>/`, which is not committed. The
  ticket, the issue, and the assignment all read the references as describing a
  committed artifact and pointed the implementer at
  `examples/distributed_history/specs/generated/testgraph/traces/`, which holds
  4 files. Under the epic-wide spec-case execution deferral the corpus cannot be
  regenerated to check, so the divergence is only discoverable by opening the
  directory.
- workaround_applied: reconstructed the documented distribution as
  `tests/corpus_fixtures.py`, labelled a fixture in its module docstring, and
  additionally ran the CLI against the genuinely committed 4-case corpus so at
  least one end-to-end path touches real artifacts
- recommendation: (none yet) — recommend the reference text state explicitly
  that the 732-case corpus is regenerated per run and not committed, and that
  MF-023 re-run `tla-spec-dev analyze corpus` against the real regenerated
  output and record the actual distribution
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/109

### SF-006 (filed: https://github.com/haydenrear/tla-spec-dev/issues/110) — plan prescribed model state for a scope that had been withdrawn

- category: budget-and-metric
- target: specs/desired_program_model/ticket_plan.yaml — MF-014
  `desired_actions: [DistillCorpus]` / `current_increment.model_state:
  [corpus_distilled]`
- observed_on: tla-spec-dev @ MF-014
- evidence: specs/tickets/MF-014/results/complexity-ledger.md
- severity: friction
- root_cause: spec
- gated_quantity: prescribed model state (DistillCorpus, corpus_distilled)
- measured_quantity: what the replaced scope actually needs (corpus_gate,
  AnalyzeCorpus)
- metric_blind_spot: this is the FOURTH instance of the SF-002 pattern
  (MF-011, MF-020, MF-017, now MF-014), and the first where the prescribed
  fields name a mechanism the same commit WITHDREW. The objective, acceptance
  criteria, and referenced ticket file were all rewritten for the diagnostics
  scope while `desired_actions`/`model_state` kept describing distillation.
  Implementing them literally would have built the filter the ticket exists to
  forbid.
- workaround_applied: implemented the gate the replaced scope requires and
  recorded the deviation in the plan entry's `outcome:` field, per the MF-017
  precedent
- recommendation: (none yet) — reinforces SF-002. A scope replacement should be
  required to rewrite or explicitly null the `desired_actions` /
  `current_increment` fields in the same change, since a stale prescription
  that contradicts the new objective is worse than an absent one
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/110

Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-025

- close_scope: ticket
- close_id: MF-025
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-18T23:11:53+00:00
- summary: MF-025: collapse active_tickets, closed_tickets and ticket_phase into one ticket_state ordinal (0..5). Premise re-verified with TLC in both directions. Retention exact: 9,011 distinct / depth 24 / 87,464 generated, unchanged. Declared bound measured 663,552 -> 34,992 (18.96x).
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-015

- close_scope: ticket
- close_id: MF-015
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-19T18:23:24+00:00
- summary: MF-015: external channel enforcement. Required channel per Test Graph binding (http/cli/fs/queue/k8s, explicitly extensible), transitive static import analysis proving no Test Graph adapter imports the declared production package, violations reported with adapter/import/remediation, and required double|real port binding configurations with at least one real port so graph runs express integration-ladder rungs. Shared gate in scripts/testgraph_channels.py applied by both run_generated_case_adapters.py (external view) and export_testgraph_cases.py. Zero model delta, reasoned and recorded: the gates are Test-Graph-invoked and no modeled CLI command reaches them. TLC 87,464/9,011/depth 24 and bound 34,992 identical to baseline; 226 repository tests, 27+24 spec-unit, specWorkflow 8/8, cliWorkflow 2/2.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-013

- close_scope: ticket
- close_id: MF-013
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-19T18:59:05+00:00
- summary: Effect conformance harness: declared typed emissions on named ports, sandboxed passive observation, per-case diff. Undeclared observed effect recorded AND FAILS; dead declared surface FAILS; nothing suppresses a gap report (out-of-contract justifications withdrawn 2026-07-18), proven by the inverse test. Spec-case execution deferred to MF-023.
- feedback_status: items-recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

### SF-007 (filed: https://github.com/haydenrear/tla-spec-dev/issues/111) — three manifest parsers disagreed on the repository's own manifest, and the strictest one blocked close

- category: profile-schema-cli
- target: scripts/extract_spec_manifest.py::load_manifest vs scripts/budgets.py::_read_manifest vs the PyYAML parse on the close path
- observed_on: tla-spec-dev @ MF-013, specs/current/spec_manifest.yaml inherited from epic tip 1dcce07 (written by MF-015)
- evidence: specs/.history/modular-fuzzing-epic/ticket-006-MF-013/results/manifest_parser_disagreement.txt
- severity: blocks-migration
- root_cause: tool
- surface: every gate that reads spec_manifest.yaml, plus `close ticket`
- data_loss: no
- note: RECURRENCE of SF-004. An unquoted block-sequence scalar containing a
  colon-space ("... for this ticket: case generation over the") made the file
  invalid YAML. Three parsers, three outcomes on the identical file:
  `extract_spec_manifest.load_manifest` ACCEPTED it and returned budgets;
  `budgets.load_budgets` returned source=None and silently fell back to
  documented defaults, emitting the "no readable spec manifest" warning on
  every `analyze complexity` run for the whole epic; PyYAML on the close path
  raised ScannerError and ABORTED `close ticket MF-013`. So "the manifest"
  meant three different things to three different gates, and the budget gate
  spent the epic reading defaults rather than the declared file. The declared
  values equal the defaults here, so no verdict was wrong -- but a deliberately
  raised budget, which is the doctrine's sanctioned accept path, would have
  been silently ignored. MF-013 is simply the first close to reach the strict
  parser.
- workaround_applied: none — fixed at the source by quoting the scalar (`- >-`),
  wording unchanged; both ticket-local manifests and the promoted
  specs/current/spec_manifest.yaml now parse under all three parsers
- recommendation: SF-004's recommendation, unactioned since MF-014, is what
  would have prevented this: treat a manifest that EXISTS but cannot be parsed
  as a hard failure, distinct from one that is ABSENT. Add to that: the
  repository should have ONE manifest parser. Three parsers with three
  tolerances mean a file can be simultaneously valid and invalid depending on
  which gate reads it, and the most permissive one hides the defect from the
  gates while the strictest one surfaces it only at close. Absorbed into
  MF-023 with SF-004; not filed as a separate issue because it is the same
  defect class and splitting it would fragment the fix.
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/111

## Close-out ticket MF-027

- close_scope: ticket
- close_id: MF-027
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-19T19:50:48+00:00
- summary: MF-027: effect oracle refuses targets it cannot observe. Observability granted only on positive in-process evidence; unobservable targets and subprocess boundaries FAIL with explicit findings; inverse test proves no config downgrades the verdict; External/test-graph gap documented with follow-up #44.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-016

- close_scope: ticket
- close_id: MF-016
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-19T21:17:14+00:00
- summary: MF-016: mutation kill test (oracle 4). Coverage derived from port/invariant declarations every run; control run refuses a red corpus; kill_rate_floor gate fails below floor with no waiver; survivors point at the variable and action to refine; abstraction validator via --baseline/--compare. Mechanism built and unit/adapter/example-validated; empirical proof over this repository's corpus deferred to MF-023 per epic policy.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-019

- close_scope: ticket
- close_id: MF-019
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-19T22:44:51+00:00
- summary: Mechanize the standing objective: complexity ledger recorded per ticket/workflow close with the delta reported jointly with retention evidence; increases require a recorded justification; a decrease with degraded or unverified retention is rejected at close; the MF-020 self-loop red flag is a hard gate; and the recursive refinement record is required. Zero model delta -- max_state_space_bound is at 70.0% with 1.43x headroom, so no new bounded variable of any cardinality fits; recorded as a finding for MF-023.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-026

- close_scope: ticket
- close_id: MF-026
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-19T23:36:50+00:00
- summary: MF-026: coverage audit gate -- prompt, report template, doctrine, ledger recording, and a worked example that found 19 in-scope gaps and real defects in the prompt itself. Zero model delta.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-028

- close_scope: ticket
- close_id: MF-028
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-20T01:23:00+00:00
- summary: Spike: measured the cost of case execution. One adapter (ScaffoldProject) executes one generated case end to end through the real runner -- before-state materialized by CLI prefix replay, action executed, after-state projected from the filesystem, 9 fields checked, 2 declared unchecked, 3 negative controls rejected. Before-state materialization -- the predicted hard part -- is cheap and ~100% shared. Found four structural blockers the ticket did not anticipate: all 57,617 cases carry empty action params (parameterized actions untestable); UpdateTicketDesired/UpdateTicketCurrent have no adapter, blocking 72.5% of the corpus; 16 adapters cover only 13 labels with 3 colliding on CloseTicket; and the effect oracle moved from 0 to 6 observed effects but still refuses as unobservable because every adapter shells out. run() alone does not restore oracle 3.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-029

- close_scope: ticket
- close_id: MF-029
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-20T02:25:41+00:00
- summary: MF-029: recover action parameters from each case's before/after state pair, generator-side. Zero TLA+ model delta. Audited all 14 action labels plus Stutter: 9 guard-pinned, 5 except-index, 1 written-through (ScaffoldProject, the only action that sacrifices an after-state check), 1 UNRECOVERABLE (RunSpecUnitTests override) marked UNCHECKED and never fabricated. 14/14 negative controls verified to fail; 6/6 implementation mutations caught after closing an initially-surviving before-vs-after mutation. No case dropped: 798,411 TLC transitions in, 798,411 cases out.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-030

- close_scope: ticket
- close_id: MF-030
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-20T22:09:21+00:00
- summary: Resolve EXTENDS in analyze_complexity: follow the module hierarchy and union VARIABLES/CONSTANTS/definitions; fail closed (named errors) on INSTANCE, WITH substitution, parameterized instantiation, LOCAL, and unresolved EXTENDS. Zero TLA+ model delta (TLC 231,621 distinct/depth 25; binding bound 699,840 unchanged). Regression proves bound moves 1->4 across an EXTENDS edge and fails pre-fix. Shipped example re-measured: External verdict diagnosis corrected from spurious 'C2 {responses} 9 actions' to true 'C1 13 actions' over all 10 variables (relevant to MF-037).
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-036

- close_scope: ticket
- close_id: MF-036
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-20T23:03:55+00:00
- summary: Made complexity advisory: analyze complexity and case generation no longer block or refuse over threshold (exit 0 with warnings + recommendations); only an unanalyzable model (ModuleResolutionError) still exits nonzero. Fixed the v'=v frame-condition R/W over-count. Zero TLA delta; TLC 231,621 distinct/depth 25.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-031

- close_scope: ticket
- close_id: MF-031
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-21T00:38:02+00:00
- summary: MF-031: UpdateTicketDesired/UpdateTicketCurrent adapters made case-executable via ticket-segment materialization; CloseTicket collision characterized as a binding-model limitation
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-032

- close_scope: ticket
- close_id: MF-032
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-21T01:35:18+00:00
- summary: Give run() to InstallLocalCli, ScaffoldWorkflow, RecordBudgets, OpenTicket (4 adapters now execute cases); promote the shared before-state builder/projector as module adapter_case_runtime.py (not a base class); fix the runner all-or-nothing == to per-field honoring UNCHECKED. Remaining adapters stay apply()-only for structural reasons (reported). Executability 7.8%->9.8% (both axes), re-measured. Zero TLA+ delta.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-033

- close_scope: ticket
- close_id: MF-033
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-21T02:12:02+00:00
- summary: Effect oracle observes out-of-process child effects via WorkingTreeObserver snapshot diff; MF-027 polarity preserved; cost report recommends running oracles advisorily.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-038

- close_scope: ticket
- close_id: MF-038
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-21T11:30:31+00:00
- summary: MF-038 kill-rate probe: control GREEN on the reduced runnable corpus; kill rate 4/13=0.308; all 9 subtle content/value/field bugs SURVIVED, only 4 structural directory/tree bugs killed. Cases are existence-and-exit-code oracles, not content oracles. Zero model delta. Recommendation: not yet ship-worthy as case-advising until file/field content is projected into model variables.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-023

- close_scope: ticket
- close_id: MF-023
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-21T12:01:44+00:00
- summary: MF-023: dogfooded the complexity scanner on this repo (advisory report recorded; suggested move ABSTRACT, modularity Q=0.012, one advisory C1 warning, exit 0); took no refactor with recorded reasoning; rewrote SKILL.md + references/modular_fuzzing.md + references/architecture_tractability.md to present the scanner as the shipped advisory feature and demote the fuzzing/oracle/kill-test machinery to EXPERIMENTAL not-validated-for-bug-catching, citing kill rate 0.31 / 0-of-9 and the Hypothesis-arm stub; zero TLA+ model delta.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CD-01

- close_scope: ticket
- close_id: CD-01
- workflow: complexity-descriptor-epic
- closed_at: 2026-07-22T00:16:40+00:00
- summary: CD-01: shipped the complexity descriptor -- removed all suggested-move machinery (abstract/decompose/refactor), fixed F1 (transitive invariant alias/composition resolution) and F3 (explicit-unknown bound, never a silent 1); docs present the descriptor as the shipped surface; zero TLA model delta, TLC green at 231,621 distinct / depth 25
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CD-02

- close_scope: ticket
- close_id: CD-02
- workflow: complexity-descriptor-epic
- closed_at: 2026-07-22T00:45:24+00:00
- summary: CD-02: complexity intuition — references/complexity_intuition.md teaches reading a descriptor as refactoring input (good/bad shapes, five real-run worked examples, how-complex-should-a-program-be best practices, validated refactors encouraged as normal practice, intuitions never automated moves); SKILL.md wires the take-this-descriptor-to-refactor framing; zero TLA model delta, TLC green 231,621 distinct
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CD-03

- close_scope: ticket
- close_id: CD-03
- workflow: complexity-descriptor-epic
- closed_at: 2026-07-22T01:09:34+00:00
- summary: CD-03: self-configurable composable fitness functions over the complexity descriptor — scripts/fitness_functions.py ({fact,op,value} leaves over published descriptor facts incl. parameterized variable_domain(v), composed with all/any/not under three-valued Kleene semantics); per-project persistence in spec_manifest.yaml fitness_functions: or sibling fitness_functions.yaml/.json (json is stdlib-only for the bare-python3 CLI); analyze complexity evaluates rules each scan and surfaces FIRED rules with leaf-level traces as notifications to future agents; advisory throughout (exit code unchanged; broken config is an advisory CONFIG ERROR); NO built-in rules; worked example recorded (two composed rules, later scan surfaces one firing); zero TLA model delta, TLC green 231,621 distinct
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CD-09

- close_scope: ticket
- close_id: CD-09
- workflow: complexity-descriptor-epic
- closed_at: 2026-07-22T17:53:01+00:00
- summary: CD-09 audit reconciliation: advisory-faithful model (override + blocking gate + SpecUnitTestsRequireAnalyzedGate removed, TLC 231,621 -> 283,805 distinct at depth 25), dead tlc_process port removed (17/17 boundaries seeded), case_adapters.toml reconciled to the exact 14-action set, complexity ledger amended to the owner-approved validated-refactor retention basis with fuzzing members recorded non-gating
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CD-10

- close_scope: ticket
- close_id: CD-10
- workflow: complexity-descriptor-epic
- closed_at: 2026-07-22T18:44:39+00:00
- summary: CD-10 manifest honesty: declared CloseTicket's destructive deletes (spec_tree_delete, filesystem.delete **/specs/** -- spec_evolution.py:154/:385/:477 incl. the GitHub #22 rmtree) and the real spawns of modeled actions (runner_process for RunSpecUnitTests' case-runner spawn tla_spec_dev.py:313-339/:358; git_metadata for CloseTicket's git rev-parse provenance spawn spec_evolution.py:99 via :801/:903); added the deliberate RecordBudgets: [] effects row (DF-2, no distinct effect); removed the dangling Core/Internal/External source_model references (DF-3); seeded one honest kill-catalog fault per new port, zero missing boundaries. Zero TLA+ model delta; TLC 283805 distinct states within the 500000 negotiated budget.
- feedback_status: none-found

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CD-11

- close_scope: ticket
- close_id: CD-11
- workflow: complexity-descriptor-epic
- closed_at: 2026-07-22T19:41:19+00:00
- summary: Port honesty for the experimental surface + the two four-run manifest desyncs (R4-1/2/3, ESC-R4-2/3): declared mutation_write and corpus_process on RunKillTest, spec_tree on RunEffectConformance, removed AnalyzeCorpus's dead evidence_report; placeholder meaning recorded for the empty state_fields/actions/ports stanzas; @port vocabulary aligned to declared port names; kill catalog 22/22; zero TLA+ semantic delta (TLC 283,805 distinct, identical to baseline)
- feedback_status: none-found

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out workflow complexity-descriptor-epic

- close_scope: workflow
- close_id: complexity-descriptor-epic
- workflow: complexity-descriptor-epic
- closed_at: 2026-07-22T19:59:04+00:00
- summary: Complexity-descriptor epic closed: CD-01 factual descriptor (F1/F3), CD-02 complexity intuition, CD-03 advisory fitness functions, validated 6/6 by agent-example runs; CD-09/10/11 audit reconciliation (advisory-faithful model, honest ports/bindings/manifest, validated-refactor retention basis); coverage audit PASS at run 5 (0 gaps)
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CD-04

- close_scope: ticket
- close_id: CD-04
- workflow: complexity-descriptor-main-readiness
- closed_at: 2026-07-22T20:23:48+00:00
- summary: CD-04: corpus gate speaks a factual finding plus a redesign question (descriptor + complexity_intuition.md as judgment inputs), never a prescribed move; repo-wide suggestion sweep recorded with per-occurrence dispositions; refusal/accept semantics unchanged; zero TLA+ model delta
- feedback_status: none-found

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CD-05

- close_scope: ticket
- close_id: CD-05
- workflow: complexity-descriptor-main-readiness
- closed_at: 2026-07-22T20:36:11+00:00
- summary: Domain resolution sees operator-defined sets (VAL-06: _set_size expands zero-parameter operators transitively through EXTENDS, sizes [S -> T] as |T|^|S|), wrapped conjuncts (VAL-16: conjunct-wise constraint parsing via resolve_constraint_chunks), and multi-view invariant naming (VAL-17: per-variable domain-source merge in documented order TypeInvariant > TypeOK > cfg invariants). F3 explicit-UNKNOWN preserved; resolver coverage contract documented in references/architecture_tractability.md 'What The Domain Resolver Can And Cannot See', cited by scanner output. Three regression tests each proven failing pre-fix. Zero TLA+ model delta.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CD-08

- close_scope: ticket
- close_id: CD-08
- workflow: complexity-descriptor-main-readiness
- closed_at: 2026-07-22T20:47:17+00:00
- summary: distributed_history example passes its own documented workflow out of the box: example manifest cap 50->200 set to measured worst action with recorded rationale (VAL-08, nothing trimmed); regenerate_tlc_cases.py passes --bindings/--manifest to the exporter (VAL-09); export_testgraph_cases.py resolves the cap manifest from the spec root holding --bindings or fails loudly naming --manifest, regression-tested (VAL-10); TLA_SPEC_DEV_ROOT override in the example's three root-deriving scripts and a target-example-path argument on the validation wrapper (VAL-11); READMEs document the real envelope keys caseNames/expectedCaseNames (VAL-14); README counts point at generated docs.md, command echoes flushed, manual tlc2 -deadlock documented (VAL-18). Pristine scratch copy completed the documented local non-k3d path end to end before and after reconciling epic tip 5b7d09f: 93 internal + 732 external cases, cap gate and channel enforcement green. Zero TLA model delta; deferred CD-08-DF-01 (local-mode wrapper kill-test step).
- feedback_status: none-found

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CD-06

- close_scope: ticket
- close_id: CD-06
- workflow: complexity-descriptor-main-readiness
- closed_at: 2026-07-22T21:00:22+00:00
- summary: R/W matrix attributed to top-level Next disjuncts through called operators (VAL-07/VAL-12): wrapper actions priming only via helpers get columns, composed actions writing via called operators/UNCHANGED get columns, helpers are never columns; dense rows/columns, action counts, and fitness facts follow the corrected action set; fallback without a findable next-state relation is stated honestly; zero TLA+ model delta
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CD-07

- close_scope: ticket
- close_id: CD-07
- workflow: complexity-descriptor-main-readiness
- closed_at: 2026-07-22T21:25:34+00:00
- summary: Advisory-doctrine language and UX polish: scaffold epilog and generated manifests speak the advisory doctrine (VAL-04); manifest fitness rules under bare python3 emit the documented PyYAML CONFIG ERROR (VAL-01); retired fuzzing-era budget keys no longer warn (VAL-02); no-manifest warning names no sentinel path (CD-02-DF-01); justification-table schema documented (VAL-05); run_tlc.sh leaves no states/ scratch dir (VAL-03); write-only-state test added to the intuition doc from the recorded ex3 divergence (VAL-15); action_count fact description corrected (CD-06-DF-01). Zero TLA+ model delta.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

---

# Entries carried from effect-provider-epic (merge 2026-07-22)

## How to use this file

1. At each close-out the CLI appends a `## Close-out …` entry below.
2. Fill in that entry's `feedback_status`, then record one `### SF-NNN` finding
   per thing the skill could not express.
3. **Turn every finding into a ticket or PR against the spec-double-compiler
   repository** — that is the point of this file, not the record-keeping:

   ```
   gh issue create --repo haydenrear/tla-spec-dev \
     --title "<SF-NNN one-line title>" --body-file <extract of the finding>
   ```

   Then set `recommendation:` to the resulting URL and `status: filed`.
4. If you looked and there was genuinely nothing, set
   `feedback_status: none-found`. **Silence is not an answer** — an unreviewed
   entry is recorded as unresolved in the close history.

## The four prompt categories

- `surviving-mutants` — Surviving mutants
- `unmodelable-effects` — Unmodelable effects
- `budget-and-metric` — Budget adjustments and metric calibration
- `profile-schema-cli` — Profile, schema, and CLI workarounds

## Finding format

Every finding is a `### SF-NNN` heading followed by `- key: value` lines. The
close path parses these, so keep the shape.

Fields required on every finding:

- `category:` one of `surviving-mutants`, `unmodelable-effects`, `budget-and-metric`, `profile-schema-cli`
- `target:` the exact tool surface that proved inadequate — command, script
  path and function, budget key, profile rule, or manifest field. Not "the CLI".
- `observed_on:` the real repository/module/ticket it was run against. A finding
  without a real target is a wish, not evidence.
- `evidence:` a durable path (command output, TLC log, report) — not prose.
- `severity:` one of `blocks-migration`, `silent-data-loss`, `wrong-result`, `manual-workaround`, `friction`
- `root_cause:` one of `tool`, `spec`, `target`, `unknown` — whether the
  tool's code, its specification, or the target under migration was at fault.
  A correct implementation of a wrong spec is `spec`; filing it against the
  code files it in the wrong place.
- `workaround_applied:` what the migration had to do to proceed, or `none`.
- `recommendation:` `ticket <url>` or `PR <url>` against spec-double-compiler / tla-spec-dev
- `status:` `open`, `filed`, or `wontfix`

Category-specific fields, so the common cases are structured rather than prose:

- `surviving-mutants` — `mutant:`, `operator:`, `location:`, `why_unreached:`
  (which generator, strategy, or profile rule could not reach it)
- `unmodelable-effects` — `effect:`, `why_not_port_state:`, `modeled_as:`
  (or `unmodeled`)
- `budget-and-metric` — `budget_key:`, `default_value:`, `value_used:`,
  `gated_quantity:` vs `measured_quantity:` (name both when a gate compares
  quantities that are not commensurable), `metric_blind_spot:` (what a passing
  metric failed to notice)
- `profile-schema-cli` — `surface:`, `forced_workaround:`, `data_loss:`
  (`yes`/`no`)

## Worked examples

These are real findings this epic produced *before* this template existed. They
are the calibration for what a good finding looks like; they are recorded here
as `SF-000x` examples and are excluded from filing status.

### SF-000a — Projected complexity reduction required deleting real behavior
- category: budget-and-metric
- target: scripts/analyze_complexity.py — projected-reduction reporting
- observed_on: tla-spec-dev @ MF-020 (ticket_phase ordinal collapse)
- evidence: specs/.history/modular-fuzzing-epic/ticket-*-MF-020/
- severity: wrong-result
- root_cause: tool
- gated_quantity: distinct reachable states
- measured_quantity: generated states
- metric_blind_spot: deleted self-loops. Reproducing the projected -13.1%
  required tightening a guard from `>= 2` to `= 2`, deleting a legitimate
  idempotent re-fire transition. The distinct-state gate is structurally blind
  to that, so a behavior deletion scored as a re-representation win.
- workaround_applied: projection withdrawn by hand after transition-level diff
- recommendation: ticket (example only)
- status: wontfix

### SF-000b — Promotion destroyed files unique to specs/current
- category: profile-schema-cli
- target: scripts/spec_evolution.py::replace_tree (ticket-close promotion)
- observed_on: tla-spec-dev @ MF-012, MF-020, MF-021
- evidence: tests/test_promotion_preserves_current.py
- severity: silent-data-loss
- root_cause: tool
- surface: `tla-spec-dev close ticket` promotion step
- forced_workaround: restore deleted regression tests from git history
- data_loss: yes
- recommendation: ticket https://github.com/haydenrear/tla-spec-dev/issues/22
- status: filed

### SF-000c — PATH wrapper ran pre-epic code for an entire epic
- category: profile-schema-cli
- target: `tla-spec-dev` PATH wrapper -> ~/.skill-manager/skills/spec-double-compiler
- observed_on: tla-spec-dev @ modular-fuzzing epic (all tickets)
- evidence: specs/desired_program_model/ticket_plan.yaml (toolchain_rule)
- severity: wrong-result
- root_cause: tool
- surface: skill installation / PATH shim
- forced_workaround: pin every lifecycle command to
  `python3 scripts/tla_spec_dev.py --spec-root specs ...`
- data_loss: yes — the stale wrapper is why the promotion defect fired three
  times, including once after its fix had merged
- recommendation: ticket (example only)
- status: wontfix

### SF-000d — Bound gate compared incommensurable quantities
- category: budget-and-metric
- target: scripts/analyze_complexity.py — state-space bound gate
- observed_on: tla-spec-dev @ MF-011
- evidence: specs/.history/modular-fuzzing-epic/ticket-*-MF-011/
- severity: blocks-migration
- root_cause: spec
- budget_key: max_distinct_states
- default_value: 50000
- value_used: new `max_state_space_bound` added (MF-022)
- gated_quantity: static state-space upper bound (1,179,648)
- measured_quantity: actual reachable distinct states (2,923)
- metric_blind_spot: a ~400x over-approximation failed a model 17x *under* its
  own budget; the tool's own recommended optimum still failed the gate.
- workaround_applied: none — gate reported its own failure rather than tuning
- recommendation: ticket https://github.com/haydenrear/tla-spec-dev/issues/28
- status: filed

---

## Close-out ticket MF-017

- close_scope: ticket
- close_id: MF-017
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-18T21:40:12+00:00
- summary: MF-017: close-out emits the migration.md Phase 6 skill-feedback retro into specs/results/skill_feedback.md (four prompt categories, structured findings, filing instructions against spec-double-compiler) and records in the append-only history whether feedback was filed and where. Zero model delta: close-out gains a file effect, not a command (MF-021 precedent).
- feedback_status: items-recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

### SF-001 (filed: https://github.com/haydenrear/tla-spec-dev/issues/105) — scaffolded fixture workflow cannot exercise two consecutive closes
- category: profile-schema-cli
- target: scripts/scaffold_spec_workflow.py — emitted desired_program_model/ticket_plan.yaml
- observed_on: tla-spec-dev @ MF-017 (SkillFeedbackCloseOutAdapter)
- evidence: specs/current/production_adapters.py::SkillFeedbackCloseOutAdapter
- severity: manual-workaround
- root_cause: tool
- surface: `tla-spec-dev scaffold workflow`
- forced_workaround: the adapter hand-appends a second ticket entry to
  ticket_plan.yaml before the second `open ticket`, because the scaffolded plan
  contains exactly one ticket and `close ticket` refuses an id that is not in
  the plan.
- data_loss: no
- note: any behavior that only appears ACROSS closes — accumulation,
  append-only-ness, history sequencing — is untestable against the stock
  fixture without this workaround. That is a class of regression the fixture
  currently cannot catch.
- recommendation: (none yet) — recommend a `--tickets N` option on
  `scaffold workflow`, or a multi-ticket fixture plan, so cross-close behavior
  is testable without hand-editing YAML
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/105

### SF-002 (filed: https://github.com/haydenrear/tla-spec-dev/issues/106) — plan prescribed model state that implementation showed to be wrong
- category: budget-and-metric
- target: specs/desired_program_model/ticket_plan.yaml — per-ticket
  `desired_actions` / `current_increment.model_state`
- observed_on: tla-spec-dev @ MF-017
- evidence: specs/tickets/MF-017/results/complexity-ledger.md
- severity: friction
- root_cause: spec
- gated_quantity: prescribed model state (`skill_feedback`, `EmitSkillFeedback`)
- measured_quantity: actual model delta after implementation (zero)
- metric_blind_spot: the plan fields are written at scheduling time and are
  never reconciled against what implementation proves. MF-011 and MF-020 each
  hit the same shape (a spec-level error with a correct implementation); this
  is the third instance, so it is a pattern, not an accident. Implementing the
  prescription literally would have cost bound 221,184 -> 663,552 to represent
  a document field.
- workaround_applied: implemented at zero delta and recorded an `outcome:` field
  on the plan entry explaining the deviation, for post-merge review
- recommendation: (none yet) — recommend the close path diff prescribed
  `desired_actions`/`model_state` against the promoted model and require an
  explicit `outcome:` when they disagree, rather than leaving the plan silently
  contradicting the accepted model
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/106

### SF-003 (filed: https://github.com/haydenrear/tla-spec-dev/issues/107) — promotion silently discards edits to seeded specs/current files
- category: profile-schema-cli
- target: scripts/spec_evolution.py::promote_current_tree — promotion report
- observed_on: tla-spec-dev @ MF-017 (specs/current/spec_manifest.yaml)
- evidence: specs/tickets/MF-017/results/complexity-ledger.md
- severity: manual-workaround
- root_cause: tool
- surface: `tla-spec-dev close ticket` promotion step
- forced_workaround: reapply the edit to specs/current after close and commit it
  separately
- data_loss: yes — recoverable, but silent
- note: MF-021 made promotion enumerate what it REMOVED and PRESERVED, which is
  why this was caught at all. It does not enumerate what it OVERWROTE. An edit
  made to a seeded specs/current file during a ticket is reverted by promotion
  with no mention in the report, and the close still reports success. The
  overwrite itself is correct (specs/current is a working copy promoted from the
  ticket); the silence is not.
- recommendation: (none yet) — recommend the promotion report also enumerate
  overwritten paths whose content changed, the same way it already enumerates
  removed and preserved paths
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/107

## Close-out ticket MF-014

- close_scope: ticket
- close_id: MF-014
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-18T22:39:57+00:00
- summary: Corpus diagnostics and hard case caps. Case caps are hard gates in the shape of MF-011's state-space bound: over budget reports and exits nonzero, never trims. No code path drops, filters, samples, or truncates a case to fit a budget. Diagnostics report count per (action, label class), dominant and starved strata, and what varies across the redundant group, classified into unconstrained ordering / interchangeable values / action enabled across equivalent states. Labelers repurposed to diagnostic strata; remediation is a recommendation requiring user approval; named regression traces always retained. Accept path is raising the cap in spec_manifest.yaml with a recorded rationale. Model delta: corpus_gate + AnalyzeCorpus, 8->9 vars, 11->12 actions, deviating from the stale DistillCorpus/corpus_distilled plan fields.
- feedback_status: items-recorded

### SF-004 (filed: https://github.com/haydenrear/tla-spec-dev/issues/108) — the minimal YAML fallback parser could not read the repository's own manifests

- category: profile-schema-cli
- target: scripts/extract_spec_manifest.py::_parse_list
- observed_on: tla-spec-dev @ MF-014
- evidence: specs/tickets/MF-014/results/complexity-ledger.md
- severity: silent-wrong-result
- root_cause: tool
- surface: every budget gate, via scripts/budgets.py::load_budgets
- data_loss: no, but every gate read the WRONG thresholds
- note: `_parse_list` raised "unexpected indentation" on a plain-scalar list
  item wrapped onto continuation lines, which `specs/current/spec_manifest.yaml`
  contains. PyYAML is an optional dependency and is absent in this environment
  (`uv run --with pytest python -c "import yaml"` fails), so the fallback parser
  is the ONLY parser. The parse failure was swallowed by
  `budgets._read_manifest`, which returns None on any exception, so
  `load_budgets` fell back to documented defaults with a warning. Net effect: a
  negotiated budget recorded in the manifest was silently ignored by
  `analyze complexity`, case generation, and the adapter runner. This ticket's
  entire "raise the cap with a rationale" accept path would have been a no-op.
- workaround_applied: none — fixed at the source in this ticket by folding
  continuation lines into the scalar, per YAML semantics
- recommendation: (none yet) — the parse bug is fixed, but the SHAPE of the
  defect remains: `_read_manifest` catches bare `Exception` and returns None,
  converting any future parser gap into a silent downgrade to defaults. That is
  the "fall back to default budgets with a warning" degeneracy already named in
  architecture_tractability.md "No Degenerate Escapes". MF-023 absorbed the
  purge of that fallback from the withdrawn MF-024 and should treat a manifest
  that exists but cannot be parsed as a hard failure, distinct from a manifest
  that is absent.
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/108

### SF-005 (filed: https://github.com/haydenrear/tla-spec-dev/issues/109) — a corpus documented in four places as committed is not committed

- category: docs-and-examples
- target: references/examples.md:48, references/edge-cases.md:84,
  references/testgraph_adapters.md:141, examples/distributed_history/README.md:34
- observed_on: tla-spec-dev @ MF-014
- evidence: specs/tickets/MF-014/results/deferred-validations.md
- severity: friction
- root_cause: spec
- gated_quantity: the 732-case ecommerce corpus named as this ticket's primary
  test fixture
- measured_quantity: 4 external traces + 4 external cases + 4 internal cases
  actually committed
- metric_blind_spot: the 732 figure is real but is produced at run time under
  `test_graph/build/validation-reports/<run>/`, which is not committed. The
  ticket, the issue, and the assignment all read the references as describing a
  committed artifact and pointed the implementer at
  `examples/distributed_history/specs/generated/testgraph/traces/`, which holds
  4 files. Under the epic-wide spec-case execution deferral the corpus cannot be
  regenerated to check, so the divergence is only discoverable by opening the
  directory.
- workaround_applied: reconstructed the documented distribution as
  `tests/corpus_fixtures.py`, labelled a fixture in its module docstring, and
  additionally ran the CLI against the genuinely committed 4-case corpus so at
  least one end-to-end path touches real artifacts
- recommendation: (none yet) — recommend the reference text state explicitly
  that the 732-case corpus is regenerated per run and not committed, and that
  MF-023 re-run `tla-spec-dev analyze corpus` against the real regenerated
  output and record the actual distribution
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/109

### SF-006 (filed: https://github.com/haydenrear/tla-spec-dev/issues/110) — plan prescribed model state for a scope that had been withdrawn

- category: budget-and-metric
- target: specs/desired_program_model/ticket_plan.yaml — MF-014
  `desired_actions: [DistillCorpus]` / `current_increment.model_state:
  [corpus_distilled]`
- observed_on: tla-spec-dev @ MF-014
- evidence: specs/tickets/MF-014/results/complexity-ledger.md
- severity: friction
- root_cause: spec
- gated_quantity: prescribed model state (DistillCorpus, corpus_distilled)
- measured_quantity: what the replaced scope actually needs (corpus_gate,
  AnalyzeCorpus)
- metric_blind_spot: this is the FOURTH instance of the SF-002 pattern
  (MF-011, MF-020, MF-017, now MF-014), and the first where the prescribed
  fields name a mechanism the same commit WITHDREW. The objective, acceptance
  criteria, and referenced ticket file were all rewritten for the diagnostics
  scope while `desired_actions`/`model_state` kept describing distillation.
  Implementing them literally would have built the filter the ticket exists to
  forbid.
- workaround_applied: implemented the gate the replaced scope requires and
  recorded the deviation in the plan entry's `outcome:` field, per the MF-017
  precedent
- recommendation: (none yet) — reinforces SF-002. A scope replacement should be
  required to rewrite or explicitly null the `desired_actions` /
  `current_increment` fields in the same change, since a stale prescription
  that contradicts the new objective is worse than an absent one
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/110

Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-025

- close_scope: ticket
- close_id: MF-025
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-18T23:11:53+00:00
- summary: MF-025: collapse active_tickets, closed_tickets and ticket_phase into one ticket_state ordinal (0..5). Premise re-verified with TLC in both directions. Retention exact: 9,011 distinct / depth 24 / 87,464 generated, unchanged. Declared bound measured 663,552 -> 34,992 (18.96x).
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-015

- close_scope: ticket
- close_id: MF-015
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-19T18:23:24+00:00
- summary: MF-015: external channel enforcement. Required channel per Test Graph binding (http/cli/fs/queue/k8s, explicitly extensible), transitive static import analysis proving no Test Graph adapter imports the declared production package, violations reported with adapter/import/remediation, and required double|real port binding configurations with at least one real port so graph runs express integration-ladder rungs. Shared gate in scripts/testgraph_channels.py applied by both run_generated_case_adapters.py (external view) and export_testgraph_cases.py. Zero model delta, reasoned and recorded: the gates are Test-Graph-invoked and no modeled CLI command reaches them. TLC 87,464/9,011/depth 24 and bound 34,992 identical to baseline; 226 repository tests, 27+24 spec-unit, specWorkflow 8/8, cliWorkflow 2/2.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-013

- close_scope: ticket
- close_id: MF-013
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-19T18:59:05+00:00
- summary: Effect conformance harness: declared typed emissions on named ports, sandboxed passive observation, per-case diff. Undeclared observed effect recorded AND FAILS; dead declared surface FAILS; nothing suppresses a gap report (out-of-contract justifications withdrawn 2026-07-18), proven by the inverse test. Spec-case execution deferred to MF-023.
- feedback_status: items-recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

### SF-007 (filed: https://github.com/haydenrear/tla-spec-dev/issues/111) — three manifest parsers disagreed on the repository's own manifest, and the strictest one blocked close

- category: profile-schema-cli
- target: scripts/extract_spec_manifest.py::load_manifest vs scripts/budgets.py::_read_manifest vs the PyYAML parse on the close path
- observed_on: tla-spec-dev @ MF-013, specs/current/spec_manifest.yaml inherited from epic tip 1dcce07 (written by MF-015)
- evidence: specs/.history/modular-fuzzing-epic/ticket-006-MF-013/results/manifest_parser_disagreement.txt
- severity: blocks-migration
- root_cause: tool
- surface: every gate that reads spec_manifest.yaml, plus `close ticket`
- data_loss: no
- note: RECURRENCE of SF-004. An unquoted block-sequence scalar containing a
  colon-space ("... for this ticket: case generation over the") made the file
  invalid YAML. Three parsers, three outcomes on the identical file:
  `extract_spec_manifest.load_manifest` ACCEPTED it and returned budgets;
  `budgets.load_budgets` returned source=None and silently fell back to
  documented defaults, emitting the "no readable spec manifest" warning on
  every `analyze complexity` run for the whole epic; PyYAML on the close path
  raised ScannerError and ABORTED `close ticket MF-013`. So "the manifest"
  meant three different things to three different gates, and the budget gate
  spent the epic reading defaults rather than the declared file. The declared
  values equal the defaults here, so no verdict was wrong -- but a deliberately
  raised budget, which is the doctrine's sanctioned accept path, would have
  been silently ignored. MF-013 is simply the first close to reach the strict
  parser.
- workaround_applied: none — fixed at the source by quoting the scalar (`- >-`),
  wording unchanged; both ticket-local manifests and the promoted
  specs/current/spec_manifest.yaml now parse under all three parsers
- recommendation: SF-004's recommendation, unactioned since MF-014, is what
  would have prevented this: treat a manifest that EXISTS but cannot be parsed
  as a hard failure, distinct from one that is ABSENT. Add to that: the
  repository should have ONE manifest parser. Three parsers with three
  tolerances mean a file can be simultaneously valid and invalid depending on
  which gate reads it, and the most permissive one hides the defect from the
  gates while the strictest one surfaces it only at close. Absorbed into
  MF-023 with SF-004; not filed as a separate issue because it is the same
  defect class and splitting it would fragment the fix.
- status: filed
- reference: https://github.com/haydenrear/tla-spec-dev/issues/111

## Close-out ticket MF-027

- close_scope: ticket
- close_id: MF-027
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-19T19:50:48+00:00
- summary: MF-027: effect oracle refuses targets it cannot observe. Observability granted only on positive in-process evidence; unobservable targets and subprocess boundaries FAIL with explicit findings; inverse test proves no config downgrades the verdict; External/test-graph gap documented with follow-up #44.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-016

- close_scope: ticket
- close_id: MF-016
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-19T21:17:14+00:00
- summary: MF-016: mutation kill test (oracle 4). Coverage derived from port/invariant declarations every run; control run refuses a red corpus; kill_rate_floor gate fails below floor with no waiver; survivors point at the variable and action to refine; abstraction validator via --baseline/--compare. Mechanism built and unit/adapter/example-validated; empirical proof over this repository's corpus deferred to MF-023 per epic policy.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-019

- close_scope: ticket
- close_id: MF-019
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-19T22:44:51+00:00
- summary: Mechanize the standing objective: complexity ledger recorded per ticket/workflow close with the delta reported jointly with retention evidence; increases require a recorded justification; a decrease with degraded or unverified retention is rejected at close; the MF-020 self-loop red flag is a hard gate; and the recursive refinement record is required. Zero model delta -- max_state_space_bound is at 70.0% with 1.43x headroom, so no new bounded variable of any cardinality fits; recorded as a finding for MF-023.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-026

- close_scope: ticket
- close_id: MF-026
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-19T23:36:50+00:00
- summary: MF-026: coverage audit gate -- prompt, report template, doctrine, ledger recording, and a worked example that found 19 in-scope gaps and real defects in the prompt itself. Zero model delta.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-028

- close_scope: ticket
- close_id: MF-028
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-20T01:23:00+00:00
- summary: Spike: measured the cost of case execution. One adapter (ScaffoldProject) executes one generated case end to end through the real runner -- before-state materialized by CLI prefix replay, action executed, after-state projected from the filesystem, 9 fields checked, 2 declared unchecked, 3 negative controls rejected. Before-state materialization -- the predicted hard part -- is cheap and ~100% shared. Found four structural blockers the ticket did not anticipate: all 57,617 cases carry empty action params (parameterized actions untestable); UpdateTicketDesired/UpdateTicketCurrent have no adapter, blocking 72.5% of the corpus; 16 adapters cover only 13 labels with 3 colliding on CloseTicket; and the effect oracle moved from 0 to 6 observed effects but still refuses as unobservable because every adapter shells out. run() alone does not restore oracle 3.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-029

- close_scope: ticket
- close_id: MF-029
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-20T02:25:41+00:00
- summary: MF-029: recover action parameters from each case's before/after state pair, generator-side. Zero TLA+ model delta. Audited all 14 action labels plus Stutter: 9 guard-pinned, 5 except-index, 1 written-through (ScaffoldProject, the only action that sacrifices an after-state check), 1 UNRECOVERABLE (RunSpecUnitTests override) marked UNCHECKED and never fabricated. 14/14 negative controls verified to fail; 6/6 implementation mutations caught after closing an initially-surviving before-vs-after mutation. No case dropped: 798,411 TLC transitions in, 798,411 cases out.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-030

- close_scope: ticket
- close_id: MF-030
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-20T22:09:21+00:00
- summary: Resolve EXTENDS in analyze_complexity: follow the module hierarchy and union VARIABLES/CONSTANTS/definitions; fail closed (named errors) on INSTANCE, WITH substitution, parameterized instantiation, LOCAL, and unresolved EXTENDS. Zero TLA+ model delta (TLC 231,621 distinct/depth 25; binding bound 699,840 unchanged). Regression proves bound moves 1->4 across an EXTENDS edge and fails pre-fix. Shipped example re-measured: External verdict diagnosis corrected from spurious 'C2 {responses} 9 actions' to true 'C1 13 actions' over all 10 variables (relevant to MF-037).
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-036

- close_scope: ticket
- close_id: MF-036
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-20T23:03:55+00:00
- summary: Made complexity advisory: analyze complexity and case generation no longer block or refuse over threshold (exit 0 with warnings + recommendations); only an unanalyzable model (ModuleResolutionError) still exits nonzero. Fixed the v'=v frame-condition R/W over-count. Zero TLA delta; TLC 231,621 distinct/depth 25.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-031

- close_scope: ticket
- close_id: MF-031
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-21T00:38:02+00:00
- summary: MF-031: UpdateTicketDesired/UpdateTicketCurrent adapters made case-executable via ticket-segment materialization; CloseTicket collision characterized as a binding-model limitation
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-032

- close_scope: ticket
- close_id: MF-032
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-21T01:35:18+00:00
- summary: Give run() to InstallLocalCli, ScaffoldWorkflow, RecordBudgets, OpenTicket (4 adapters now execute cases); promote the shared before-state builder/projector as module adapter_case_runtime.py (not a base class); fix the runner all-or-nothing == to per-field honoring UNCHECKED. Remaining adapters stay apply()-only for structural reasons (reported). Executability 7.8%->9.8% (both axes), re-measured. Zero TLA+ delta.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-033

- close_scope: ticket
- close_id: MF-033
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-21T02:12:02+00:00
- summary: Effect oracle observes out-of-process child effects via WorkingTreeObserver snapshot diff; MF-027 polarity preserved; cost report recommends running oracles advisorily.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-038

- close_scope: ticket
- close_id: MF-038
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-21T11:30:31+00:00
- summary: MF-038 kill-rate probe: control GREEN on the reduced runnable corpus; kill rate 4/13=0.308; all 9 subtle content/value/field bugs SURVIVED, only 4 structural directory/tree bugs killed. Cases are existence-and-exit-code oracles, not content oracles. Zero model delta. Recommendation: not yet ship-worthy as case-advising until file/field content is projected into model variables.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket MF-023

- close_scope: ticket
- close_id: MF-023
- workflow: modular-fuzzing-epic
- closed_at: 2026-07-21T12:01:44+00:00
- summary: MF-023: dogfooded the complexity scanner on this repo (advisory report recorded; suggested move ABSTRACT, modularity Q=0.012, one advisory C1 warning, exit 0); took no refactor with recorded reasoning; rewrote SKILL.md + references/modular_fuzzing.md + references/architecture_tractability.md to present the scanner as the shipped advisory feature and demote the fuzzing/oracle/kill-test machinery to EXPERIMENTAL not-validated-for-bug-catching, citing kill rate 0.31 / 0-of-9 and the Hypothesis-arm stub; zero TLA+ model delta.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket EP-01

- close_scope: ticket
- close_id: EP-01
- workflow: effect-provider-epic
- closed_at: 2026-07-22T02:32:06+00:00
- summary: Added typed project-owned effect-provider lookup and failure-safe Python batch lifecycle with zero host TLA+ model delta.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket EP-02

- close_scope: ticket
- close_id: EP-02
- workflow: effect-provider-epic
- closed_at: 2026-07-22T04:19:37+00:00
- summary: Add deterministic provider campaigns, exact replay, project-owned helper scaffolds, and effect-safe lifecycle isolation with zero host-model delta.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket EP-03

- close_scope: ticket
- close_id: EP-03
- workflow: effect-provider-epic
- closed_at: 2026-07-22T06:52:37+00:00
- summary: Validated three preregistered effect-provider projects; Python V0 is a conditional go with parser, semantic-plan, signature, replay, bypass, and Java sequencing recommendations.
- feedback_status: none-found  # finalization review 2026-07-23: placeholder entry, no findings recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket EP-04

- close_scope: ticket
- close_id: EP-04
- workflow: effect-provider-epic
- closed_at: 2026-07-22T23:00:46+00:00
- summary: Replaced the public domain-flavored helper surface with one required agent-authored EffectProvider.bind(context) object contract; callable-only providers fail closed; scaffolds and authoring guidance are neutral; provider usage evidence is local; the historical twelve-gap example audit remains unchanged and explicitly scoped. Zero host-model delta.
- feedback_status: none-found

## Close-out ticket EP-05

- close_scope: ticket
- close_id: EP-05
- workflow: effect-provider-epic
- closed_at: 2026-07-22T23:13:47+00:00
- summary: Resolved DEF-001 through DEF-003: replay retains a dependency-bearing virtualenv, one constrained parser makes generated trees dependency-invariant and rejects inline maps, and binding methods must match generated arity plus parameter/return annotations before application execution. Zero host-model delta.
- feedback_status: none-found

## Close-out ticket EP-06

- close_scope: ticket
- close_id: EP-06
- workflow: effect-provider-epic
- closed_at: 2026-07-22T23:53:35+00:00
- summary: Revalidated three independent agent-authored provider consumers with repeatable non-overwriting evidence: 140 generated cases, 36 unique fixed mutants, 37 exact replays, 3140 clean lifecycle checks, and 70 real-boundary cases. Recorded the Python-first generic-interface recommendation with zero host-model delta.
- feedback_status: none-found

---

Finalization review 2026-07-23 (epic owner): SF-001..SF-007 filed as issues #105-#111 (links inline above); all placeholder entries reviewed and set none-found; the four pending backlog findings carried as issues #112-#115.

## Close-out workflow complexity-descriptor-main-readiness

- close_scope: workflow
- close_id: complexity-descriptor-main-readiness
- workflow: complexity-descriptor-main-readiness
- closed_at: 2026-07-23T21:22:33+00:00
- summary: Main-readiness workflow closed: CD-04..08 removed every validated negative side effect (redesign question, descriptor accuracy, advisory language, example repair); effect-provider epic merged with zero host-model delta and the composed surface validated by run-4 kill probes; coverage audit close-2 PASS (0 gaps); SF findings filed #105-#111, backlog carried #112-#115; promotion gate for main
- feedback_status: none-found  # finalization review 2026-07-23: no NEW findings at this close; all prior SF findings are status: filed with issue references (#105-#111)

## Close-out ticket CM-01

- close_scope: ticket
- close_id: CM-01
- workflow: architectural-coherence-epic
- closed_at: 2026-07-27T16:48:55+00:00
- summary: CM-01: declared model discovery (CM-F1 fixed), case_modules: manifest block, per-module action scope (CM-F2 fixed), and the per-action coverage aggregation report. Zero TLA+ model delta.
- feedback_status: unreviewed

## Close-out ticket AC-01

- close_scope: ticket
- close_id: AC-01
- workflow: architectural-coherence-epic
- closed_at: 2026-07-27T16:40:39+00:00
- summary: AC-01: analyze architecture -- components, per-variable writers and single-writer violations, ports, spanning actions; JSON descriptor (schema v1) for AC-02/AC-03; architecture_scan + AnalyzeArchitecture landed in current. Both real models measured DO NOT DECOMPOSE and the descriptor refuses rather than inventing a cut.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket AC-02

- close_scope: ticket
- close_id: AC-02
- workflow: architectural-coherence-epic
- closed_at: 2026-07-27T17:27:47+00:00
- summary: (none given)
- feedback_status: unreviewed

## Close-out ticket AC-03

- close_scope: ticket
- close_id: AC-03
- workflow: architectural-coherence-epic
- closed_at: 2026-07-27T17:20:19+00:00
- summary: AC-03: the ask -- prompts/implementation_brief.md + templates/implementation_brief.md and prompts/aspect_decomposition.md. Zero TLA+ model delta (ticket current == desired, TLC green, figures identical to AC-01). Four end-to-end renders kept as evidence: two DEGRADED briefs from this repository's own model under a declared partition, one REFUSAL from the emergent one-component partition, one FULL brief from the worked example's Internal view. consumable_as_architecture is necessary but not sufficient for a non-vacuous brief; the prompt adds three per-render vacuity tests. Two deferred findings filed (AC-03-DF-01, AC-03-DF-02).
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket AC-04

- close_scope: ticket
- close_id: AC-04
- workflow: architectural-coherence-epic
- closed_at: 2026-07-27T18:02:59+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket EV-01

- close_scope: ticket
- close_id: EV-01
- workflow: architectural-coherence-epic
- closed_at: 2026-07-27T18:47:57+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket EV-02

- close_scope: ticket
- close_id: EV-02
- workflow: architectural-coherence-epic
- closed_at: 2026-07-27T19:23:28+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket RP-01

- close_scope: ticket
- close_id: RP-01
- workflow: architectural-coherence-epic
- closed_at: 2026-07-30T21:02:29+00:00
- summary: (none given)
## Close-out ticket RP-02

- close_scope: ticket
- close_id: RP-02
- workflow: architectural-coherence-epic
- closed_at: 2026-07-30T20:55:30+00:00
- summary: RP-02: set-membership parameter recovery closes the ex4 oracle leak (EV-01-DF-01) and the audit now reports what the run measured (EV-02-DF-03). A fourth mechanism recovers the element that entered or left a set, cross-checked across every such conjunct of the action; ex4 goes 0 of 5 -> 5 of 5 parameters and all 330 cases carry a real argument where every one carried UNCHECKED. The adapter reads case.input.params and never touches case.after; an unrecovered argument is a hard failure there. Generation stays deterministic (two regenerations byte-identical). The audit is rendered from the corpus it audits: the sentence 'Every parameter of every action is recoverable from its state pair' is gone, nine tests assert it cannot return, an unmeasured audit declares itself STATIC, a class that recovered nothing is UNRECOVERABLE ON THIS CORPUS whatever the syntax promised, and marker-declared arguments are reported as model-declared rather than credited as recovered. THE HONEST NEGATIVE: the reconstructed 12-mutant catalog is identical before and after -- guard relaxation still 0 of 3 by corpus, 3 of 3 by hand-written tests -- because all 330 recovered arguments are arguments the guard ACCEPTS and 0 are rejected inputs (220 refusable pairs exist that a state graph can never emit). Removing the leakage half of EV-02's two causes moves nothing, so the whole remaining failure is the structural half. Separately, the wrong-item class seeded_faults.toml declined to seed as unmeasurable is killed on BOTH instruments; that caveat was a prediction never run and is amended in place. Zero TLA+ model delta.
## Close-out ticket RP-04

- close_scope: ticket
- close_id: RP-04
- workflow: architectural-coherence-epic
- closed_at: 2026-07-30T20:55:30+00:00
## Close-out ticket RP-05

- close_scope: ticket
- close_id: RP-05
- workflow: architectural-coherence-epic
- closed_at: 2026-07-30T20:37:59+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket RP-03

- close_scope: ticket
- close_id: RP-03
- workflow: architectural-coherence-epic
- closed_at: 2026-07-30T21:35:17+00:00
## Close-out ticket RP-07

- close_scope: ticket
- close_id: RP-07
- workflow: architectural-coherence-epic
- closed_at: 2026-07-30T21:23:28+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket EV-03

- close_scope: ticket
- close_id: EV-03
- workflow: architectural-coherence-epic
- closed_at: 2026-07-30T22:24:24+00:00
- summary: EV-03: re-ran the eval suite against the repaired tree and re-scored against the same committed predictions. RP-01 measured (203-partition sweep: 12 false cleans -> 0, zero true findings lost, 20 released). RP-02's honest negative confirmed on a second instrument (parameter recovery 0/5 -> 5/5, mutant matrix unchanged in every cell). RP-03 measured (modules generate in place, corpora carry arguments, a Given's corpus executes); CM-F5 still open and sharper. Two blind runs, both DP-1 PASS, one of which found a major new false clean (EV-03-DF-03) that the DP-1 scoring rule cannot detect. Five findings filed, none fixed. Zero model delta.
- feedback_status: items-recorded

EV-03 is a MEASUREMENT ticket and this is where its toolchain findings belong.
All five are recorded in full in `specs/desired_program_model/deferred_findings.yaml`
with a reproduction command, a suggested fix and a measured blast radius. This
epic is LOCAL-ONLY by owner direction (schedule_revision 3 amendment (a)): ticket
agents push nothing and open no issue, so `recommendation:` carries the local
finding id rather than a URL and `status` is `recorded-local` rather than
`filed`. Filing them upstream is the epic owner's call, not this ticket's.

### SF-101

- surface: scripts/architecture_reflexion.py
- severity: major
- summary: First-party-outside---code detection tests exactly one path
  (`code_root.parent / name`), so a first-party package nested at `generated/pkg`,
  `src/pkg`, `gen/pkg` or `vendor/pkg` is silently filed as third-party. Every
  divergence is then erasable by re-exporting through it -- `coherent` on a
  codebase with four real divergences for a 41-line diff, both digests unchanged,
  `blind_spots: []`, `basis_limits: []`, behavioural suite green, runtime coupling
  intact. Conversely the coherent fixture's verdict flips to `unmappable` when its
  generated package moves up one directory with zero Python changed.
- found_by: blind agent under EV-03, reproduced independently by the scorer
- evidence: examples/validation/runs/ex5-run4/artifacts/reexport_attack/
- recommendation: EV-03-DF-03 -- resolve first-party-ness against the project root
  and the sys.path the project installs; the fix is entirely in the detection and
  changes no verdict rule.
- skill_change: declined(target removed -- scripts/architecture_reflexion.py no
  longer exists in this repository; the architecture-reflexion surface was cut by
  the architectural-coherence / cut-the-apparatus work, so there is nothing left
  to repair. Verified absent on the epic tip by SI-05.)
- status: declined

### SF-102

- surface: scripts/run_generated_case_adapters.py
- severity: minor
- summary: A slice narrower than its view orphans the view's effect providers and
  the runner refuses its corpus. Both mappings the ex4 fixture ships bind the
  port, so a slice excluding the effect-carrying action has ZERO working
  configurations and the documented workaround needs a third file that exists
  nowhere -- and the file you write has no durable-write oracle, so the resulting
  instrument is strictly weaker than it looks. (CM-F5, sharpened.)
- found_by: EV-03 mechanical arm and, independently, the blind aspect agent
- evidence: examples/validation/runs/ex4-run4/artifacts/case_modules_worked_example.txt
- recommendation: EV-03-DF-02 -- a lever that treats an unused provider on a
  declared case module as a fact rather than a misconfiguration.
- skill_change: applied(28cf7b39) -- run_generated_case_adapters.py now carries
  `orphan_ports` and REPORTS an unused provider instead of refusing the corpus;
  the comment at the site states the no-new-gates rule in those words. This is
  exactly the "fact rather than a misconfiguration" lever the finding asked for.
  Verified by SI-05 at scripts/run_generated_case_adapters.py.
- status: applied

### SF-103

- surface: scripts/run_generated_case_adapters.py
- severity: minor
- summary: `--effect-report PATH` accepts a path and silently writes nothing, with
  no warning and exit 0, on a project that declares effect ports through `ports:`
  + `effect_ports:` rather than an `effects:` block. The code comment two lines
  above the gate claims the report is written unconditionally.
- found_by: blind agent under EV-03, verified by the scorer
- evidence: examples/validation/runs/ex4-run6/scoring.md
- recommendation: EV-03-DF-04 -- write the report with an explicit "no effect
  declarations found" body, or refuse naming the files searched. Silence is the
  one option that is wrong.
- skill_change: proposed(tla-spec-dev, specs/results/epic-self-improvement-substrate/tickets/SI-05/proposals/SF-103-effect-report-silence.diff)
  -- STILL REPRODUCIBLE, re-verified by SI-05. The write sits inside
  `if effects_active:` and the comment three lines above it still claims "The
  report is written unconditionally". scripts/run_generated_case_adapters.py is
  outside SI-05's conflict keys, so this is proposed as a diff, not applied.
- status: proposed

### SF-104

- surface: scripts/analyze_architecture.py, prompts/aspect_decomposition.md
- severity: minor
- summary: `analyze architecture` without `--components` silently substitutes an
  emergent partition for the one the project declares, and the shipped prompt's
  Step 1 tells a first-day engineer to run it that way. On the ex4 fixture the
  default run erases the deliberate `Deliver` spanning action and attributes the
  boundary crossing to a different action.
- found_by: blind agent under EV-03, verified by the scorer
- evidence: examples/validation/runs/ex4-run6/scoring.md
- recommendation: EV-03-DF-05 -- name a declaration the run did not use (a fact,
  not a suggestion, so CD-01 is not engaged), and fix the prompt.
- skill_change: declined(both surfaces retired -- scripts/analyze_architecture.py
  no longer exists, and prompts/aspect_decomposition.md:126 already records that
  the step "used to read `analyze architecture`, removed 2026-08-04". The prompt
  half the finding asked for is done; the command half has no target left.)
- status: declined

### SF-105

- surface: references/, examples/validation/README.md
- severity: minor
- summary: EV-02-DF-05 re-scored STILL OPEN. No `python3` on the eval machine's
  PATH carries `yaml`, `pytest` and `tomllib` together, and no document states an
  interpreter requirement. Both round-2 blind agents hit it independently. EV-03
  solved it for itself with a pinned uv venv and documented that in the validation
  README; the toolchain docs still do not.
- found_by: EV-03 and both blind agents
- evidence: examples/validation/runs/ex4-run4/scoring.md
- recommendation: EV-02-DF-05 -- state an absolute interpreter path, or declare
  the dependency set the published commands need.
- skill_change: applied(SI-05 -- skills/spec-double-2/references/migration.md
  Phase 6) -- the toolchain docs now declare the dependency set the published
  commands need, in the pinned `uv run --python 3.12 --with ...` form. That is
  the half EV-03 had solved only for itself in the validation README.
- status: applied

## Close-out ticket RC-01

- close_scope: ticket
- close_id: RC-01
- workflow: architectural-coherence-epic
- closed_at: 2026-08-01T23:37:54+00:00
- summary: RC-01: all nine MF-026 in-scope gaps closed by modelling them or changing the program, plus the owner's guard-weakening decision. GenerateCases + CloseTicketWeakened + architecture_delta + TicketClosedWeakened; bound 9.53x, TLC green 7.99x distinct at unchanged depth 26.
- feedback_status: items-recorded

### SF-201

- surface: `scripts/spec_evolution.py::record_complexity_ledger`, and the
  `complexity_ledger.yaml` template `scripts/new_ticket_workflow.py` scaffolds.
- what happened: RC-01 measured a 7.99x reachable-state increase, wrote the TLC
  output to `specs/results/rc01-tlc-current.txt`, named it as close evidence, and
  the ledger entry still recorded `distinct_states: null`. The ledger fills those
  figures only from one of three conventional FILENAMES inside the ticket's own
  `results/` directory, and nothing in the scaffolded input mentions the
  convention, offers a field for the path, or warns when none resolves.
- why it matters: the same silence produced nulls for AC-01 (the epic's headline
  4.6x) and EV-03. The one entry in this epic that carries a reachable-state
  figure is AC-04's, which added no model delta at all. The machine record of the
  standing objective has the number for the ticket that moved nothing and null
  for the three that moved it most.
- recommendation: add `tlc_report:` to the scaffolded ledger input with the
  convention documented beside it, keep the filename probe as a fallback, and
  print one line at close when neither resolves. Filed locally as RC-01-DF-04 in
  `specs/desired_program_model/deferred_findings.yaml`.
- skill_change: proposed(tla-spec-dev, specs/results/epic-self-improvement-substrate/tickets/SI-05/proposals/SF-201-ledger-tlc-report.diff)
  -- STILL OPEN, re-verified by SI-05. `record_complexity_ledger` accepts a
  `tlc_report` path, but the scaffolded complexity_ledger.yaml TEMPLATE offers no
  field for it, so the figure is still filled only by the filename probe. The
  TEMPLATE constant lives in scripts/complexity_ledger.py, outside SI-05's
  conflict keys.
- status: proposed

### SF-202

- surface: `tla-spec-dev run spec-unit-tests --scope`.
- what happened: `specs/desired_program_model/tests/` carries a 17-file
  conformance suite that is copied forward at every `open ticket` and is never
  executed -- project scope resolves to `specs/current` only. Its binding
  reconciliation test had been asserting "fourteen command actions" against a
  fifteen-action module since AC-01 closed, and no run ever said so.
- why it matters: this is the toolchain doing to itself what the MF-026 coverage
  audit exists to catch -- an oracle that is never pointed at a surface reports
  nothing about it, which is not the same as reporting that it is clean.
- recommendation: either add a scope that includes the desired tree, or stop
  scaffolding tests into it and say plainly that the desired tree carries no
  executable conformance. Filed locally as RC-01-DF-02.
- skill_change: proposed(tla-spec-dev, specs/results/epic-self-improvement-substrate/tickets/SI-05/proposals/SF-202-spec-unit-desired-scope.diff)
  -- STILL OPEN AND RE-MEASURED BY SI-05: `--scope` still offers only
  {auto, project}, and specs/desired_program_model/tests still carries 17 files
  that no scope reaches. scripts/tla_spec_dev.py is outside SI-05's conflict keys.
- status: proposed

### SF-203

- surface: `scripts/skill_feedback.py`, the close-out feedback record itself.
- what happened: filling this block revealed that EVERY close-out entry in this
  file -- eight of them, across this epic and its predecessor -- still reads
  `feedback_status: unreviewed` with the boilerplate instruction untouched. The
  close prints "feedback NOT yet filed" and closes anyway.
- why it matters: it is a required close-out step that nothing requires. The
  same shape as the gaps this epic's audit was opened to find: an obligation
  stated in prose, checked by nobody, and therefore not an obligation.
- recommendation: owner's call whether the step is real. If it is, make the
  close refuse `unreviewed` at WORKFLOW close (it already refuses plenty else
  there); if it is not, stop printing the warning.
- skill_change: applied(SI-05 -- scripts/spec_evolution.py::print_skill_change_proposals)
  -- THE OWNER'S CALL WENT A THIRD WAY, and this finding is why SI-05 exists.
  "Make the close REFUSE `unreviewed`" is DECLINED: the epic's GOAL-no-new-gates
  records that a refusal here reads to an agent as a stop. "Stop printing the
  warning" is declined too. Instead the warning became SPECIFIC and ACTIONABLE --
  the close now names each finding that targets this repository and proposes no
  change, tells the reader the exact field to add, and PROCEEDS. The obligation
  is reported, never enforced.
- status: applied

## Close-out ticket RC-02

- close_scope: ticket
- close_id: RC-02
- workflow: architectural-coherence-epic
- closed_at: 2026-08-02T00:53:30+00:00
- summary: Closed MF-026 round-3 N-1 (three unattached ports attached to InstallLocalCli in all three trees, with @port mirrors and two always-on consistency tests), N-2 (generate cases --out and --dot constrained through spec_paths.resolve_spec_tree_out, which constrains the metadir rmtree by construction), and N-3 (the stale citation fixed and a file-qualified, content-anchored citation check shipped, which found eight more stale citations). Ran run effect-conformance against this model for the first time: unobservable, 57 observed effects over 8 cases, 20 gaps, 9 dead ports, 15 unobservable targets, exit 1, nothing tuned; the N-1 counterfactual measures the fix at -2 gaps and -1 dead port. generation_status stays planned because this model's corpus is 3,678,217 cases at 18,391x its own cap. TLC unchanged at 10,331,543 distinct states, depth 26.
- feedback_status: items-recorded

### SF-301

- surface: `tla-spec-dev run effect-conformance`, adapter import resolution.
- what happened: the FIRST EVER execution of this oracle against this
  repository's own model died with `ModuleNotFoundError: No module named
  'production_adapters'` before a single case ran. The command executes
  adapters in-process and never puts the target spec directory on `sys.path`,
  while `case_adapters.toml` -- the file this same CLI scaffolds -- names them
  as bare module paths. The enforcing copy does not have the defect:
  `run spec-unit-tests` puts the target directory on `PYTHONPATH` when it
  spawns the runner.
- why it matters: the standalone oracle cannot run against ANY project this CLI
  scaffolds, which is the opposite of the documented relationship between the
  two ("this command exists so the diff can be produced and inspected on its
  own"). It is a direct contributor to the "no oracle has ever run" limit that
  MF-026 has reported since round 2: the first operator to try it gets an
  import error and cannot tell whether the oracle or their project is at fault.
- recommendation: put the resolved spec directory and the repository root on
  `sys.path` in `_execute_corpus` before the first `load_object`, and add a
  regression test that points the oracle at `specs/current` with no PYTHONPATH
  set. Filed locally as RC-02-DF-02.
- skill_change: applied(28cf7b39) -- "HP-04: run the oracle, then fix the three
  things running it found". effect_conformance.py's module docstring now records
  that the run had failed to "put the target spec directory on ``sys.path``, so
  the very first run died", and the path is resolved before the first
  load_object. Verified by SI-05.
- status: applied

### SF-302

- surface: `tla-spec-dev run effect-conformance`, case execution.
- what happened: the oracle calls `call_adapter` for every case and never
  consults `can_run` / `adapter_accepts_case`, so it ABORTS THE WHOLE RUN on
  the first adapter that cannot take its case -- here `TypeError: adapter
  <AnalyzeArchitectureAdapter> does not define run(case, ...)`, on the second
  case. `run_generated_case_adapters` applies exactly that capability check
  before executing anything.
- why it matters: the two runners are documented as the same measurement in two
  places, and they are not. It also means the oracle has no partial report: one
  unrunnable adapter and there is no evidence at all, rather than evidence about
  the cases that did run.
- recommendation: call `adapter_accepts_case` and record a SKIP with its reason,
  and REPORT the skipped set -- a case the oracle silently did not run is the
  "unobservable read as clean" shape MF-027 removed. Filed locally as
  RC-02-DF-03.
- skill_change: applied(28cf7b39) -- the oracle now carries SkippedCase with
  SKIP_NOT_RUNNABLE / SKIP_DECLINED / SKIP_UNBOUND / SKIP_ERROR kinds, its summary
  line reports executed/skipped/unbound counts, and a port whose every declaring
  action was skipped is annotated UNEXERCISED rather than read as clean -- which
  is precisely the MF-027 distinction the finding asked for. Verified by SI-05.
- status: applied

### SF-303

- surface: `tla-spec-dev generate cases`, and `references/case_modules.md`.
- what happened: generating this repository's own corpus from the REDUCED
  config MF-028 added for the purpose produces 3,678,217 cases and a 7.4 GB
  `cases.py` -- 18,391x the manifest's own `max_internal_cases_per_component`
  -- and the cap gate refuses it after writing the whole thing to disk. Every
  worked example in `references/case_modules.md` pairs generation with a
  `tlc_projection.py`; the toolchain's own model has none, and nothing in the
  CLI says that a model of any size needs one.
- why it matters: this is why no oracle has ever run against this model, and it
  is invisible until someone tries. The refusal message offers "redesign" or
  "raise the cap" and never mentions the projector, which is the actual lever:
  projecting away the two variables the repository already documents as
  unrecoverable takes the corpus from 3,678,217 to 628,424 with no model change.
- recommendation: name `--state-projector` in the cap-refusal message as a third
  way forward, and gate on the projected count before rendering, so a refused
  corpus does not cost 7.4 GB and five minutes first. Filed locally as
  RC-02-DF-04.
- skill_change: proposed(tla-spec-dev, specs/results/epic-self-improvement-substrate/tickets/SI-05/proposals/SF-303-cap-refusal-names-projector.diff)
  -- STILL OPEN, re-verified by SI-05. `analyze corpus` still offers exactly two
  ways forward ("redesign or raising the cap with a recorded rationale") in both
  its description and its next_step and names no projector, although
  `--state-projector` exists in generate_cases_from_tlc_dump.py.
  scripts/tla_spec_dev.py is outside SI-05's conflict keys.
- status: proposed

### SF-304

- surface: internal line citations across `scripts/` and `spec_manifest.yaml`.
- what happened: RC-02 shipped a content-anchored citation check and it
  immediately found EIGHT stale citations beyond the one the coverage audit
  filed -- 9 of the 11 distinct citations in that surface were wrong in at least
  one tree, including one inside the comment block the previous ticket had just
  written.
- why it matters: three consecutive tickets were charged with "shipping a stale
  citation" as though it were a lapse in care. The measurement says otherwise:
  nothing checked, and a repository that cites line numbers in durable comments
  will always drift. This is a skill-level pattern, not a repository one --
  every project this skill scaffolds inherits comment-heavy manifests.
- recommendation: ship the check (or its convention) with the scaffolded
  project, or stop encouraging line-number citations in the templates and cite
  symbols instead. Fixed here for this repository's surface, so no deferred
  finding was filed.
- skill_change: applied(SI-05 -- scripts/scaffold_spec_workflow.py) and
  proposed(tla-spec-dev, specs/results/epic-self-improvement-substrate/tickets/SI-05/proposals/SF-304-ship-citation-check.diff)
  -- THE FINDING OFFERED TWO ROUTES AND SI-05 TOOK THE ONE IN ITS KEYS. "Stop
  encouraging line-number citations in the templates and cite symbols instead"
  is APPLIED: the scaffolded desired/current READMEs now ship the
  cite-symbols-not-lines convention, so a new project starts on the side that
  does not rot. "Ship the check with the scaffolded project" is PROPOSED as a
  diff -- SI-05 grepped the whole skill surface and nothing outside
  check_citations.py references it. (SI-05's own baseline carries three failing
  test_source_citations cases, which is this finding still being true here.)
- status: applied

Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out workflow architectural-coherence-epic

- close_scope: workflow
- close_id: architectural-coherence-epic
- workflow: architectural-coherence-epic
- closed_at: 2026-08-04T00:54:24+00:00
- summary: Architectural coherence and case modules: four architecture levers, case modules, two measured eval rounds, four MF-026 audit rounds, two reconciliation tickets, and a standardized scorecard baseline
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket HP-01

- close_scope: ticket
- close_id: HP-01
- workflow: hexagonal-prompting-epic
- closed_at: 2026-08-04T12:35:37+00:00
- summary: The A/B experiment: two declared arms, a 10-mutant seeded catalogue proven exactly-once, and 13 sealed predictions including 6 negatives. No model surface added, deliberately.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket HP-02

- close_scope: ticket
- close_id: HP-02
- workflow: hexagonal-prompting-epic
- closed_at: 2026-08-04T14:06:33+00:00
- summary: HP-02: the hexagonal + minimize-complexity ask ships as prompts/hexagonal_implementation.md, is inlined into arm B's HP-01 slot, and is documented in references/hexagonal_prompting.md. No checker, no threshold, no gate. Local pilot ran both arms end to end: hexagonality moved as expected, complexity moved the wrong way (declared instrument could not run -- HP-02-DF-01), and the catch-bugs guard moved the wrong way by one cell on an instrument whose positive control survives. The pilot also found a hole in the prompt (a real-vs-fake test that asserts nothing); one sentence was added afterwards and is UNMEASURED.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket HP-03

- close_scope: ticket
- close_id: HP-03
- workflow: hexagonal-prompting-epic
- closed_at: 2026-08-04T14:51:24+00:00
- summary: The negative corpus: TLC's disabled edges asserted rejected, and a projection that takes MCsmall from 3,678,217 cases to 541. Guard relaxation moved off zero for the first time -- 3 of 3 seeded, 5 of 5 fresh, against 0 of 3 and 0 of 5 for the whole-view corpus. Zero model surface added. Four findings filed, none fixed. The hand-written suite still kills 10 of 10 where the corpora together kill 8 of 10.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket HP-04

- close_scope: ticket
- close_id: HP-04
- workflow: hexagonal-prompting-epic
- closed_at: 2026-08-04T15:03:52+00:00
- summary: The effect oracle runs: it loads a scaffolded project's adapters unaided, skips and names what it cannot drive, and reports the same numbers twice. CM-F5 closed. The mutant matrix moved by zero cells, exactly as HP-01 predicted.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket HP-05

- close_scope: ticket
- close_id: HP-05
- workflow: hexagonal-prompting-epic
- closed_at: 2026-08-04T15:28:40+00:00
- summary: Content assertion is the default: codegen generates and binds the content-asserting effect provider, every mapping states its oracles unprompted, and M04 moves from surviving every corpus to dying under the default mapping (durable_content 1 of 2 -> 2 of 2). The generator is still worse than the suite, now by one mutant instead of two.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket HP-06

- close_scope: ticket
- close_id: HP-06
- workflow: hexagonal-prompting-epic
- closed_at: 2026-08-04T16:29:19+00:00
- summary: EVALUATION: the A/B judged blind. GOAL-hexagonal-in-fact MET (D3 = 4 from both judges, the first 4 outside D5 in this project's history); GOAL-catch-bugs MET (D1 = 3 from both judges, guard relaxation 3 of 3 under the negative corpus and 1 of 1 on a fresh blind catalogue); GOAL-simpler-same-behavior MISSED (D2 = 2 from all four judges -- an A/B cannot reach anchor 3). The prompt produced the structure and the structure caught nothing: 49 of 49 comparable kill cells identical between the arms. The positive control is RED on arm A. 7 PASS / 4 FAIL on the sealed predictions, three of the four failures negative. Findings by channel 0 suite : 17 adversarial : 13 blind author. Twelve findings filed, none fixed; six of HP-06's own claims falsified and corrected in place.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out workflow hexagonal-prompting-epic

- close_scope: workflow
- close_id: hexagonal-prompting-epic
- workflow: hexagonal-prompting-epic
- closed_at: 2026-08-05T15:28:59+00:00
- summary: Hexagonal prompting: architecture as a prompt, a negative corpus that reached a class nothing had reached, static scanners removed, and an A/B decided by judged scorecards on a repaired instrument
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket PA-02

- close_scope: ticket
- close_id: PA-02
- workflow: ports-as-adapters-epic
- closed_at: 2026-08-05T18:07:32+00:00
- summary: PA-02: scripts/code_complexity.py -- complexity figures over PRODUCED Python. A thermometer: it reports, refuses nothing, exits 0 on every input, and nothing in the toolchain reads its output. Distinguishes both committed anchor trees and both sealed arms.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket PA-03

- close_scope: ticket
- close_id: PA-03
- workflow: ports-as-adapters-epic
- closed_at: 2026-08-05T18:20:16+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket PA-04

- close_scope: ticket
- close_id: PA-04
- workflow: ports-as-adapters-epic
- closed_at: 2026-08-05T19:27:44+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket PA-05

- close_scope: ticket
- close_id: PA-05
- workflow: ports-as-adapters-epic
- closed_at: 2026-08-05T18:18:14+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket PA-06

- close_scope: ticket
- close_id: PA-06
- workflow: ports-as-adapters-epic
- closed_at: 2026-08-05T21:23:16+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket FI-01

- close_scope: ticket
- close_id: FI-01
- workflow: falsifiable-instruments-epic
- closed_at: 2026-08-06T12:44:46+00:00
- summary: FI-01: a positive control seeded inside the port's derived region on every tree that declares a port (FI-M15 on reference_ports and arm B), and a control-property probe made two-sided so it can fail -- shipped with five deliberately broken controls it must report broken (R1). PA-M14 is measured INERT on reference_ports and REPORTED RED rather than repaired (R2). extends is followed when reading [pa_control_properties] (PA-06-DF-02). No model delta.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket FI-02

- close_scope: ticket
- close_id: FI-02
- workflow: falsifiable-instruments-epic
- closed_at: 2026-08-06T13:55:09+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket FI-03

- close_scope: ticket
- close_id: FI-03
- workflow: falsifiable-instruments-epic
- closed_at: 2026-08-06T14:02:41+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket FI-04

- close_scope: ticket
- close_id: FI-04
- workflow: falsifiable-instruments-epic
- closed_at: 2026-08-06T14:27:22+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket FI-05

- close_scope: ticket
- close_id: FI-05
- workflow: falsifiable-instruments-epic
- closed_at: 2026-08-06T13:37:05+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket FI-06

- close_scope: ticket
- close_id: FI-06
- workflow: falsifiable-instruments-epic
- closed_at: 2026-08-06T16:44:15+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket SM-01

- close_scope: ticket
- close_id: SM-01
- workflow: subtract-to-measure-epic
- closed_at: 2026-08-06T20:43:01+00:00
- summary: Seeded 9 gap mutants and 2 positive controls before any removal, captured the before-state descriptor, sealed 12 predictions with 6 negatives. 3 PASS / 4 FAIL of the 7 decidable now.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket SM-02

- close_scope: ticket
- close_id: SM-02
- workflow: subtract-to-measure-epic
- closed_at: 2026-08-06T23:11:15+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket SM-03

- close_scope: ticket
- close_id: SM-03
- workflow: subtract-to-measure-epic
- closed_at: 2026-08-06T22:14:10+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket SM-04

- close_scope: ticket
- close_id: SM-04
- workflow: subtract-to-measure-epic
- closed_at: 2026-08-07T02:06:40+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket SM-06

- close_scope: ticket
- close_id: SM-06
- workflow: subtract-to-measure-epic
- closed_at: 2026-08-07T14:50:01+00:00
- summary: One home for the card: 20 live statements of a dimension, an anchor or a scoring rule deleted from 5 files; 3 of 4 disagreeing copies were UNCAUGHT before it; the card's content is byte-unchanged
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket SM-05

- close_scope: ticket
- close_id: SM-05
- workflow: subtract-to-measure-epic
- closed_at: 2026-08-07T18:51:44+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket RD-01

- close_scope: ticket
- close_id: RD-01
- workflow: reading-discipline-epic
- closed_at: 2026-08-08T17:20:57+00:00
- summary: RD-01: R3 executed -- a claim carries its scope; contested computes; judge tier is a field
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket RD-02

- close_scope: ticket
- close_id: RD-02
- workflow: reading-discipline-epic
- closed_at: 2026-08-08T20:19:20+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket RD-04

- close_scope: ticket
- close_id: RD-04
- workflow: reading-discipline-epic
- closed_at: 2026-08-08T20:24:10+00:00
- summary: RESEARCH: architecture tags -- one axis, two demonstrated values, per-dimension refusal authority, and the suppression-key attack answered by fail-open derivation.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket RD-05

- close_scope: ticket
- close_id: RD-05
- workflow: reading-discipline-epic
- closed_at: 2026-08-08T23:45:02+00:00
- summary: Implement the effect_boundary architecture tag from RD-04's design: one axis, two values with refusal authority keyed on (dimension, value-pair), an INCOMPARABLE verdict that prints both score sets, derivation over declaration with every unresolved state failing open, and R-H1's third clause re-derived from the cards on every audit. No model delta: the derivation reads figures the shipped complexity instrument already prints and refuses nothing about any artifact.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket RD-03

- close_scope: ticket
- close_id: RD-03
- workflow: reading-discipline-epic
- closed_at: 2026-08-09T20:25:04+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket RM-01

- close_scope: ticket
- close_id: RM-01
- workflow: portable-substrate-epic
- closed_at: 2026-08-10T18:14:21+00:00
- summary: RM-01: a gap mutant that goes DIES->SURVIVES on a real removal, and the shipped classifier that said it could not. The re-runnability rule does exclude discriminating faults, but the fault that priced SM-03's removal was always re-runnable -- it was excluded one level further in by removal_census discriminate, which reads a surviving detector NAME as a surviving kill. Survivorship over a before-table is sound towards SURVIVES and unsound towards DIES; there is no such thing as an entailed DIES. RM-01-RF-1 DIES at bf0fb29~1 and SURVIVES at bf0fb29 with pytest-full whole at both trees and a positive control dying at both; both lost kills are DETECTOR-WEAKENED, the class the sealed record contains none of. SM-04-GM-T1 reproduces CAUGHT->UNCAUGHT from an independent implementation. The re-priced historical removals still come back at ZERO. Four findings filed, none fixed; RM-01-DF-01 is blocking and binds RM-03.
- feedback_status: unreviewed

## Close-out ticket RM-02

- close_scope: ticket
- close_id: RM-02
- workflow: portable-substrate-epic
- closed_at: 2026-08-10T17:32:22+00:00
- summary: RESEARCH: the card grades this project's toolchain on D1 and D4, one architectural style on D3; adoption requires LESS and every recommendation is a removal. No production code.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket RM-06

- close_scope: ticket
- close_id: RM-06
- workflow: portable-substrate-epic
- closed_at: 2026-08-10T19:25:39+00:00
- summary: Restore the baseline: 16 tests pinned to a record RD-03 grew, sorted into three groups. Five re-derived, five claims rewritten, six left deliberately red with findings RM-06-DF-01..04. Suite 16 failed/1481 passed at 356ffe8 -> 6 failed/1495 passed at e0dae3d, both real checkouts.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket RM-03

- close_scope: ticket
- close_id: RM-03
- workflow: portable-substrate-epic
- closed_at: 2026-08-10T21:50:03+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket RM-04

- close_scope: ticket
- close_id: RM-04
- workflow: portable-substrate-epic
- closed_at: 2026-08-11T00:08:20+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket RM-05

- close_scope: ticket
- close_id: RM-05
- workflow: portable-substrate-epic
- closed_at: 2026-08-11T01:41:36+00:00
- summary: EVALUATION: all four goals decided; the first PRICED removal headline withdrawn; the served rubric fell 23.7% while the shipped toolchain did not move; the loop does not transfer. 5 findings filed, 0 fixed.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CL-01

- close_scope: ticket
- close_id: CL-01
- workflow: close-the-loop-epic
- closed_at: 2026-08-11T18:24:39+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CL-02

- close_scope: ticket
- close_id: CL-02
- workflow: close-the-loop-epic
- closed_at: 2026-08-11T19:07:59+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CL-03

- close_scope: ticket
- close_id: CL-03
- workflow: close-the-loop-epic
- closed_at: 2026-08-11T19:30:10+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CL-04

- close_scope: ticket
- close_id: CL-04
- workflow: close-the-loop-epic
- closed_at: 2026-08-11T21:28:03+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket SV-06

- close_scope: ticket
- close_id: SV-06
- workflow: score-drives-validation-epic
- closed_at: 2026-08-12T17:00:05+00:00
- summary: SV-06 RESEARCH: the goal-score wiring already exists and has never been populated with a score. 27 goals, 12 dimension-keyed, 0 with a scored baseline, against 87 sealed cards. Design at references/goal_score_wiring.md; SV-07 hand-off is 4 prose edits across 3 skills, 0 fields, 0 bytes to serve. No production code, no skill edited.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket SV-02

- close_scope: ticket
- close_id: SV-02
- workflow: score-drives-validation-epic
- closed_at: 2026-08-12T17:13:11+00:00
- summary: SV-02 RESEARCH: validation IS scorable without grading a toolchain, and the property was already in the card -- D4's retired anchor 4, "the check is demonstrated to be capable of failing", whose own sentence names no tool and which inherits toolchain-dependence only through the "3, and" chain. The locality is three clauses, not two dimensions: 13 of 13 of D4's machinery-citing anchor decisions name anchor 3, 26 of 28 of D1's name anchor 3 or 4. Autopsy fraction, RM-02's method with its patterns copied unchanged: 44 of 315 demonstration sentences (14.0%) over the record, and 1 of 30 (3%) in the ladder-free N-D1 notes, against D1's 37%. 5 of 5 D4 tier-split groups have every lower-tier card naming the model clause, so the card's stated reason for retiring D4 is a symptom of that clause. Carrier: a note prompt at -15 bytes, not a rung at +682 bytes and four permanent anchors. Adapter surfaces score with zero toolchain today; TLA+ models are unfalsified on this record; diagrams appear in 0 sentences across 0 of 87 cards. Design at references/scoring_validation.md. No production code.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket SV-03

- close_scope: ticket
- close_id: SV-03
- workflow: score-drives-validation-epic
- closed_at: 2026-08-12T19:18:38+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket SV-07

- close_scope: ticket
- close_id: SV-07
- workflow: score-drives-validation-epic
- closed_at: 2026-08-12T20:36:46+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket SV-01

- close_scope: ticket
- close_id: SV-01
- workflow: score-drives-validation-epic
- closed_at: 2026-08-12T21:41:01+00:00
- summary: The negative control: D3 = 4,4 under card version 4 and 4,4 under version 5 on an artifact lacking the single-observer property. The caveat DISCRIMINATES; close-the-loop's headline is a detection, not a recalibration. Prediction sealed at 5e07dce before any judge ran.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket SV-04

- close_scope: ticket
- close_id: SV-04
- workflow: score-drives-validation-epic
- closed_at: 2026-08-12T22:04:07+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CA-01

- close_scope: ticket
- close_id: CA-01
- workflow: cut-the-apparatus-epic
- closed_at: 2026-08-13T15:35:40+00:00
- summary: Blindness measured, not assumed: 3 of 4 dispatched agents received the operator's auto-memory and the five most recent commit subject lines before any tool call, correcting SV-05-DF-02's '4 of 4' to a tier. A memory-free path is proven on real subjects (2 REFUSED, 1 PASS) and its residual impossibility is stated as blocking finding CA-01-DF-01: blindness to our conclusions is achievable, blindness to our identity is not. No memory file and no skill edited; two diffs escalated. Costs 182 Python lines in examples/validation/.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CA-02

- close_scope: ticket
- close_id: CA-02
- workflow: cut-the-apparatus-epic
- closed_at: 2026-08-13T17:31:12+00:00
- summary: Cut the removal-pricing machinery, an instrument RM-05-DF-01/CL-02 measured able to return only ENTAILED-SURVIVES. Removed price_removal.py (838), altered_score_probe.py (177), residual_faults.toml (193), removal_census.py (429), removals.toml (712) and their two test files (888), each deletion naming its finding. examples/validation/ 15,901 -> 14,457 (-1,444); scripts/ unchanged at 27,652 because complexity_ledger.py has NO pricer coupling (CA-02-DF-01); card unchanged at 6,281 / sha256:2d7d4a0506d9b259. Registry rows retired not deleted (FI-04-DF-04); gap_mutants/ kept as a tombstone because it is sealed subject rm04_removal_pricer's declared scope, which went UNDERIVABLE and moved the tag derivation 17->16 of 21 (numerator fell, denominator held at 21). The deliberate pricer-grep red was DELETED WITH ITS SUBJECT, not repaired. Suite 6 failed / 1526 passed on both the pre-merge and reconciled trees, zero new reds. Price-table format established as plain markdown, no new code.
## Close-out ticket CA-05

- close_scope: ticket
- close_id: CA-05
- workflow: cut-the-apparatus-epic
- closed_at: 2026-08-13T17:53:55+00:00
- summary: A disposition requirement an epic cannot close through, demonstrated by refusing THIS epic (10 of 15 rows open) while accepting two real sealed epics; harvest register repaired 38 -> 41 with the denominator movement named; channel/channel_note and cost{basis,value} defined and populated on CA-05's own five rows. Main finding: the disposition practice existed for three epics and lapsed silently on 2026-08-08, in exact correlation with SELF-IMPROVEMENT.md's own lapse.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CA-03

- close_scope: ticket
- close_id: CA-03
- workflow: cut-the-apparatus-epic
- closed_at: 2026-08-13T19:26:02+00:00
- summary: CA-03: RD-03-DF-08's cut was already made at card version 4 (zero lines removed, enumeration shipped as evidence); SV-04-DF-05 repaired in cmd_scaffold by recording the [round-dir, arm-label] pair blinding makes necessary, with a demonstrated failing input on the real subject toolchain_fixture. All five checks kept and decided on the record. No new gate. Card unchanged at 6281 bytes.
- feedback_status: none-found

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CA-04

- close_scope: ticket
- close_id: CA-04
- workflow: cut-the-apparatus-epic
- closed_at: 2026-08-13T22:04:12+00:00
- summary: Cut oracle 4, the mutation kill test and the last hard static gate in this repository (RM-03-DF-05, which identified this cut, declined it as a model delta its own ticket forbade, and asked for 'its own ticket against the CLI model'). Removed: the kill_test variable, the RunKillTest action and the KillTestVerdictRequiresBudgets invariant; RunKillTestAdapter and its binding; kill_rate_floor, the mutation_write port and RunKillTest's port row; three kill_mutants.toml catalogues; three spec-unit adapter tests; scripts/run_kill_test.py; tests/test_kill_test.py; and the 'run kill-test' subcommand. scripts/ -1,105 lines; card unchanged at 6,281 bytes sha256:2d7d4a0506d9b259. THE DECREASE IS LICENSED AND WAS NOT WHEN THIS CLOSE WAS FIRST ATTEMPTED: the ledger REFUSED the first attempt because no TLC had been run, that refusal was correct and is kept at close-refusal.txt, and the basis was then measured -- TLC green on both models, the before-model reconstructed from the branch point and verified both by sha256 and by reproducing the 563,963-state figure the repository had already recorded for it. WHAT THE MODEL CAN NO LONGER EXPRESS: nothing validates the representation against the PROGRAM; the cost caps lost their matching value floor; coverage can drift behind the model silently; and compare_reports, which separated a legitimate simplification from a disguised deletion, is gone -- in a cutting epic. A green tlc_after is weaker evidence here than for an ordinary refactor, because it certifies self-consistency, which is exactly what the kill test existed because TLC could not check. ONE MEASUREMENT GOT WORSE AND THE FLATTERING VERSION WAS WITHDRAWN: the bound fell 1,111,320 -> 277,830, but comparable_to_cap returns None rather than True for an incomplete bound under the cap, so the model did not become compliant, it became UNMEASURABLE against the cap. TWO ORDERED DELETIONS WERE REFUSED: kill_test.py has five in-repo consumers of its parser and suppression scanner, one at module scope in the driver RD-03 used for the zero-unique-kills disproof, so the oracle-4 half was cut and the 310-line parser retained; and candidate_note_bar.py rests on a misattributed finding, holds the repository's only assertion that the card is 6,281 bytes, and is the named reproduction of the open SV-07-DF-01. THE MOST TRANSFERABLE RESULT IS CA-04-DF-06 AND IT GENERALISES BEYOND THIS CUT: the epic's REQUIRED loader check greps deleted PATHS and is structurally blind to deleted INTERFACES -- CLI subcommands, exported symbols, manifest keys, TOML sections have no basename to grep for -- so every cutting ticket runs a check that cannot see the interfaces it retires and shipped adopter instructions rot with nothing going red; demonstrated on this ticket's own cut at SKILL.md:1167 and :1174, and again from the other end in CA-04-DF-08, where the validation matrix given to all eight tickets names a 'run tlc' subcommand the CLI does not have. AND CA-04-DF-07, which this ledger produced about itself: a hard gate refused a real promotion on substance and was right, after lying dormant the whole epic because CA-04 is the first ticket to change the model at all. Eight findings against a budget of five, all disposed, the overrun recorded as one. Suite 8 failed / 1466 passed on the merged tip: six pre-existing at CA-03's tip, two this ticket's, both declared and outside its scope, none repaired.
- feedback_status: items-recorded

### SF-305

- category: profile-schema-cli
- target: `scripts/complexity_ledger.py:192` `TEMPLATE_SENTINEL = "TODO"`, applied at `:777` as `if TEMPLATE_SENTINEL in narrative: narrative = ""`
- observed_on: tla-spec-dev, ticket CA-04, `specs/tickets/CA-04/results/complexity_ledger.yaml`
- evidence: specs/results/scorecards/cut-the-apparatus/CA-04/close-refusal.txt, plus a second refused close whose only remaining verdict was "REJECTED -- no `narrative:` recorded" against a 5,842-character narrative that was present and parsed
- severity: silent-data-loss
- root_cause: tool
- workaround_applied: paraphrased the sentence so the narrative no longer contains the sentinel substring
- recommendation: fixed in this repository. The substring test became equality for `narrative` and `justification`; extended to `refinement.detail` and `transition_diff` at the attribute-the-catch close, where the first repair had left the same defect in two more free-prose fields.; not filed by CA-04 because opening issues is outside a ticket agent's remit
- skill_change: applied(7066e065) -- scripts/complexity_ledger.py is now
  `return value == TEMPLATE_SENTINEL`, with a comment citing SF-305 by id. The
  remaining `TEMPLATE_SENTINEL in ...` sites are status and enum fields, where a
  substring test is correct. Verified by SI-05.
- status: applied
- surface: the narrative sentinel check
- forced_workaround: paraphrase a legitimate quotation to avoid a substring
- data_loss: yes
- detail: THE SENTINEL IS A SUBSTRING TEST OVER THE WHOLE NARRATIVE, SO A NARRATIVE THAT QUOTES THE TEMPLATE WORD IS SILENTLY DISCARDED. CA-04's narrative recorded a load-bearing fact -- that CA-02 and CA-03 both left `validated_refactor` at its unfilled template value and closed cleanly, which is the evidence that the decrease gate had been dormant for the whole epic. Containing that quotation made the ledger treat 5,842 characters of filled narrative as an unfilled template, blank it, and refuse the close with a message pointing at ABSENCE when the cause was CONTENT. Nothing reported that the narrative had been discarded or why. The failure is worst exactly where the tool is most valuable: a narrative ABOUT the ledger's own template states cannot be written in the ledger. Fix by testing equality against the shipped default value, or a marker the scaffold writes and the author deletes, rather than `in` over free prose.

### SF-306

- category: profile-schema-cli
- target: `scripts/tla_spec_dev.py` `run` subparser -- registers only `spec-unit-tests` and `effect-conformance`; there is no `tlc` target and no top-level `tlc` command
- observed_on: tla-spec-dev, ticket CA-04, the first model-changing ticket of the cut-the-apparatus epic
- evidence: specs/results/scorecards/cut-the-apparatus/CA-04/tlc-before.txt and tlc-after.txt (the route that does work), against `specs/desired_program_model/ticket_plan.yaml` `validation.tlc`
- severity: manual-workaround
- root_cause: spec
- workaround_applied: drove TLC directly via `.skill-manager/bin/cli/tlc2 -config MC.cfg TlaSpecDevCli.tla`, and reconstructed the pre-change model from the branch point with `git show <base>:specs/current/...` into a scratch tree
- recommendation: https://github.com/haydenrear/tla-spec-dev/issues/319 (deferred at the attribute-the-catch close: new CLI surface plus a baseline-reconstruction design); also filed in the epic ledger as CA-04-DF-08
- status: filed
- surface: the CLI's TLC entry point, and the close gate that depends on it
- forced_workaround: bypass the documented CLI entirely and hand-roll both sides of a two-sided measurement
- data_loss: no
- detail: THE CLOSE GATE REQUIRES TLC EVIDENCE THE CLI CANNOT PRODUCE. The complexity ledger licenses a complexity DECREASE only on the CD-09 validated-refactor basis, whose first two members are `tlc_before` and `tlc_after` from the same run. The toolchain ships no command that runs TLC at all, and every ticket assignment in this epic says to run `tla-spec-dev --spec-root specs run tlc`, which answers "argument target: invalid choice: 'tlc'". Worse, `tlc_before` is unaddressed rather than merely unimplemented: the pre-change model does not exist in the working tree by close time, so satisfying the gate requires reconstructing it from git into a scratch directory -- a step no documentation mentions and which has an obvious wrong answer (running "before" against the post-change file). A `tla-spec-dev run tlc [--baseline <rev>]` emitting both runs in the shape `validated_refactor` expects would close the gap. Until then every model-changing ticket hand-rolls it, and the first one to try had its close refused before discovering the command did not exist.

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CA-05

- close_scope: ticket
- close_id: CA-05
- workflow: cut-the-apparatus-epic
- closed_at: 2026-08-14T00:34:31+00:00
- summary: RECONCILED CLOSE at the epic tip e379d6b (CA-01..CA-04 merged). This is a SECOND, APPEND-ONLY history entry: ticket-004-CA-05 is the first close, taken before the promotion predecessor merged, and is preserved unedited. Requirement REFUSES cut-the-apparatus 24 of 36 (16 D1 rows from CA-00/CA-01/CA-02 outstanding). Ledger 246 = tip's 239 + this ticket's 7, verified row-by-row, nothing dropped or reordered. CA-05-DF-06: seven duplicate-key rows the check certified clean, repaired, with a structural guard whose failing input is the real pre-repair file. CA-05-DF-07: this gate's ticket delta straddles a merge and charged CA-04's model reduction to CA-05 -- basis filled BY CITATION to CA-04's TLC run on the owner's instruction, never re-measured. Discrimination argument WITHDRAWN: 10 false D2/D3 refusals, each inspected. Register 38->41 (denominator rose), then NUMERATOR 1->2 of 41 via CA-03's F3 repair, verified by hand. Suite 8/1483, exactly the epic-tip baseline measured in a detached worktree.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CA-06

- close_scope: ticket
- close_id: CA-06
- workflow: cut-the-apparatus-epic
- closed_at: 2026-08-14T02:22:47+00:00
- summary: THE PATH IS SIMPLER AND IT IS NOT DRAMATICALLY SMALLER, AND THE MEASUREMENT TAKEN INSTEAD OF THE CUT IS THE OUTPUT. The mass this ticket was sent to cut -- --negative-cases (290 lines on a 1,043-line shared TLA+ parser and guard evaluator) and --port-cases (397) -- was measured and KEPT by SM-02 one epic ago in a still-green shipped test written expressly against this widening, so it was measured again instead. CA-06-DF-01: extract_action_signatures hardcoded the name `Next` and neither caller ever overrode it, so BOTH defended mechanisms emit ZERO cases on any model spelling its next-state relation differently -- every number defending them is taken on QuotaLedger, the one model here named `Next` -- while the run still printed `corpus gate PASS`. Fixed by calling find_next_relation, which the sibling module has shipped for three epics; 0 -> 11 cases. CA-06-DF-02: those 11 cannot execute, params keyed by TLA formal names against adapters written for recovered names, so the measured yield on a real subject is zero cases EXECUTED. CA-06-DF-05: the one-sided cap that made the zero silent is NOT repaired, filed with a subtractive fix because no_new_gates_rule forbids the obvious one. COST AND CATCH on examples/distributed_history, 128 exhaustively enumerated mutants: 39 corpus-unique kills raw, but on JOINTLY-EXERCISED CODE the corpus has ZERO semantic unique kills and the hand-written suite has ONE -- the 39 is coverage breadth, not fault-detection power, and that third discount is the independent reviewer's, adopted whole. The disproof survives; CA-06-DF-04 refutes only the UNQUALIFIED generalisation. THE CUT: one execution mode instead of two, and its "zero live callers" justification was FALSE when filed -- two live callers passed no flag at all, and A GREP CANNOT FIND AN ABSENT ARGUMENT, which is CA-04-DF-06's class from a third direction in three tickets. scripts/ moved -4 for this ticket and +209 actual, 28 of the difference being the review fixes themselves: RD-02 for the third time inside one ticket. Model delta direction=zero, TLC legitimately skipped -- but "no model delta" meant NO MODEL WORK WAS DONE and two now-dead ports remain declared, enumerated for the successor. Suite 8 failed / 1485 passed at the merged tip, identical item-for-item to the e379d6b baseline. Five findings, all disposed.
- feedback_status: items-recorded

### SF-307

- category: instrument-blindness-loader-check
- target: the epic's REQUIRED loader check -- `git grep` over deleted paths (CA-02) and deleted interfaces (CA-04-DF-06)
- observed_on: tla-spec-dev, ticket CA-06, cut-the-apparatus epic
- evidence: specs/results/scorecards/cut-the-apparatus/CA-06/loader-check.txt -- which ran BOTH required greps and still missed three live consumers; and CA-06-DF-03 in specs/desired_program_model/deferred_findings.yaml
- severity: wrong-result
- root_cause: skill
- workaround_applied: none available -- the misses were found by an independent reviewer reading the tests, not by any grep
- recommendation: https://github.com/haydenrear/tla-spec-dev/issues/320 (deferred at the attribute-the-catch close: needs a caller graph, and the finding says a third grep will not do it); the ledger row is CA-06-DF-03
- status: filed
- surface: the loader-check procedure prescribed by PRICE-TABLE-FORMAT.md section 5
- forced_workaround: human reading of every test that invokes the changed entry point
- data_loss: no
- detail: A GREP CANNOT FIND AN ABSENT ARGUMENT, AND THAT IS THE THIRD DIRECTION THIS CLASS HAS ARRIVED FROM IN THREE TICKETS. CA-02 missed a deleted PATH and silently broke repriced_history.py. CA-04 established that the check is blind to deleted INTERFACES -- subcommands, exports, manifest keys, TOML sections -- because it greps paths only. CA-06 ran BOTH greps, correctly, and still missed three live consumers of the execution mode it deleted: two tests that reach the mode by passing NO execution-mode flag at all (one of them literally NAMED for the mode), and a shipped CLI flag `--no-batch` that became a silent no-op. Every one of them is characterised by the ABSENCE of a token, and a check built on `git grep` searches for tokens. This is not fixable by adding a third grep. What would catch it is a check that enumerates the CALLERS of a changed entry point and asks which defaults each one relies on -- an import/invocation graph rather than a text search. Until something like that exists, every simplification that removes a default is unaudited by the procedure the epic requires, and the procedure will keep reporting clean.

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CA-07

- close_scope: ticket
- close_id: CA-07
- workflow: cut-the-apparatus-epic
- closed_at: 2026-08-14T03:36:35+00:00
- summary: CA-06-DF-02 consumed as an adapter conformance case: the negative corpus now names its arguments the way the module declares them, the sealed fixture is byte-identical because it declares no marker, and the 11 unlocked cases execute for the first time -- 5 of them naming a real model/implementation divergence, filed not fixed.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket CA-08

- close_scope: ticket
- close_id: CA-08
- workflow: cut-the-apparatus-epic
- closed_at: 2026-08-14T05:26:52+00:00
- summary: EVALUATION: 14 goal clauses met, 4 missed. The apparatus cut reached 14% of its target and CA-08-DF-08 measures why. scope returns 0 counted figures on the charter that credits it. Static gates adjudicated at 3:1 with the doctrine's real defect named. Eight findings filed, nothing fixed.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out workflow cut-the-apparatus-epic

- close_scope: workflow
- close_id: cut-the-apparatus-epic
- workflow: cut-the-apparatus-epic
- closed_at: 2026-08-14T22:46:54+00:00
- summary: Workflow close for cut-the-apparatus-epic. Eight delivered tickets, none retired, --accept-new used nowhere. CA-05 carries two close receipts by design; the earlier one is marked superseded_by the reconciled one and is excluded from the count, not deleted. The cumulative findings ledger (278 rows) is archived at closed-snapshot/deferred_findings.yaml and recorded in this manifest under findings_ledger; disposition.py reads it from there. GOAL-apparatus-cut is MISSED and awaits the owner's recorded acceptance on PR #272.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket AT-01

- close_scope: ticket
- close_id: AT-01
- workflow: attribute-the-catch-epic
- closed_at: 2026-09-06T16:17:44+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket AT-02

- close_scope: ticket
- close_id: AT-02
- workflow: attribute-the-catch-epic
- closed_at: 2026-09-06T16:17:44+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket AT-03

- close_scope: ticket
- close_id: AT-03
- workflow: attribute-the-catch-epic
- closed_at: 2026-09-06T16:17:44+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket AT-04

- close_scope: ticket
- close_id: AT-04
- workflow: attribute-the-catch-epic
- closed_at: 2026-09-06T16:17:44+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out workflow attribute-the-catch-epic

- close_scope: workflow
- close_id: attribute-the-catch-epic
- workflow: attribute-the-catch-epic
- closed_at: 2026-09-06T16:17:54+00:00
- summary: attribute-the-catch: the four record kinds (CATCH/REACH/BLIND/PRICE), the surfaces that ask for them, the refactor prompt, and AT-04's clause-by-clause evaluation. Six goals MET, one clause DESIGNED-NOT-APPLIED because the 364-row ledger it would dispose lives on epic/stabilize-substrate and arrives with #296. SF-305 repaired and extended to its class; SF-306 and SF-307 deferred to #319 and #320.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket AT-01

- close_scope: ticket
- close_id: AT-01
- workflow: attribute-the-catch-epic
- closed_at: 2026-09-06T20:38:09+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket AT-02

- close_scope: ticket
- close_id: AT-02
- workflow: attribute-the-catch-epic
- closed_at: 2026-09-06T20:38:10+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket AT-03

- close_scope: ticket
- close_id: AT-03
- workflow: attribute-the-catch-epic
- closed_at: 2026-09-06T20:38:10+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out ticket AT-04

- close_scope: ticket
- close_id: AT-04
- workflow: attribute-the-catch-epic
- closed_at: 2026-09-06T20:38:10+00:00
- summary: (none given)
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out workflow attribute-the-catch-epic

- close_scope: workflow
- close_id: attribute-the-catch-epic
- workflow: attribute-the-catch-epic
- closed_at: 2026-09-06T20:38:57+00:00
- summary: attribute-the-catch: the four record kinds, the surfaces that ask for them, the refactor prompt, and AT-04's clause-by-clause evaluation. Zero model delta; TLC run at close on the converged model. SF-305 repaired and extended to its class; SF-306 and SF-307 deferred to #319 and #320.
- feedback_status: unreviewed

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

## Close-out workflow evidence-sized-delivery

- close_scope: workflow
- close_id: evidence-sized-delivery
- workflow: evidence-sized-delivery
- closed_at: 2026-11-11T23:45:04+00:00
- summary: Epic #234 evidence-sized delivery: ESD-01..07 delivered as instruction/attribution/architecture/test-graph guidance; no-op model result
- feedback_status: items-recorded

Set `feedback_status` to `none-found` or `items-recorded`, then record findings as `### SF-NNN` blocks below using the field list above.
Every finding must become a ticket or PR against spec-double-compiler / tla-spec-dev; put its URL in `recommendation:` and set `status: filed`.

### SF-ESD-01 — census rejects a cross-epic duplicate; `--surface` writes only to production
- category: tool-defect
- target: skills/git-epic-workflow/scripts/census.py (lines ~203, ~349, ~394); references/deferment.md:151
- observed_on: tla-spec-dev @ epic #234 manual pass (MAN-01, MAN-02)
- evidence: specs/results/evidence-sized-delivery/finalization/README.md §5a
- severity: wrong-result
- root_cause: tool
- recommendation: https://github.com/haydenrear/tla-spec-dev-plugin/issues/264
- status: filed

### SF-ESD-02 — validate_assignment accepts leftover template placeholders
- category: tool-defect
- target: skills/git-epic-workflow/scripts/validate_assignment.py
- observed_on: tla-spec-dev @ epic #234 manual pass (MAN-03)
- evidence: specs/results/evidence-sized-delivery/finalization/README.md §5a
- severity: missed-check
- root_cause: tool
- recommendation: https://github.com/haydenrear/tla-spec-dev-plugin/issues/264
- status: filed

### SF-ESD-03 — spec.workflow.cleanup guard is always true; can delete the test_graph project
- category: graph-node-defect
- target: test_graph spec_workflow_cleanup.py:35 (`bool(str(repo))`); GraphModel.kt ordering (MAN-05)
- observed_on: tla-spec-dev @ epic #234 review and manual pass (MAN-04, MAN-05)
- evidence: specs/results/evidence-sized-delivery/finalization/README.md §5a
- severity: destructive
- root_cause: instrument
- recommendation: https://github.com/haydenrear/tla-spec-dev-plugin/issues/261 ; https://github.com/haydenrear/tla-spec-dev-plugin/issues/262
- status: filed

### SF-ESD-04 — step-sizing and graph-review changes need a blind re-measure
- category: budget-and-metric
- target: skills/git-epic-workflow/references/step-sizing.md; skills/test-graph/references/graph-architecture-review.md
- observed_on: tla-spec-dev @ ESD-07 (#270), after evaluation ticket ESD-06
- evidence: specs/results/evidence-sized-delivery/ESD-07/README.md
- severity: unmeasured
- root_cause: process
- recommendation: https://github.com/haydenrear/tla-spec-dev-plugin/issues/264
- status: filed
