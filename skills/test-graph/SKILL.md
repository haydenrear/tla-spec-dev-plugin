---
name: test-graph
description: >-
  Work with the test-graph validation system — scaffold a test_graph project,
  add JBang/uv nodes, compose graphs, discover/plan them, run one graph or all
  graphs, and aggregate reports. Trigger on "set up validation nodes", "compose
  a validation graph", "run test_graph", "debug a failing graph", or extending
  an existing test_graph project.
---

# test-graph skill

You are helping the user build or extend a **test_graph** project: a polyglot
validation DAG where each node is a small JBang or uv script that self-describes
metadata and returns a structured `NodeResult`.

This repo is the skill. This file is the agent-facing entry point; durable detail
lives under `references/`.

## Why Test Graph Exists

Test graph exists to eliminate degenerate testing behavior. Agents are often
capable of finding the shortest path to a green test, and that path can be wrong:
asserting the current broken behavior, mocking away the real failure, testing an
implementation detail the bug itself controls, or writing a narrow regression
that proves the patch instead of the user-visible behavior.

Test graph moves validation onto the plane of behavior. A good graph exercises
the system the way a user, operator, browser, client, or downstream service
would: it can scale up real infrastructure, seed real fixtures, drive real
workflows, and assert on externally meaningful outcomes. The point is not heavier
tests for their own sake — it is a test that is hard to satisfy by exploiting the
same bug it is supposed to catch.

Author graph nodes as reusable behavioral contracts anchored to behavior rather
than to private code shape, so they survive refactors. When in doubt, ask what
evidence would convince a skeptical user, and encode that evidence as testbed,
fixture, action, assertion, and evidence nodes with explicit dependencies.

## Start Here

Use the skill scripts first. They auto-detect the active scaffolded
`<repo>/test_graph/` from the repo root or anywhere inside the scaffold.

| Goal | Command |
| --- | --- |
| Scaffold into a repo | `<skill>/scripts/scaffold.py <repo-root>` |
| Prepare managed provider bindings | `<skill>/scripts/prepare-bindings.py` |
| Migrate legacy provider symlinks | `<skill>/scripts/migrate-bindings.py` |
| List registered graphs | `<skill>/scripts/discover.py` |
| Plan one graph, render `docs/<graph>.dot` / `.png` | `<skill>/scripts/discover.py <graph>` |
| Run one graph | `<skill>/scripts/run.py <graph>` |
| Run every graph serially | `<skill>/scripts/run.py --all` |
| Clean scaffold build outputs | `<skill>/scripts/clean.py` |
| Add a JBang node | `<skill>/scripts/new-jbang-node.py <node-id> <kind>` |
| Add a uv node | `<skill>/scripts/new-uv-node.py <node-id> <kind>` |
| Add GitHub Actions | `<skill>/scripts/github-action.py <repo-root>` |

Raw Gradle tasks exist but are lower-level equivalents. Prefer the scripts in
docs, CI, and agent instructions — they handle root detection and keep the common
workflows discoverable.

If the user asks to run or debug a graph, start with `discover.py` before
`run.py`. If they ask for all validation, use `run.py --all`. If they ask for CI,
read `references/github-actions.md`.

## When a graph fails

**Do not blindly rerun a whole graph after every small fix.** Nodes are
independently runnable scripts, and repeated full-graph runs can waste hours when
the same late node fails for different reasons.

1. Inspect the failed node's report first:
   `<test_graph>/build/validation-reports/<runId>/report.md`, `summary.json`,
   `envelope/<node-id>.json`, and any `node-logs/` entries.
2. Decide whether the failure is isolated or invalidates upstream setup. If
   upstream still produced valid published context, iterate on the failed node
   alone.
3. Resume downstream, or replay one node, with `run.py --resume-from-build … 
   --resume-from-node …` / `--run-only-node …`. The node must have `rerun=true`.
4. After the targeted node passes, rerun the whole graph once from the beginning
   to validate ordering, fresh context, reporting, and integration.

Rerun from the beginning immediately when the fix changes a dependency node,
shared fixture/testbed state, graph composition, node ids, context keys consumed
by multiple downstream nodes, or anything making the previous context stale.

The full loop — direct node invocation with saved context, the resume/run-only
acquisition rules, envelope schema and closure verification, and the managed
process-group requirements — is `references/failure-loop.md`.

If a graph fails in an agent command but passes when re-run manually, or Python,
uv, `PATH`, virtualenv activation or Gradle daemon state looks inconsistent, read
[`references/debug-python-uv-env.md`](references/debug-python-uv-env.md). The
first thing to try for wrapper scripts is often running the exact command with
`python3`, because `python` may only be an interactive shell alias.

## Core Model

