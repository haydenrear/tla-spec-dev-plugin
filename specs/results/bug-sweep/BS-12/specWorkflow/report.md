# Validation report — 20261107-180959

**Graph**: `specWorkflow`

**Trace ID**: `231952e0aa3f2601b7536acfda5dfb35`

**Overall**: ERRORED

**Execution scope**: full graph

**Plan evidence**: 9/9 expected node envelopes observed

**Input-context evidence**: 9/9 expected node snapshots observed

**Execution error**: `java.lang.RuntimeException` — node spec.workflow.failure_cleanup_probe errored: node timed out after 180s; executor force-killed the subprocess (see capturedStdoutLog)

**Nodes**: 9 (passed=7, failed=0, errored=1, skipped=1)

| Node | Status | Duration | Input context | Captured stdout |
|---|---|---|---|---|
| `spec.cli.install` | **PASS** | 7406ms | [context/spec.cli.install.input.json](context/spec.cli.install.input.json) | [node-logs/spec.cli.install.stdout.log](node-logs/spec.cli.install.stdout.log) |
| `spec.reference.adapters_resolve` | _skipped_ | 0ms | [context/spec.reference.adapters_resolve.input.json](context/spec.reference.adapters_resolve.input.json) | [node-logs/spec.reference.adapters_resolve.stdout.log](node-logs/spec.reference.adapters_resolve.stdout.log) |
| `spec.workflow.cleanup` | **PASS** | 6150ms | [context/spec.workflow.cleanup.input.json](context/spec.workflow.cleanup.input.json) | [node-logs/spec.workflow.cleanup.stdout.log](node-logs/spec.workflow.cleanup.stdout.log) |
| `spec.workflow.close` | **PASS** | 7385ms | [context/spec.workflow.close.input.json](context/spec.workflow.close.input.json) | [node-logs/spec.workflow.close.stdout.log](node-logs/spec.workflow.close.stdout.log) |
| `spec.workflow.complete` | **PASS** | 6768ms | [context/spec.workflow.complete.input.json](context/spec.workflow.complete.input.json) | [node-logs/spec.workflow.complete.stdout.log](node-logs/spec.workflow.complete.stdout.log) |
| `spec.workflow.failure_cleanup_probe` | **ERROR** | 181043ms | [context/spec.workflow.failure_cleanup_probe.input.json](context/spec.workflow.failure_cleanup_probe.input.json) | [node-logs/spec.workflow.failure_cleanup_probe.stdout.log](node-logs/spec.workflow.failure_cleanup_probe.stdout.log) |
| `spec.workflow.repo` | **PASS** | 6643ms | [context/spec.workflow.repo.input.json](context/spec.workflow.repo.input.json) | [node-logs/spec.workflow.repo.stdout.log](node-logs/spec.workflow.repo.stdout.log) |
| `spec.workflow.spec_units` | **PASS** | 8258ms | [context/spec.workflow.spec_units.input.json](context/spec.workflow.spec_units.input.json) | [node-logs/spec.workflow.spec_units.stdout.log](node-logs/spec.workflow.spec_units.stdout.log) |
| `spec.workflow.start` | **PASS** | 7723ms | [context/spec.workflow.start.input.json](context/spec.workflow.start.input.json) | [node-logs/spec.workflow.start.stdout.log](node-logs/spec.workflow.start.stdout.log) |

## `spec.cli.install` — **PASS**

executor start: `2026-11-07T18:10:01.539110Z`

executor end: `2026-11-07T18:10:08.945098Z`

spawn exit code: 0

**Input context**: [context/spec.cli.install.input.json](context/spec.cli.install.input.json)

### Assertions

| Name | Status |
|---|---|
| install script succeeded | **PASS** |
| tla-spec-dev wrapper exists | **PASS** |

### Metrics

- `durationMs`: 614

### Subprocesses

| Label | Exit | Duration | PID | Log | Error |
|---|---|---|---|---|---|
| install-tla-spec-dev | 0 | 610ms | 1208 | [`node-logs/spec.cli.install.install-tla-spec-dev.log`](node-logs/spec.cli.install.install-tla-spec-dev.log) |  |

### Artifacts

- `tla-spec-dev` — [`/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/tla-spec-dev-bin/tla-spec-dev`](/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/tla-spec-dev-bin/tla-spec-dev)

### Published context

- `cliPath`: `/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/tla-spec-dev-bin/tla-spec-dev`
- `binDir`: `/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/tla-spec-dev-bin`

