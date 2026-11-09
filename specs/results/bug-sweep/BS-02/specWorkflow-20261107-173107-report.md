# Validation report — 20261107-173107

**Graph**: `specWorkflow`

**Trace ID**: `e722830123c32848cf37f2e3a5060b98`

**Overall**: ERRORED

**Execution scope**: full graph

**Plan evidence**: 9/9 expected node envelopes observed

**Input-context evidence**: 9/9 expected node snapshots observed

**Execution error**: `java.lang.RuntimeException` — node spec.workflow.failure_cleanup_probe errored: node launcher exited with live descendants: 32106

**Nodes**: 9 (passed=7, failed=0, errored=1, skipped=1)

| Node | Status | Duration | Input context | Captured stdout |
|---|---|---|---|---|
| `spec.cli.install` | **PASS** | 6180ms | [context/spec.cli.install.input.json](context/spec.cli.install.input.json) | [node-logs/spec.cli.install.stdout.log](node-logs/spec.cli.install.stdout.log) |
| `spec.reference.adapters_resolve` | _skipped_ | 0ms | [context/spec.reference.adapters_resolve.input.json](context/spec.reference.adapters_resolve.input.json) | [node-logs/spec.reference.adapters_resolve.stdout.log](node-logs/spec.reference.adapters_resolve.stdout.log) |
| `spec.workflow.cleanup` | **PASS** | 6112ms | [context/spec.workflow.cleanup.input.json](context/spec.workflow.cleanup.input.json) | [node-logs/spec.workflow.cleanup.stdout.log](node-logs/spec.workflow.cleanup.stdout.log) |
| `spec.workflow.close` | **PASS** | 6593ms | [context/spec.workflow.close.input.json](context/spec.workflow.close.input.json) | [node-logs/spec.workflow.close.stdout.log](node-logs/spec.workflow.close.stdout.log) |
| `spec.workflow.complete` | **PASS** | 7868ms | [context/spec.workflow.complete.input.json](context/spec.workflow.complete.input.json) | [node-logs/spec.workflow.complete.stdout.log](node-logs/spec.workflow.complete.stdout.log) |
| `spec.workflow.failure_cleanup_probe` | **ERROR** | 99297ms | [context/spec.workflow.failure_cleanup_probe.input.json](context/spec.workflow.failure_cleanup_probe.input.json) | [node-logs/spec.workflow.failure_cleanup_probe.stdout.log](node-logs/spec.workflow.failure_cleanup_probe.stdout.log) |
| `spec.workflow.repo` | **PASS** | 6107ms | [context/spec.workflow.repo.input.json](context/spec.workflow.repo.input.json) | [node-logs/spec.workflow.repo.stdout.log](node-logs/spec.workflow.repo.stdout.log) |
| `spec.workflow.spec_units` | **PASS** | 6687ms | [context/spec.workflow.spec_units.input.json](context/spec.workflow.spec_units.input.json) | [node-logs/spec.workflow.spec_units.stdout.log](node-logs/spec.workflow.spec_units.stdout.log) |
| `spec.workflow.start` | **PASS** | 6392ms | [context/spec.workflow.start.input.json](context/spec.workflow.start.input.json) | [node-logs/spec.workflow.start.stdout.log](node-logs/spec.workflow.start.stdout.log) |

## `spec.cli.install` — **PASS**

executor start: `2026-11-07T17:31:07.480592Z`

executor end: `2026-11-07T17:31:13.660615Z`

spawn exit code: 0

**Input context**: [context/spec.cli.install.input.json](context/spec.cli.install.input.json)

### Assertions

| Name | Status |
|---|---|
| install script succeeded | **PASS** |
| tla-spec-dev wrapper exists | **PASS** |

### Metrics

- `durationMs`: 330

### Subprocesses

| Label | Exit | Duration | PID | Log | Error |
|---|---|---|---|---|---|
| install-tla-spec-dev | 0 | 330ms | 25446 | [`node-logs/spec.cli.install.install-tla-spec-dev.log`](node-logs/spec.cli.install.install-tla-spec-dev.log) |  |

### Artifacts

- `tla-spec-dev` — [`/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/tla-spec-dev-bin/tla-spec-dev`](/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/tla-spec-dev-bin/tla-spec-dev)

### Published context

- `cliPath`: `/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/tla-spec-dev-bin/tla-spec-dev`
- `binDir`: `/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/tla-spec-dev-bin`

**Node-process stdout**: [node-logs/spec.cli.install.stdout.log](node-logs/spec.cli.install.stdout.log)

---

## `spec.reference.adapters_resolve` — _skipped_

**Failure**: node skipped after earlier graph failure

executor start: `2026-11-07T17:33:33.002615Z`

