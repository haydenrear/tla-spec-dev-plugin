# Graph architecture review

Read this page **before you author or change a node or a graph, and when you
review a PR that does**. It turns the failure families audited in the
evidence-sized-delivery epic into a checklist for graph authors. The checklist
uses only what already exists: the six node kinds, `Context`/`NodeResult`,
`sideEffects`/`cacheable`/`rerun`/`timeout`/`retries`, finalizer tags and the
executor's process-group supervisor. It proposes no new node kind, runtime type,
SDK feature or runner change. Where a fix needs the runtime, the page links a
finding instead.

**Where the evidence comes from.** Row ids such as `BS-07-DF-05` are rows in
`specs/results/evidence-sized-delivery/ESD-01/inventory.yaml` in the
tla-spec-dev-plugin repository. Family ids F1-F8 are the families in
`failure-families.md` next to that file. Each rule below is tagged:

- **[obs: row]**: a recorded failure that the rule would have flagged;
- **[hypothesis]**: no audited row shows this failure. The rule is reasoned,
  not measured.

Each rule also states its **cost**. None of these rules is free.

## A graph change is a product change

A node is an oracle. When a node changes, review it with the same care as the
code it judges. Ask five questions, and leave none of them blank in the PR:

1. **Oracle validity.** Has this node been shown red on a planted wrong answer,
   a mutation or the untouched base? Does it fail when it exercised nothing?
   (F3: `DEF-124` was a 6-second green over zero cases. `SI-27-DF-01` was a
   counter that counted its own writes.)
2. **False-green and false-red risk.** What can turn this node green without
   the behavior, and what can turn it red with the behavior intact? (F1, F4, F5.)
3. **Effect scope.** What does the node create, write, spawn or reach, and does
   all of it lie inside `ctx.report_dir` and the node's own process tree?
4. **Runtime identity.** Which runner, SDK, home, unit copy, interpreter and
   toolchain does the node actually execute against, and does the report say so?
   (F2.)
5. **Recovery behavior.** Is the node safe to replay from saved context? Must it
   reconstruct its prerequisites first, or must it refuse replay?

When a red turns out to be the instrument and not the subject, record it as
`skills/spec-double-2/references/bug_attribution.md` says. Write origin,
channel and effect as separate axes (§4.3). The correction is one CATCH against
the instrument, with the charged runs listed (§6a). Its anchor is a validation
bin named after the instrument, such as `UNMODELED/test-graph-process-ownership`
(§7d). A changed contract also reruns every instrument that asserts it
(`skills/git-epic-workflow/references/validation-review.md`).

## Conceptual roles vs node kinds

Use the six existing kinds. Some roles that show up in reviews have no kind of
their own. Express them with the metadata that already exists:

| Role in a review | Express it as |
|---|---|
| provision a host, toolchain or app | `testbed`, publishing the handles it created |
| seed data or a file tree | `fixture` |
| teardown or cleanup | a `fixture` whose id ends in `.cleanup` or that is tagged `finalizer`. The executor runs it after an upstream failure once its dependencies have executed. Declare `rerun(false)` unless replay is harmless. |
| deliberate red control (a probe) | an `assertion` over a nested run that is *meant* to fail, with its setup in an upstream node |
| identity / preflight check | a `testbed` or `assertion` that publishes the resolved identity and fails with a named precondition |

If a role really seems to need a new runtime type, that is a successor issue
with its own model decision. Do not encode it in a node.

## The node contract checklist

### A. Declared inputs, outputs, prerequisites and effects

**A1. Depend on what you read, and only that.** Every `ctx.get(upstream, key)`
names a `dependsOn` upstream. Every key a downstream node reads is declared
with `.output(...)`. Do not use `dependsOn` to order nodes. A non-data edge
puts a heavy node in front of unrelated nodes, and after a failure the executor
skips every non-finalizer node that follows. **[obs: `BS-07-DF-05`, effect
*skipped*.]** `spec.reference.adapters_resolve` never ran in bug-sweep
milestone 1 because it sits behind the probe. **Cost:** the true data graph
may let nodes run in an order that shares state you had not noticed. Write
that shared state down as a dependency instead of relying on list order.

