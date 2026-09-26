---
name: discovery
description: >-
  Use when kicking off work in a repository and the agent must learn how it
  works before changing it. Starts from the `specs/` tree and the `test_graph`
  project rather than raw source. Trigger on "start this ticket", "pick up this
  issue", "do discovery", "create issues for this repo", "how does this codebase
  work", or landing in an unfamiliar repo.
skill-imports:
  - unit: tla-spec-dev
    path: skills/spec-double-2/SKILL.md
    reason: Canonical semantics of the specs/ tree — program_model, current/desired workflow directories, tickets, and the append-only history this skill mines.
  - unit: tla-spec-dev
    path: skills/spec-double-2/references/ai_retrieval.md
    reason: How to select the smallest executable contract from the spec tree as context for a change.
  - unit: tla-spec-dev
    path: skills/spec-double-2/references/spec_evolution.md
    reason: How specs/.history entries are structured and how to search them.
  - unit: tla-spec-dev
    path: skills/test-graph/references/workflows.md
    reason: How to discover, plan, and read reports from the repository test_graph project during discovery.
---

# discovery

Spec-first repository discovery. In repositories following this workflow,
discovery does **not** start by grepping source code. The repository carries two
machine-validated maps, and they are the entry points:

- The **spec-double-compiler `specs/` tree** — the canonical TLA+ program model.
  It answers *what the program is*: state, actions, invariants, resource
  boundaries, and public surface.
- The **`test_graph/` project** — the behavioral validation DAG. It answers *what
  evidence exists that the program works*: graphs, nodes, and reports anchored to
  externally observable behavior.

Source code is read last, guided by the ports, adapters and actions the spec
already names. The spec is compact, current, and validated by TLC and generated
tests; raw code exploration re-derives a worse version of it.

## Verify the layout first

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

The full expected tree, file by file, is `references/layout.md`.

## Discovery sequence

Read in this order. Each step narrows the next; most tasks never need the whole
tree.

1. **`specs/program_model/spec_manifest.yaml`** — ports, invariants, finite
   model, onboarding status. The table of contents for the program.
2. **`Core.tla` and `Internal.tla`** — the internal state machine: variables,
   actions, guards, invariants. The program narrative in executable form.
3. **`External.tla` — always consider the External view.** External is the public
   surface a harness can drive or observe: HTTP routes, CLI commands, filesystem
   behavior, queue operations. Most tickets change or extend public behavior, so
   ask explicitly: *does this work touch the External view?* If yes, the ticket
   needs External model changes, updated `testgraph_bindings.yml`, and Test Graph
   coverage — plan for that from the start, not at wiring time.
4. **`actions.yml`, `case_adapters.toml`, `testgraph_bindings.yml`** — the map
   from modeled actions to spec-unit and Test Graph adapters. This tells you
   which actions are validated, where, and by what.
5. **In-flight work.** If `specs/current`, `specs/desired_program_model` or
   `specs/tickets/` exist, a workflow is active. Read
   `specs/desired_program_model/ticket_plan.yaml` for the plan, status and
   dependencies before proposing new work — new tickets belong in that plan, not
   beside it.
6. **`specs/.history/`** — before re-deriving any context, search history. Prior
   tickets and workflow closes live here with evidence attached:

   ```bash
   grep -rl "<keyword>" specs/.history/*/*/manifest.json specs/.history/*/*/summary.md
   ```

   Read matching `summary.md` files first, then open referenced snapshots only as
   needed. History is append-only; never edit entries.
7. **Check the test graph.** List and plan graphs to see what behavior is already
   validated and how nodes compose:

   ```bash
   <test-graph-skill>/scripts/discover.py            # list registered graphs
   <test-graph-skill>/scripts/discover.py <graph>    # plan one graph, render docs/<graph>.dot
   ```

   Then look at the most recent
   `test_graph/build/validation-reports/<runId>/report.md` and `summary.json` for
   current evidence. Graph node ids are public API — cite them by id.
8. **Production source, last.** Enter through the boundaries the spec names:
   ports in generated `ports.py`, adapters in `adapters.py` and the repo's
   adapter modules, then the implementation behind them. Retrieve the smallest
   executable contract that explains the boundary you are changing.

## What discovery produces

Shape the output to the scenario that triggered it:

- **Starting an issue/ticket** (with `git-issue-workflow`): the spec slice the
  ticket touches — which actions, variables and invariants change; whether the
  External view changes; which `testgraph_bindings.yml` entries and graph nodes
  cover it; and which history entries carry prior related work. This becomes the
  ticket's `desired/` starting point.
- **Discovery for creating issues** (with `git-issue`): a References section
  pointing at concrete files — spec modules and actions by name, adapter
  bindings, graph node ids, history entry paths — so the implementing agent
  starts from your findings instead of from zero.
- **General repo discovery**: a program narrative summarized from the spec —
  state, actions, invariants, public surface, validation coverage — plus explicit
  gaps where the spec and the code appear to disagree. A spec/code disagreement
  is a finding to report, not to silently resolve.

## When this skill's own instruction did not work

Discovery has two stop-and-reconcile points above — a missing
`specs/program_model` or `test_graph/`, and a baseline that is only partly there
— and both assume a route forward exists. When one does not, or when any
instruction here turned out not to fit the repository in front of you, say so
where the work is reported instead of quietly working around it: one row in the
PR body's `## Skill changes proposed` section — the unit, what you hit, and the
change you propose as a diff or the commit that applied it — or one line to the
user when there is no PR. A spec/code disagreement is a finding about the
repository; an instruction that could not be followed is a finding about this
skill, and the agent that hit it is the only one who can see it. It asks for no
extra run, and it is never a gate on anything.

## Anti-patterns

- Grepping the source tree before reading `spec_manifest.yaml`.
- Treating the Internal view as the whole program and skipping `External.tla`.
- Re-deriving project history from git log when `specs/.history` has curated
  summaries with evidence attached.
- Proposing tickets outside `ticket_plan.yaml` while a desired/current workflow
  is in flight.
- Running whole test graphs during discovery. Discovery reads plans and past
  reports; `run.py` is for validation, not exploration.
- Silently onboarding a repo that is missing `specs/` or `test_graph/` instead of
  surfacing the gap first.

## Reference map

| Task | Read |
| --- | --- |
| The expected `specs/` and `test_graph/` tree, file by file | `references/layout.md` |
| Selecting the smallest executable contract as context | spec-double-2 `references/ai_retrieval.md` |
| How `specs/.history` entries are structured and searched | spec-double-2 `references/spec_evolution.md` |
| Discovering, planning and reading test_graph reports | test-graph `references/workflows.md` |