executor end: `2026-11-07T17:33:33.002615Z`

spawn exit code: -1

**Input context**: [context/spec.reference.adapters_resolve.input.json](context/spec.reference.adapters_resolve.input.json)

**Node-process stdout**: [node-logs/spec.reference.adapters_resolve.stdout.log](node-logs/spec.reference.adapters_resolve.stdout.log)

---

## `spec.workflow.cleanup` — **PASS**

executor start: `2026-11-07T17:33:26.842298Z`

executor end: `2026-11-07T17:33:32.954438Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.cleanup.input.json](context/spec.workflow.cleanup.input.json)

### Assertions

| Name | Status |
|---|---|
| fixture repo path was published | **PASS** |
| fixture repo removed | **PASS** |

### Metrics

- `removedRepos`: 1
- `durationMs`: 63

**Node-process stdout**: [node-logs/spec.workflow.cleanup.stdout.log](node-logs/spec.workflow.cleanup.stdout.log)

---

## `spec.workflow.close` — **PASS**

executor start: `2026-11-07T17:31:40.900048Z`

executor end: `2026-11-07T17:31:47.493494Z`

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

- `durationMs`: 520

### Subprocesses

| Label | Exit | Duration | PID | Log | Error |
|---|---|---|---|---|---|
| close-ticket | 0 | 282ms | 30581 | [`node-logs/spec.workflow.close.close-ticket.log`](node-logs/spec.workflow.close.close-ticket.log) |  |
| git-add | 0 | 56ms | 30638 | [`node-logs/spec.workflow.close.git-add.log`](node-logs/spec.workflow.close.git-add.log) |  |
| git-commit | 0 | 102ms | 30645 | [`node-logs/spec.workflow.close.git-commit.log`](node-logs/spec.workflow.close.git-commit.log) |  |
| git-status | 0 | 40ms | 30655 | [`node-logs/spec.workflow.close.git-status.log`](node-logs/spec.workflow.close.git-status.log) |  |

### Artifacts

- `history-manifest` — [`/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/spec-workflow-history-manifest.json`](/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/spec-workflow-history-manifest.json)

### Published context

- `historyDir`: `/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/fixture-repos/spec-workflow-repo/specs/.history/desired-ticket-workflow/ticket-000-FLOW-1`

**Node-process stdout**: [node-logs/spec.workflow.close.stdout.log](node-logs/spec.workflow.close.stdout.log)

---

## `spec.workflow.complete` — **PASS**

executor start: `2026-11-07T17:31:26.278256Z`

executor end: `2026-11-07T17:31:34.146945Z`

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

- `durationMs`: 188

### Subprocesses

| Label | Exit | Duration | PID | Log | Error |
|---|---|---|---|---|---|
| git-add | 0 | 96ms | 28938 | [`node-logs/spec.workflow.complete.git-add.log`](node-logs/spec.workflow.complete.git-add.log) |  |
| git-commit | 0 | 87ms | 28949 | [`node-logs/spec.workflow.complete.git-commit.log`](node-logs/spec.workflow.complete.git-commit.log) |  |

### Artifacts

- `ticket-plan` — [`/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/fixture-repos/spec-workflow-repo/specs/desired_program_model/ticket_plan.yaml`](/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/fixture-repos/spec-workflow-repo/specs/desired_program_model/ticket_plan.yaml)

**Node-process stdout**: [node-logs/spec.workflow.complete.stdout.log](node-logs/spec.workflow.complete.stdout.log)

---

## `spec.workflow.failure_cleanup_probe` — **ERROR**

**Failure**: node launcher exited with live descendants: 32106

executor start: `2026-11-07T17:31:47.517277Z`

executor end: `2026-11-07T17:33:26.814857Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.failure_cleanup_probe.input.json](context/spec.workflow.failure_cleanup_probe.input.json)

### Rerun guidance

Saved input context: [`context/spec.workflow.failure_cleanup_probe.input.json`](context/spec.workflow.failure_cleanup_probe.input.json)

Resume graph:

```bash
./gradlew 'specWorkflow' --resume-from-build '/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107' --resume-from-node 'spec.workflow.failure_cleanup_probe'
```

Run only this node:

```bash
./gradlew 'specWorkflow' --resume-from-build '/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107' --run-only-node 'spec.workflow.failure_cleanup_probe'
```

**Node-process stdout**: [node-logs/spec.workflow.failure_cleanup_probe.stdout.log](node-logs/spec.workflow.failure_cleanup_probe.stdout.log)

---

## `spec.workflow.repo` — **PASS**

executor start: `2026-11-07T17:31:13.689068Z`

executor end: `2026-11-07T17:31:19.796840Z`

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

- `durationMs`: 286

### Subprocesses