**A2. Describe mode must not hide setup effects.** `--describe-out` must be
pure. It must not import a module that touches the filesystem, network or
`PATH`, must not spawn processes, and must not write files. Module-level code
runs at describe time, and the SDK describes **every** script under
`sourcesDir`, not only the ones in the graph. **[obs: `#195 / BS-10`, and the
`support/` comment in
`test_graph/sources/spec_workflow_failure_cleanup_probe.py`.]** A module-level
import of a missing helper took the whole graph red during describe. **Cost:**
helpers move behind `main`, so the code repeats some imports.

**A3. Setup lives in `testbed`/`fixture`, not in an assertion.** An assertion
that builds a project, installs a toolchain or forks a build hides all of that
setup's failure modes behind an assertion's verdict. **[obs: `RP-07-DF-01`,
`BS-07-DF-05`.]** Both are an assertion node that copies a Test Graph project
and runs a nested Gradle build. **Cost:** one more node id, plus the context
keys between the setup and the assertion.

**A4. `sideEffects` lists every effect the node has.** Spawning Gradle or a
nested graph is `process:gradle`. Writing outside the report directory is not
`fs:tmp`. Reaching a package index is `net:external`. The executor validates
the registry but does not schedule by it, so the declaration is a **review cue
and not a guard**. **[hypothesis]** that a complete declaration would have made
`BS-07-DF-05` reviewable earlier: the probe declares only `fs:tmp`. **Cost:**
none at runtime. It only costs the reviewer's attention.

### B. Runtime and provider identity

**B1. Publish the resolved identity and refuse a mismatch with a named error.**
A node that depends on a home, a unit copy, an interpreter or a toolchain
publishes which one it resolved: the path, the version or commit, and the
source (installed, clone or override). When it is not the one under test, the
node fails with a message naming the precondition. It must not fall through to
the next candidate it can find. **[obs: `BS-03-DF-01`, 8 voided eval runs;
`missing-rung family (REACH)` / `SI-25-DF-06`; `#194 / BS-09`;
`SI-25-DF-01`.]** **Cost:** some reds become "environment not as declared"
where they used to be greens on the wrong code. Those greens were never worth
having.