**Node-process stdout**: [node-logs/spec.cli.install.stdout.log](node-logs/spec.cli.install.stdout.log)

---

## `spec.reference.adapters_resolve` — _skipped_

**Failure**: node skipped after earlier graph failure

executor start: `2026-11-07T18:13:53.176046Z`

executor end: `2026-11-07T18:13:53.176046Z`

spawn exit code: -1

**Input context**: [context/spec.reference.adapters_resolve.input.json](context/spec.reference.adapters_resolve.input.json)

**Node-process stdout**: [node-logs/spec.reference.adapters_resolve.stdout.log](node-logs/spec.reference.adapters_resolve.stdout.log)

---

## `spec.workflow.cleanup` — **PASS**

executor start: `2026-11-07T18:13:47.013613Z`

executor end: `2026-11-07T18:13:53.163679Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.cleanup.input.json](context/spec.workflow.cleanup.input.json)

### Assertions

| Name | Status |
|---|---|
| fixture repo path was published | **PASS** |
| fixture repo removed | **PASS** |

### Metrics

- `removedRepos`: 1
- `durationMs`: 68

**Node-process stdout**: [node-logs/spec.workflow.cleanup.stdout.log](node-logs/spec.workflow.cleanup.stdout.log)

---

## `spec.workflow.close` — **PASS**

executor start: `2026-11-07T18:10:38.511693Z`

executor end: `2026-11-07T18:10:45.896857Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.close.input.json](context/spec.workflow.close.input.json)

### Assertions

| Name | Status |
|---|---|
| open ticket scaffolded the complexity ledger input with TODO sentinels | **PASS** |
| close-ticket succeeded | **PASS** |
| close wrote a complexity ledger entry | **PASS** |
| ledger entry records the delta jointly with retention evidence | **PASS** |
| ledger entry carries the required refinement record | **PASS** |
| ledger entry verdict is recorded | **PASS** |
| active ticket directory removed | **PASS** |
| history directory exists | **PASS** |
| history contains ticket desired | **PASS** |
| history contains ticket external view | **PASS** |
| history has no ticket current (desired-only close) | **PASS** |
| manifest records the desired-only close | **PASS** |
| manifest records no guard weakening | **PASS** |
| project current promoted internal view | **PASS** |
| project current promoted external view | **PASS** |
| project current promoted Test Graph binding | **PASS** |
| project current has spec adapter | **PASS** |
| project current has adapter test | **PASS** |
| project testgraph bindings merged | **PASS** |
| project test_graph sources merged | **PASS** |
| history captured result | **PASS** |
| manifest records replace promotion | **PASS** |
| git-add succeeded | **PASS** |
| git-commit succeeded | **PASS** |
| git-status succeeded | **PASS** |
| git working tree clean after close commit | **PASS** |

### Metrics

- `durationMs`: 928

### Subprocesses

| Label | Exit | Duration | PID | Log | Error |
|---|---|---|---|---|---|
| close-ticket | 0 | 561ms | 6340 | [`node-logs/spec.workflow.close.close-ticket.log`](node-logs/spec.workflow.close.close-ticket.log) |  |
| git-add | 0 | 74ms | 6391 | [`node-logs/spec.workflow.close.git-add.log`](node-logs/spec.workflow.close.git-add.log) |  |
| git-commit | 0 | 118ms | 6397 | [`node-logs/spec.workflow.close.git-commit.log`](node-logs/spec.workflow.close.git-commit.log) |  |
| git-status | 0 | 47ms | 6409 | [`node-logs/spec.workflow.close.git-status.log`](node-logs/spec.workflow.close.git-status.log) |  |

### Artifacts

- `history-manifest` — [`/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/spec-workflow-history-manifest.json`](/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/spec-workflow-history-manifest.json)

### Published context

- `historyDir`: `/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/fixture-repos/spec-workflow-repo/specs/.history/desired-ticket-workflow/ticket-000-FLOW-1`

**Node-process stdout**: [node-logs/spec.workflow.close.stdout.log](node-logs/spec.workflow.close.stdout.log)

---

## `spec.workflow.complete` — **PASS**

executor start: `2026-11-07T18:10:23.422543Z`

