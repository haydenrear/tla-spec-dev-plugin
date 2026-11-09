# tla-spec-dev Test Graph

This graph validates the `tla-spec-dev` workflow against a disposable git
repository created under `test_graph/build/validation-reports/<runId>/`.

## One command

```bash
python3 test_graph/run-graphs.py          # materialise bindings, run all three graphs, report
python3 test_graph/run-graphs.py --list   # classification only; runs nothing
```

Three graphs are registered and all three run here — `specWorkflow`,
`cliWorkflow`, `effectProviderExamples`. None is opt-in and none is dead, and
`--list` says so rather than leaving it to be inferred. Verdicts are read from
each run's own `summary.json`; a graph with no fresh report is UNDECIDED, not
green. The command always exits 0: it reports, it does not gate.

## Running a graph directly

```bash
# NOT `~/.skill-manager`: the test-graph unit lives in the home THIS checkout is
# bound to (a project or worktree `.skill-manager`), and only that copy matches
# the units this checkout was resolved against. See
# references/runtime_requirements.md, "Which Skill Manager home those tools come from".
"$SKILL_MANAGER_HOME"/plugins/tla-spec-dev/skills/test-graph/scripts/discover.py specWorkflow
"$SKILL_MANAGER_HOME"/plugins/tla-spec-dev/skills/test-graph/scripts/run.py specWorkflow
```

The graphs use the test-graph skill **installed in the home** (contained in the
`tla-spec-dev` plugin), not the in-repo `skills/test-graph` source.
`provider-bindings.json` declares only the `skill-root` candidate, so the runner
you invoke decides which SDK the `build-logic`/`sdk`/`standard-nodes` links
point at. Do not run `python3 skills/test-graph/scripts/run.py` here: that binds
the graphs back to the working-tree copy. An edit to `skills/test-graph` reaches
the graphs once it is merged and pulled into the home with
`skt sync tla-spec-dev`.

**Do not run `cd test_graph && ./gradlew <graph>` in a fresh worktree.**
`settings.gradle.kts` includes the build `build-logic`, which is a *managed
provider binding*: a generated symlink, gitignored, with `provider-bindings.json`
as the committed record (they were untracked in 175f5c7c because as tracked
symlinks their blobs held one developer's absolute home path). A fresh checkout
has no `build-logic`, so bare Gradle fails at configuration time in ~2s with
"Included build '.../build-logic' does not exist". The skill runner materialises
the bindings first — `run_gradle()` calls `prepare_provider_bindings_or_warn` —
and so does `run-graphs.py`, explicitly and out loud. Measured both ways in a
fresh checkout at 07b9a97d: bare Gradle BUILD FAILED in 2s; the same checkout
through the runner ran `specWorkflow` to a green report in 1m42s.

The `specWorkflow` graph performs the workflow end to end:

1. `spec.workflow.repo` creates a temporary git repository with
   no spec model yet and publishes the installed `tla-spec-dev` path.
2. `spec.workflow.start` runs `tla-spec-dev --spec-root specs scaffold project`,
   `tla-spec-dev --spec-root specs scaffold workflow`, and
   `tla-spec-dev --spec-root specs open ticket`.
3. `spec.workflow.complete` updates ticket-local `desired/` first, mirrors it
   into `current/`, adds spec adapter/test files, adds Test Graph artifacts, and
   marks the ticket done.
4. `spec.workflow.spec_units` runs
   `tla-spec-dev --spec-root specs run spec-unit-tests` against the
   ticket-local `current/` spec tests.
5. `spec.workflow.close` runs `tla-spec-dev --spec-root specs close ticket`,
   asserts ticket
   `current/ == desired/` closed correctly, verifies project `specs/current`
   and Test Graph artifacts were merged, and commits the close in the temp repo.
6. `spec.workflow.failure_cleanup_probe` creates a separate temporary Test Graph
   project, runs an intentionally failing graph after repository allocation, and
   asserts that the cleanup finalizer still removed that failed graph's fixture
   repo.
7. `spec.workflow.cleanup` removes the disposable git repository from the build
   directory.

The graph is intentionally external to the unit tests: it proves the CLI
work when invoked from a real git-backed repository, including history movement,
promotion, adapter/test merging, and cleanup after both passing and failing
downstream graph paths.

## The nested probe build must own every process it starts

`spec.workflow.failure_cleanup_probe` is the only node that runs a *nested*
Gradle build, so it is the only node that has to think about the executor's
process-ownership contract: when a node launcher exits while any descendant is
still alive, the executor reaps the tree and reports the node as errored with
`node launcher exited with live descendants: <pids>`.

The default Kotlin Gradle plugin compile strategy breaks that contract here.
The probe recopies the project on every run (`copy_probe_project` ignores
`build/`), so the nested build always compiles `build-logic` from scratch, and
the default `daemon` strategy forks
`KotlinCompileDaemon --daemon-autoshutdownIdleSeconds=7200`. That daemon is a
shared, deliberately persistent, user-scoped service — but it is forked as a
descendant of this node's launcher, so it outlives the node and the contract
correctly flags it. The daemon is also shared with the *outer* build, so the
executor's reap of it is not harmless.

The probe therefore pins `kotlin.compiler.execution.strategy=in-process` on
both channels — the `-P` project property (which propagates into the
`build-logic` included build) and the `-D` system property in `GRADLE_OPTS`.
The nested Kotlin compile then happens inside the process tree the node owns
and can reap. Do not drop either flag; the graph goes red at this node without
them.

The node also asserts `nested probe build left no live descendants` directly,
after a bounded drain for processes that are genuinely shutting down (Gradle's
single-use daemon closes its sockets before its exit is observable). That is a
strictly narrower window than the executor's own check, and it exists so a
future regression is reported with the offending command lines in
`node-logs/spec.workflow.failure_cleanup_probe.lingering-descendants.log`
instead of as bare PIDs in a build failure. The executor's check remains the
authority.