**B2. Verify the runner's version. Do not trust its docs.** The graphs in this
repository run the test-graph copy **installed in the home**, not the branch
copy (`test_graph/README.md`). A documented feature is only as good as the
installed copy. Resume was documented and was broken: no attempt closure was
written under continue-after-failure (`#226 / BS-HP-05`, found by a consumer
epic's close-out, not by any graph). Before a recovery plan relies on resume or
run-only, confirm that the copy you run contains the fix:

```bash
# which commit is the home's copy at, and does it carry the #226 regression test?
git -C "$SKILL_MANAGER_HOME/plugins/tla-spec-dev" log -1 --oneline
grep -rl continueAfterFailureAttemptIsClosedAndReplayableFromThePersistedMode \
  "$SKILL_MANAGER_HOME/plugins/tla-spec-dev/skills/test-graph/project_sdk_sources/build-logic/src/test"
```

**[obs: `#226 / BS-HP-05`; `BS-13-DF-02` is still open: macOS `/var` vs
`/private/var`.]** **Cost:** one lookup per session, which is far cheaper than
trusting a resumed green.

### C. Environment, reviewed separately from product assertions

Review these four as **environment** questions in their own pass, before you
read any assertion about the product. A red from one of them is an
instrument-origin red until a control says otherwise (`bug_attribution.md` §6a).

**C1. Cold vs warm dependency resolution.** State whether the node works from a
cold cache (fresh worktree, empty uv/Gradle/JBang cache, no daemon) and set its
budget for cold. A node that passes only warm is a host property. **[obs:
`SM #295` (cold 3 × 180 s killed, warm 4 m 50 s); `EA-DF-15` → `#248`;
`E10-OWNER-GRAPH-STARTUP-001`.]** **Cost:** cold budgets are long, and cold runs
are slow (F6).

**C2. Network and package-manager failure is an environment outcome.** A node
that downloads anything declares `net:external` and is opt-in, or it fails with
a message naming the fetch. A download failure must never read as a product red.
This repository's good example is `run-graphs.py`, which keeps `sktSurface` and
`sktHooks` opt-in and prints why. **[obs: `EA-DF-15`, `#248`, F7.]** **Cost:**
opt-in graphs run less often.

**C3. Shared caches and daemons are shared state.** `~/.gradle`, the uv cache,
`KotlinCompileDaemon` and the Gradle daemon are shared with the outer build and
with every concurrent agent. Prefer a per-run cache under `ctx.report_dir`
(`effect.providers.examples` sets `UV_CACHE_DIR` that way) or an in-process
strategy. **[obs: `RP-07-DF-01`, confirmed by a three-arm A/B.]** **Cost:** a
private cache is a cold cache, every run. This is the F6/F1 tension: warm reuse
is exactly what process ownership reaps, so any warm-reuse design must state
who owns the long-lived process.

**C4. Concurrent contention for the host, the output tree and the home.** Ask
what this node shares with a concurrent run. The canonical `run.py`/`discover.py`
hold one advisory lock per project output tree (`#241`). A raw `gradlew` does not
take that lock, and the lock does nothing about host load or a shared home.
**[obs: `#241 (polymarket#115)`; `DEF-154` (MH, serial dispatch); CDC
`HOST-LOAD family` ×14.]** **Cost:** serializing graphs costs wall-clock time.
Reviewing contention costs nothing.

### D. Time and liveness

**D1. Readiness is a polled condition with a bounded deadline, never a sleep.**
Poll the thing you need, such as a port, a file or "no live descendants",
against a monotonic deadline. When the deadline passes, report what is *still*
not ready. `await_no_descendants` in the probe is the shape to copy: a 20 s
budget, a 0.5 s poll, and the residue written to
`node-logs/<id>.lingering-descendants.log`. **[obs: `BS-07-DF-05` (Gradle's
single-use daemon closes its sockets before its exit is observable).]** **Cost:**
a readiness predicate has to be written and can itself be wrong. Give it a red
control.

**D2. The node's timeout budget covers all nested work.** `procs.run` takes no
timeout, so the node's `.timeout(...)` is the only bound on everything it
spawns. The executor kills the group and reports `cause: timeout`
(`workflows.md`, *Read `outcome.json`*). Make the node timeout at least the sum
of its bounded nested steps plus a margin, and give each nested step a smaller
bound of its own. A fixed budget against a cost that scales with host load is a
false red waiting for a busy host. **[obs: `BS-07-DF-05` ("node timed out after
180s" at load 28-47); CDC `GO-PERSISTER-TIMEOUT family` ×6.]** **Cost:** long
budgets delay real hangs. Read `load_avg_*` in `outcome.json` before you blame
the code.

**D3. Retries only for an evidenced transient fault, and only where that fault
occurs.** `retries` re-attempts only after a timeout. Use it only when a
recorded run shows a timeout that was transient. Never retry to get past an
assertion. Never put a retry around a whole nested build to absorb contention:
that turns F1 into an invisible cost. **[hypothesis]**: no audited row shows a
retry masking a defect. **Cost:** without retries, a real transient fault errors
the run.

### E. Process ownership, cancellation and cleanup

**E1. The node owns its whole subprocess tree.** It forks no daemons. It pins
in-process strategies (`-Dorg.gradle.daemon=false`, plus
`kotlin.compiler.execution.strategy=in-process` as both a `-P` and a `-D`
property). It asserts *itself* that no descendants are left, naming their
command lines. The executor's supervisor is the authority (`workflows.md`: exit
125 = orphan group reaped, closable `ERRORED`; exit 124 = ownership unprovable,
closure withheld), but it reports bare PIDs. **[obs: `RP-07-DF-01` (confirmed),
`BS-07-DF-05` (inferred).]** **Cost:** in-process compilation is slower and
cannot be shared.

**E2. Cleanup runs on every exit and is scoped to what the node created.**
Release in-node resources in `try/finally`. Put cross-node resources in a
finalizer node. A cleanup path must come from a value the node can **prove it
created**: check that it is non-empty, absolute and under `ctx.report_dir`
before deleting it. `Path("")` is `.`, and a node's working directory is the
`test_graph/` project. **[obs: wave-3 review of the self-improvement-substrate
epic, item 3: "a failing graph node deleted 27 tracked files of `test_graph/`
itself"; F5 `SM #378`, `DEF-OHV-010` (41 GiB of leaked homes, 27 of 46 eval runs
died on ENOSPC).]** **Cost:** a guard that refuses can leave residue. Make the
refusal a red assertion, so the residue is named.

### F. Isolation, idempotency and resource lifetime

**F1. Write only under `ctx.report_dir`.** Use a hermetic home that is never
parented on a real home. A write outside the report directory is declared,
gitignored and justified in the node's docstring. Checkers that walk the
checkout count anything else as source. **[obs: `SI-27-DF-06 / verify.sh
BLIND`, `HP-01-DF-01`, `SM #378`.]** **Cost:** copying fixtures into the report
directory costs disk and time.

**F2. Setup is idempotent: recreate, do not reuse.** A setup node removes its
own previous output and recreates it from scratch, so that a rerun into the
same directory starts from the same state. `spec.workflow.repo` does this.
**[hypothesis]** for this repository, and the shape of F5 elsewhere. **Cost:**
there is no warm reuse.

**F3. Every resource has a stated lifetime.** Name who creates it, who
publishes its handle, who destroys it, and for how long the handle is valid.
Usually that is "this run only". A published path that a finalizer later
deletes is **not** valid input for a later replay (G1). **[hypothesis.]**
**Cost:** one docstring line per resource.

### G. Rerun, replay and recovery, decided at authoring time

**G1. Classify every node for replay, and declare the class.**

| Class | Meaning | Declare |
|---|---|---|
| replay-safe | a function of its saved input context and read-only effects | default `rerun(true)` |
| replay-by-reconstruction | recreates its own resources from the saved context, which must still describe valid inputs | `rerun(true)`, with the reconstruction in the docstring |
| refuses replay | non-idempotent external mutation, one-shot token, claimed port, destructive cleanup, or an input that the run itself destroyed | `rerun(false)` (`reference.md`) |

A node is **not** replay-safe merely because the default says `rerun=true`. A
saved context that points at a path a finalizer has deleted is a stale
prerequisite. Reconstruct the prerequisite with a fresh run from the start; do
not replay against the deleted path. **Cost:** `rerun(false)` gives up
targeted iteration on that node.

**G2. Recovery is designed, not improvised.** For each node, write down:

- which saved input context is valid to replay from;
- when a prerequisite is stale and must be rebuilt fresh;
- which downstream nodes must rerun once its outputs change;
- where the replay report's lineage lives (execution scope v3 records the
  source closure and context digests: `failure-loop.md`);