- A node is one validation unit with a stable dotted id, one kind, one runtime,
  optional dependencies, and a `NodeResult`.
- The script is the source of truth. It emits `NodeSpec` in
  `--describe-out=<path>` mode; there are no YAML sidecars.
- A graph is declared in the scaffolded `build.gradle.kts` with
  `testGraph("name") { ... }`.
- `node("sources/Foo.java")` or `node("sources/foo.py")` adds a project-owned
  node. `standardNode("stable.dotted.id")` composes a centrally shipped node from
  the scaffold's non-copied `standard-nodes/` catalog. `.dependsOn(...)`,
  `.tags(...)`, `.timeout(...)`, `.cacheable(...)` and `.sideEffects(...)`
  overlay script metadata. Use script-level `NodeSpec.rerun(false)` only when
  direct replay from saved context is unsafe.
- Transitive dependencies resolve from `sourcesDir("sources")` when a node
  depends on a node id not listed explicitly in the graph DSL.
- Data flows downstream through `Context[]`. Publish with
  `NodeResult.publish(key, value)` and read with `ctx.get(upstreamId, key)`.
- Reports live under `<test_graph>/build/validation-reports/<runId>/`.

## Node Shape

Use dependency nodes for reusable setup:

- `testbed`: app/server/container/runtime ready
- `fixture`: seeded data or filesystem state
- `action`: operation performed against the system
- `assertion`: invariant check
- `evidence`: logs, screenshots, dumps, measurements
- `report`: custom aggregation

Do not hide setup inside assertion nodes. If multiple graphs need the same
app/database/user fixture, make one node and declare dependencies on it.

## Editing Rules

- In a consumer scaffold, do not edit `sdk/`, `build-logic/`, or
  `standard-nodes/`. Managed projects generate and ignore those runtime links
  from the committed `provider-bindings.json`; legacy projects keep supported
  symlinks until an explicit `migrate-bindings.py` run. Real changes belong in
  `project_sdk_sources/` in this skill repo and reach consumers through
  `skill-manager sync`.
- Node scripts live in `<repo>/test_graph/sources/` and can import the user's
  real project code with paths relative to that file. From `sources/`, the user
  repo root is `../..`.
- For Java nodes use JBang `//SOURCES ../../src/main/java/...` and optional
  `//DEPS`. For Python nodes prefer uv inline metadata with `[tool.uv.sources]`
  pointing the user package at `../..`.
- When touching `sources/` or `build.gradle.kts`, verify with `discover.py` and
  `discover.py <graph>` before running.
- Before finalizing a validation change, run `run.py <graph>` for the affected
  graph, or `run.py --all` when graph coverage is broad.

## When this skill's own instruction did not work

A graph that will not compose, a wrapper script that refuses, a resume or
run-only path this file describes that the scaffold in front of you does not
have, a failure loop that cannot reach the failing node — when the blocker is
this skill or its scripts rather than the system under test, report it instead of
hand-rolling past it. One row in the PR body's `## Skill changes proposed`
section: the unit, what you hit, and the change you propose as a diff or the
commit that applied it. It asks for no extra run, `none met` is the usual answer,
and nothing blocks on it — but a route around a broken instruction that nobody
records is a cost the next agent pays again.

## Avoid

- One giant script that does setup, action, and assertion.
- Tests that can pass by depending on the bug, mocked-away behavior, or private
  implementation details.
- Patch-shaped regressions that prove only the current fix.
- Renaming node ids casually. Treat ids as public API.
- Ordering via sleeps instead of `dependsOn`.
- Plain stdout as the only result. Return a structured `NodeResult`.
- Leading users or agents to raw `./gradlew` when a wrapper script exists.

## Reference map

Open only the page your task needs.

| Task | Read |
| --- | --- |
| Normal operating guide: root detection, scaffolding, node creation, graph composition, reports | [`references/workflows.md`](references/workflows.md) |
| Dense API/DSL/task reference: `NodeSpec`, `NodeResult`, context wire format, Gradle DSL, Java/Python SDK | [`references/reference.md`](references/reference.md) |
| Debugging a failed graph: direct node invocation, resume/run-only rules, envelope and closure schema | [`references/failure-loop.md`](references/failure-loop.md) |
| Branch environment repository contract, Git fixture policy, OpenTofu outputs, local k3d, required coverage | [`references/environment-repositories.md`](references/environment-repositories.md) |
| Generated GitHub Actions workflow, skill install, symlink repair/preserve modes, private installs | [`references/github-actions.md`](references/github-actions.md) |
| Python/uv/Gradle environment mismatches, `python` alias vs `python3` | [`references/debug-python-uv-env.md`](references/debug-python-uv-env.md) |
| Lightweight future-work notes | [`references/tickets/`](references/tickets/) |