executor end: `2026-11-07T18:10:30.190137Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.complete.input.json](context/spec.workflow.complete.input.json)

### Assertions

| Name | Status |
|---|---|
| git-add succeeded | **PASS** |
| git-commit succeeded | **PASS** |
| ticket plan marked done | **PASS** |
| desired internal view updated first-class | **PASS** |
| desired external view updated first-class | **PASS** |
| new external action mapped for Test Graph | **PASS** |
| no ticket-local current/ to converge | **PASS** |
| ticket spec adapter written | **PASS** |
| ticket Test Graph binding written | **PASS** |

### Metrics

- `durationMs`: 195

### Subprocesses

| Label | Exit | Duration | PID | Log | Error |
|---|---|---|---|---|---|
| git-add | 0 | 88ms | 4157 | [`node-logs/spec.workflow.complete.git-add.log`](node-logs/spec.workflow.complete.git-add.log) |  |
| git-commit | 0 | 95ms | 4163 | [`node-logs/spec.workflow.complete.git-commit.log`](node-logs/spec.workflow.complete.git-commit.log) |  |

### Artifacts

- `ticket-plan` — [`/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/fixture-repos/spec-workflow-repo/specs/desired_program_model/ticket_plan.yaml`](/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/fixture-repos/spec-workflow-repo/specs/desired_program_model/ticket_plan.yaml)

**Node-process stdout**: [node-logs/spec.workflow.complete.stdout.log](node-logs/spec.workflow.complete.stdout.log)

---

## `spec.workflow.failure_cleanup_probe` — **ERROR**

**Failure**: node timed out after 180s; executor force-killed the subprocess (see capturedStdoutLog)

executor start: `2026-11-07T18:10:45.920818Z`

executor end: `2026-11-07T18:13:46.963682Z`

spawn exit code: -1

**Input context**: [context/spec.workflow.failure_cleanup_probe.input.json](context/spec.workflow.failure_cleanup_probe.input.json)

### Rerun guidance

Saved input context: [`context/spec.workflow.failure_cleanup_probe.input.json`](context/spec.workflow.failure_cleanup_probe.input.json)

Resume graph:

```bash
./gradlew 'specWorkflow' --resume-from-build '/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959' --resume-from-node 'spec.workflow.failure_cleanup_probe'
```

Run only this node:

```bash
./gradlew 'specWorkflow' --resume-from-build '/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959' --run-only-node 'spec.workflow.failure_cleanup_probe'
```

**Node-process stdout**: [node-logs/spec.workflow.failure_cleanup_probe.stdout.log](node-logs/spec.workflow.failure_cleanup_probe.stdout.log)

---

## `spec.workflow.repo` — **PASS**

executor start: `2026-11-07T18:10:08.996851Z`

executor end: `2026-11-07T18:10:15.639008Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.repo.input.json](context/spec.workflow.repo.input.json)

### Assertions

| Name | Status |
|---|---|
| git-init succeeded | **PASS** |
| git-branch succeeded | **PASS** |
| git-email succeeded | **PASS** |
| git-name succeeded | **PASS** |
| git-add succeeded | **PASS** |
| git-commit succeeded | **PASS** |
| installed CLI path exists | **PASS** |
| fixture repo starts without program model | **PASS** |

### Metrics

- `durationMs`: 301

### Subprocesses

| Label | Exit | Duration | PID | Log | Error |
|---|---|---|---|---|---|
| git-init | 0 | 64ms | 2264 | [`node-logs/spec.workflow.repo.git-init.log`](node-logs/spec.workflow.repo.git-init.log) |  |
| git-branch | 0 | 29ms | 2270 | [`node-logs/spec.workflow.repo.git-branch.log`](node-logs/spec.workflow.repo.git-branch.log) |  |
| git-email | 0 | 36ms | 2273 | [`node-logs/spec.workflow.repo.git-email.log`](node-logs/spec.workflow.repo.git-email.log) |  |
| git-name | 0 | 28ms | 2278 | [`node-logs/spec.workflow.repo.git-name.log`](node-logs/spec.workflow.repo.git-name.log) |  |
| git-add | 0 | 70ms | 2282 | [`node-logs/spec.workflow.repo.git-add.log`](node-logs/spec.workflow.repo.git-add.log) |  |
| git-commit | 0 | 71ms | 2287 | [`node-logs/spec.workflow.repo.git-commit.log`](node-logs/spec.workflow.repo.git-commit.log) |  |

### Artifacts

- `fixture-repo` — [`/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/fixture-repos/spec-workflow-repo`](/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/fixture-repos/spec-workflow-repo)