- that the containing graph is rerun once from the start before anyone calls it
  green.

The failure loop (`failure-loop.md`) is the mechanism; this list is what the
node author owes it. **[obs: `#226 / BS-HP-05`, `#186 / BS-13`.]** **Cost:**
writing those lines down at authoring time.

**G3. `cacheable(true)` only for a pure function of declared inputs.** It
defaults to false. Anything that reads the host, the network, the time or a
home is not pure. **[hypothesis]**: no audited row. **Cost:** none.

### H. The verdict itself

**H1. Demonstrate red before you trust green.** A new or changed assertion
shows red on a planted wrong answer, a mutation or the untouched base, and the
PR cites that run. **[obs: F3, `DEF-124`, `SI-27-DF-01`, `SI-08-DF-01`; the
counter-example is the bug-sweep's 19/19 red-on-base → green-on-branch.]**
**Cost:** one extra run per changed gate.

**H2. Zero exercised is not a pass.** Assert that the count of cases, controls,
mutants or files is greater than zero, as `effect.providers.examples` does with
`controls_total > 0`. **[obs: `DEF-124`, `ATTR-234-36`.]** **Cost:** none.

**H3. Assert behavior, not source text.** Line numbers, literal versions and
copied prose go stale on innocent merges. **[obs: `BS-07-DF-04`, 48 stale
citations; F4.]** **Cost:** behavioral assertions take more setup.

**H4. A missing precondition fails with a name a reader can attribute.** When a
node cannot supply its own environment, it fails with a message that names the
precondition, such as `python 3.11: uv is not on PATH`. That lets the red be
filed against the instrument's bin and not the product. **[obs: F2/F7 voided
eval runs; `bug_attribution.md` §6a.]** **Cost:** these reds still count as
`failed` in `outcome.json`. Attribution reads the message, not the status.