| Label | Exit | Duration | PID | Log | Error |
|---|---|---|---|---|---|
| git-init | 0 | 67ms | 26543 | [`node-logs/spec.workflow.repo.git-init.log`](node-logs/spec.workflow.repo.git-init.log) |  |
| git-branch | 0 | 25ms | 26553 | [`node-logs/spec.workflow.repo.git-branch.log`](node-logs/spec.workflow.repo.git-branch.log) |  |
| git-email | 0 | 48ms | 26558 | [`node-logs/spec.workflow.repo.git-email.log`](node-logs/spec.workflow.repo.git-email.log) |  |
| git-name | 0 | 40ms | 26564 | [`node-logs/spec.workflow.repo.git-name.log`](node-logs/spec.workflow.repo.git-name.log) |  |
| git-add | 0 | 44ms | 26572 | [`node-logs/spec.workflow.repo.git-add.log`](node-logs/spec.workflow.repo.git-add.log) |  |
| git-commit | 0 | 57ms | 26578 | [`node-logs/spec.workflow.repo.git-commit.log`](node-logs/spec.workflow.repo.git-commit.log) |  |

### Artifacts

- `fixture-repo` — [`/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/fixture-repos/spec-workflow-repo`](/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/fixture-repos/spec-workflow-repo)

### Published context

- `repoPath`: `/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/fixture-repos/spec-workflow-repo`
- `sourceRepo`: `/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition`
- `ticketId`: `FLOW-1`
- `cliPath`: `/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/tla-spec-dev-bin/tla-spec-dev`

**Node-process stdout**: [node-logs/spec.workflow.repo.stdout.log](node-logs/spec.workflow.repo.stdout.log)

---

## `spec.workflow.spec_units` — **PASS**

executor start: `2026-11-07T17:31:34.176409Z`

executor end: `2026-11-07T17:31:40.863462Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.spec_units.input.json](context/spec.workflow.spec_units.input.json)

### Assertions

| Name | Status |
|---|---|
| cli spec-unit tests succeeded | **PASS** |
| spec-unit output names the ticket desired model | **PASS** |
| spec-unit output reports pass | **PASS** |

### Metrics

- `durationMs`: 717

### Subprocesses

| Label | Exit | Duration | PID | Log | Error |
|---|---|---|---|---|---|
| cli-run-spec-unit-tests | 0 | 716ms | 29775 | [`node-logs/spec.workflow.spec_units.cli-run-spec-unit-tests.log`](node-logs/spec.workflow.spec_units.cli-run-spec-unit-tests.log) |  |

### Artifacts

- `spec-unit-log` — [`/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/node-logs/spec.workflow.spec_units.cli-run-spec-unit-tests.log`](/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/node-logs/spec.workflow.spec_units.cli-run-spec-unit-tests.log)

**Node-process stdout**: [node-logs/spec.workflow.spec_units.stdout.log](node-logs/spec.workflow.spec_units.stdout.log)

---

## `spec.workflow.start` — **PASS**

executor start: `2026-11-07T17:31:19.849297Z`

executor end: `2026-11-07T17:31:26.241291Z`

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
- `durationMs`: 506

### Subprocesses

| Label | Exit | Duration | PID | Log | Error |
|---|---|---|---|---|---|
| cli-scaffold-project | 0 | 93ms | 27685 | [`node-logs/spec.workflow.start.cli-scaffold-project.log`](node-logs/spec.workflow.start.cli-scaffold-project.log) |  |
| cli-scaffold-workflow | 0 | 127ms | 27703 | [`node-logs/spec.workflow.start.cli-scaffold-workflow.log`](node-logs/spec.workflow.start.cli-scaffold-workflow.log) |  |
| cli-open-ticket | 0 | 127ms | 27718 | [`node-logs/spec.workflow.start.cli-open-ticket.log`](node-logs/spec.workflow.start.cli-open-ticket.log) |  |
| git-add | 0 | 65ms | 27734 | [`node-logs/spec.workflow.start.git-add.log`](node-logs/spec.workflow.start.git-add.log) |  |
| git-commit | 0 | 92ms | 27747 | [`node-logs/spec.workflow.start.git-commit.log`](node-logs/spec.workflow.start.git-commit.log) |  |

### Artifacts

- `ticket-dir` — [`/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/fixture-repos/spec-workflow-repo/specs/tickets/FLOW-1`](/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/fixture-repos/spec-workflow-repo/specs/tickets/FLOW-1)

### Published context

- `ticketDir`: `/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107/fixture-repos/spec-workflow-repo/specs/tickets/FLOW-1`

**Node-process stdout**: [node-logs/spec.workflow.start.stdout.log](node-logs/spec.workflow.start.stdout.log)

---
