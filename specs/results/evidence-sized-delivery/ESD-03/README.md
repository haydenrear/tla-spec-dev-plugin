# ESD-03: Test Graph architecture guidance from observed validation failures

Ticket #237 (epic #234, `evidence-sized-delivery`), wave 3. The base is
`3e57ea9e` (the epic tip, containing merged ESD-01 and ESD-02). This ticket
changes instructions and evidence only. It adds no script, node framework,
SDK/runner change, executable example or validator.

## What changed

| File | +/- lines | What |
|---|---|---|
| `skills/test-graph/references/graph-architecture-review.md` | +399 / -0 | New, the one page the entry point links. It has five parts: "a graph change is a product change" (five review questions, linked to `bug_attribution.md` §4.3/§6a/§7d); conceptual roles mapped onto the existing kinds; the A-H checklist, where each rule is tagged with its ESD-01 rows or marked **[hypothesis]** and states its cost; annotated bad/better node-contract snippets (prose); and a worked review of this repository's `test_graph/` that names the dangerous nodes, who owns what, and the recommended changes. |
| `skills/test-graph/SKILL.md` | +8 / -0 | A brief trigger under "Node Shape" and one reference-map row. |
| `test_graph/README.md` | +15 / -3 | Corrects the stale "three graphs registered, none opt-in" (five are registered, and `sktSurface`/`sktHooks` are opt-in, matching `run-graphs.py`). Adds a short "Before changing a node" pointer to the worked review and to `ESD-03-DF-01`. |
| `specs/results/deferred/ESD-03.yaml` | +168 / -0 | Five deferred findings (budget 5), all node-source changes outside the conflict keys. |
| `specs/results/evidence-sized-delivery/ESD-03/*` | this README, `local-signal.md`, validation outputs | evidence |

Line counts are from `git diff --numstat` against `3e57ea9e`.

## Decisions

- **One page, not several.** The checklist and the worked review live together,
  because the worked review is the checklist applied. `failure-loop.md` and
  `reference.md` are linked, not extended, so their existing contracts are
  unchanged.
- **No new node kinds.** Teardown, probe and identity check are *roles*,
  expressed with existing kinds, the `.cleanup`/`finalizer` convention,
  `sideEffects` and `rerun(false)`.
- **No line-number citations.** Rows are cited by id and files by path
  (family F4 / `BS-07-DF-04`).
- **Runtime findings are links.** `RP-07-DF-01`'s carried half (the executor
  names surviving command lines) and `#241`'s raw-`gradlew` gap are cited where
  they are already recorded. They are not re-filed.

## Model result

**No-op.** `specs/current`, `specs/desired_program_model` and
`specs/program_model` are unchanged. The ticket edits prose and evidence and
changes no action, variable or invariant. Under `bug_attribution.md` §7d, prose
and validation-infrastructure guidance is a no-op.

## Validation

| Entry | Result | Output |
|---|---|---|
| `validation.repository_unit` | 407 passed, 1 skipped (the same as ESD-02's base) | `repository-unit.txt` |
| `validation.spec_unit` | 2 failed, 54 passed. These are the same 2 known base failures (`test_every_model_action_is_bound`, `test_unfilled_ledger_template_refuses_the_close`), with no new failures. | `spec-unit.txt` |
| `skill-manager unit validate skills/test-graph` | no markdown skill-import violations | (console) |

Local signal: `local-signal.md`.