### Published context

- `repoPath`: `/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/fixture-repos/spec-workflow-repo`
- `sourceRepo`: `/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired`
- `ticketId`: `FLOW-1`
- `cliPath`: `/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/tla-spec-dev-bin/tla-spec-dev`

**Node-process stdout**: [node-logs/spec.workflow.repo.stdout.log](node-logs/spec.workflow.repo.stdout.log)

---

## `spec.workflow.spec_units` — **PASS**

executor start: `2026-11-07T18:10:30.227371Z`

executor end: `2026-11-07T18:10:38.485676Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.spec_units.input.json](context/spec.workflow.spec_units.input.json)

### Assertions

| Name | Status |
|---|---|
| cli spec-unit tests succeeded | **PASS** |
| spec-unit output names the ticket desired model | **PASS** |
| spec-unit output reports pass | **PASS** |

### Metrics

- `durationMs`: 1786

### Subprocesses

| Label | Exit | Duration | PID | Log | Error |
|---|---|---|---|---|---|
| cli-run-spec-unit-tests | 0 | 1785ms | 4943 | [`node-logs/spec.workflow.spec_units.cli-run-spec-unit-tests.log`](node-logs/spec.workflow.spec_units.cli-run-spec-unit-tests.log) |  |

### Artifacts

- `spec-unit-log` — [`/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/node-logs/spec.workflow.spec_units.cli-run-spec-unit-tests.log`](/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/node-logs/spec.workflow.spec_units.cli-run-spec-unit-tests.log)

**Node-process stdout**: [node-logs/spec.workflow.spec_units.stdout.log](node-logs/spec.workflow.spec_units.stdout.log)

---

## `spec.workflow.start` — **PASS**

executor start: `2026-11-07T18:10:15.666082Z`

executor end: `2026-11-07T18:10:23.389467Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.start.input.json](context/spec.workflow.start.input.json)

### Assertions

| Name | Status |
|---|---|
| cli-scaffold-project succeeded | **PASS** |
| cli-scaffold-workflow succeeded | **PASS** |
| cli-open-ticket succeeded | **PASS** |
| git-add succeeded | **PASS** |
| git-commit succeeded | **PASS** |
| program model scaffolded by CLI with both views | **PASS** |
| project workflow scaffolded by CLI | **PASS** |
| ticket directory exists | **PASS** |
| ticket desired carries the whole baseline | **PASS** |
| ticket opens desired-only: no ticket-local current/ | **PASS** |
| no single-module stand-in left behind | **PASS** |
| ticket metadata written | **PASS** |

### Metrics

- `baselineFilesMissing`: 0
- `baselineFilesNotCopiedToTicket`: 0
- `durationMs`: 1172

### Subprocesses

| Label | Exit | Duration | PID | Log | Error |
|---|---|---|---|---|---|
| cli-scaffold-project | 0 | 125ms | 3187 | [`node-logs/spec.workflow.start.cli-scaffold-project.log`](node-logs/spec.workflow.start.cli-scaffold-project.log) |  |
| cli-scaffold-workflow | 0 | 308ms | 3214 | [`node-logs/spec.workflow.start.cli-scaffold-workflow.log`](node-logs/spec.workflow.start.cli-scaffold-workflow.log) |  |
| cli-open-ticket | 0 | 514ms | 3289 | [`node-logs/spec.workflow.start.cli-open-ticket.log`](node-logs/spec.workflow.start.cli-open-ticket.log) |  |
| git-add | 0 | 111ms | 3312 | [`node-logs/spec.workflow.start.git-add.log`](node-logs/spec.workflow.start.git-add.log) |  |
| git-commit | 0 | 96ms | 3319 | [`node-logs/spec.workflow.start.git-commit.log`](node-logs/spec.workflow.start.git-commit.log) |  |

### Artifacts

- `ticket-dir` — [`/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/fixture-repos/spec-workflow-repo/specs/tickets/FLOW-1`](/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/fixture-repos/spec-workflow-repo/specs/tickets/FLOW-1)

### Published context

- `ticketDir`: `/Users/hayde/IdeaProjects/tla-spec-dev-141-close-carries-desired/test_graph/build/validation-reports/20261107-180959/fixture-repos/spec-workflow-repo/specs/tickets/FLOW-1`

**Node-process stdout**: [node-logs/spec.workflow.start.stdout.log](node-logs/spec.workflow.start.stdout.log)

---