## Annotated node contracts

Illustrative prose snippets, not files to copy into `sources/`.

**Bad: setup hidden in an assertion, effects under-declared, data edge used
for ordering.**

```python
NodeSpec("x.cleanup_probe")
    .kind("assertion")             # A3: builds a project and runs nested Gradle
    .depends_on("x.close")         # A1: reads only x.repo's sourceRepo; the edge is ordering
    .tags("finalizer")             # runs after an upstream failure, as a finalizer
    .timeout("180s")               # D2: one fixed bound over a cold nested build
    .side_effects("fs:tmp")        # A4: spawns Gradle -> process:gradle is missing
```

**Better: the same intent, with the setup, its effects and its budget visible.**

```python
NodeSpec("x.cleanup_probe.project")          # fixture: copies the probe project
    .kind("fixture").depends_on("x.repo")
    .side_effects("fs:tmp").output("probeRoot", "string")

NodeSpec("x.cleanup_probe")                  # assertion: one nested run, owned tree
    .kind("assertion").depends_on("x.cleanup_probe.project")
    .side_effects("fs:tmp", "process:gradle")
    .timeout("<cold nested build + drain + margin>")   # D2, sized from a cold run
    # body: in-process Kotlin + no daemon (E1); bounded drain that names residue (D1);
    # asserts the nested graph's per-node statuses, not just exit != 0 (H1)
```

**Bad: cleanup trusts an absent context value.**

```python
repo = Path(ctx.get("x.repo", "repoPath") or "")   # "" -> Path(".") == test_graph/
if repo.exists():
    shutil.rmtree(repo)                            # E2: deletes the project on a missing key
```

**Better: cleanup proves it is deleting what the run created.**

```python
raw = ctx.get("x.repo", "repoPath")
repo = Path(raw).resolve() if raw else None
owned = repo is not None and repo.is_relative_to(ctx.report_dir.resolve())
# assert `owned` as a named assertion; delete only when it holds; rerun(false) stays
```

## Worked review: this repository's `test_graph/`

Reviewed at the epic base used by ESD-03 (`origin/epic/evidence-sized-delivery`).
Node sources are in `test_graph/sources/`, and the graphs are in
`test_graph/build.gradle.kts`.

**Who owns what.**

- `test_graph/sources/*` and `support/` are this repository's validation code.
  Their defects are anchored to `UNMODELED/<instrument>` bins.
- The executor, supervisor, SDK and runner are the **test-graph skill**
  (`skills/test-graph/project_sdk_sources`). The graphs run the copy *installed
  in the home*, so a branch edit is not under test until it reaches a home
  (`#194 / BS-09`). This plugin ships that runner, so its defects are
  product-origin here (`bug_attribution.md` §4.3).
- Homes and installed units belong to skill-manager.

**Dangerous nodes, most dangerous first.**

