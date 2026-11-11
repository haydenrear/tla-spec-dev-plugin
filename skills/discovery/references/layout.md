# Assumed repository layout

Moved here from `SKILL.md` by SI-09 (progressive disclosure). The card carries
the one-line verification and the stop-and-reconcile rule; this page is the tree
those checks are against.

When kicking off on a repo, assume — and verify — this layout exists:

```
specs/
  program_model/          # accepted whole-program baseline
    Core.tla              # shared constants and operators
    Internal.tla + .cfg   # internal view -> spec-unit cases
    External.tla + .cfg   # external/public view -> Test Graph cases
    actions.yml           # per-action layer, controllability, what it generates
    adapters.py           # spec-unit + Test Graph adapters, projections
    case_adapters.toml    # internal action -> spec-unit adapter
    testgraph_bindings.yml# external action -> Test Graph adapter
    spec_manifest.yaml    # ports, invariants, finite model, onboarding status
  .history/               # append-only workflow history (ALWAYS present)
    <workflow-name>/<entry>/manifest.json, summary.md, snapshots/
  current/                # only while a ticket workflow is in flight
  desired_program_model/  # only while a ticket workflow is in flight
    ticket_plan.yaml      # ticket source of truth when present
  tickets/<ticket-id>/    # open ticket workspaces
test_graph/
  build.gradle.kts        # graph composition: testGraph("name") { ... }
  sources/                # JBang/uv node scripts
  build/validation-reports/<runId>/  # evidence from prior runs
```

The Core/Internal/External split, `actions.yml` and `testgraph_bindings.yml` are
the layout *where the repository has them*. A single canonical module named in
`spec_manifest.yaml`, with its non-decomposition recorded there, is a complete
baseline, not a partial one (this plugin's own `TlaSpecDevCli.tla` is that case).

Verify with one pass before reading anything deeply:

```bash
ls specs/ specs/program_model/ specs/.history/ test_graph/ 2>&1
```

**If `specs/program_model` or `test_graph/` is missing, stop and reconcile.** The
repo is not onboarded to this workflow. Do not silently fall back to raw code
discovery: surface the gap and offer first onboarding via the
spec-double-compiler skill (`tla-spec-dev --spec-root specs scaffold project`)
and the test-graph skill (`<test-graph-skill>/scripts/scaffold.py <repo-root>`).

If only some files are missing (for example no `External.tla`), that is a
stop-and-reconcile checkpoint too — the baseline is incomplete, not merely
differently shaped.