| Node (graph) | What the checklist flags | Evidence | Recommended change (owner) |
|---|---|---|---|
| `spec.workflow.failure_cleanup_probe` (specWorkflow) | A1, A3, A4, C3, C4, D2, E1. It is an assertion that copies a project and runs a nested Gradle build; it declares only `fs:tmp`; its fixed 180 s budget covers a cold `build-logic` compile; its `dependsOn` close edge is ordering; it is tagged `finalizer`, so it runs after an upstream failure and then gates `adapters_resolve` | `RP-07-DF-01`, `BS-07-DF-05` (13 runs, 7 innocent tickets) | Split the setup into a fixture, declare `process:gradle`, depend on `spec.workflow.repo`, size the budget from a cold run (`ESD-03-DF-02`). The executor naming surviving command lines is `RP-07-DF-01`'s carried half (runtime, not this ticket). |
| `spec.workflow.cleanup` (specWorkflow and the probe's nested graph) | E2, F3. It deletes `Path(ctx.get(...) or "")`. With no published `repoPath`, the path is `.`, which is the `test_graph/` project. It is a finalizer, so it runs after an upstream failure, and under `--continue-after-failure` it runs unconditionally. `rerun(False)` is correct | wave-3 review item 3 (27 tracked files deleted). The recorded fix changed the install path; at this base the cleanup still has no guard | Guard on non-empty, under-`report_dir` paths and assert it (`ESD-03-DF-01`) |
| `skt.wrapper-installed` (sktSurface, sktHooks; opt-in) | C1, C2, D2. A testbed that may download CPython (`uv python install`, nested timeout 900 s, plus two 120 s finds) inside a node whose own timeout is 900 s. A missing tool is a named `FAIL` (H4: good) | F6 `SM #295` (cold vs warm), `EA-DF-15` | Make the node budget exceed the nested bounds, or provision interpreters in their own testbed (`ESD-03-DF-03`) |
| `skt.ticket-roundtrip` (sktSurface) | B1. It resolves `git-issue-workflow` from `$SKILL_MANAGER_HOME`, then the **root** `~/.skill-manager`, then a clone of an archived remote. It publishes `giwSource` (good) but does not refuse when the copy found is not the one under test | `missing-rung family (REACH)` / `SI-25-DF-06`; `BS-03-DF-01` (root-home skew) | Refuse a root-home or clone source unless it is explicitly requested (`ESD-03-DF-04`) |
| `effect.providers.examples` (effectProviderExamples) | A3, D2, F1. One assertion runs an entire external validation runner under an 1800 s budget, and writes evidence into the checkout (`examples/effect_providers/evidence/validation-runs/`, gitignored) instead of `report_dir`. Good: a per-run `UV_CACHE_DIR`, `controls_total > 0`, a fresh run id per attempt (replay-safe) | `SI-27-DF-06` (checkers walking build output), `R4-DF-03 / DEF-001` | Move the evidence under `report_dir`, or declare the write and keep it out of checker scans (`ESD-03-DF-05`) |
| `spec.cli.install` (specWorkflow, cliWorkflow) | B1. It installs from `TLA_SPEC_DEV_SOURCE_REPO`, else the checkout, into a per-run bin/cache under `report_dir` (good). Its failure once led to the cleanup above | wave-3 review item 3 | none beyond `ESD-03-DF-01` |
| `spec.reference.adapters_resolve` (specWorkflow) | The good example: it strips `SKILL_MANAGER_HOME`/`PYTHONPATH`, uses an empty `HOME`, and runs from a neutral working directory. Its only risk is its *position*, after the probe | `BS-07-DF-05` (effect *skipped*) | Covered by `ESD-03-DF-02` |

`spec.workflow.repo`, `.start`, `.complete`, `.spec_units` and `.close` are
ordinary: they write under `report_dir`, use one fixture repository, and have
data edges. They are replay-by-reconstruction **only while the fixture
repository exists**. After `spec.workflow.cleanup` has run, replaying them from
saved context points at a deleted path (G1), so recover with a fresh run.

**Graph-level notes.**

- `test_graph/README.md` is the front door for these graphs. The canonical
  commands take the project lock (`#241`), and `cd test_graph && ./gradlew` does
  not.
- Under the current executor, the first non-finalizer red skips every later
  non-finalizer node. So a heavy finalizer-tagged probe placed early costs
  coverage as well as time.

The flag/miss table against ESD-01's families is in
`specs/results/evidence-sized-delivery/ESD-03/local-signal.md`.
