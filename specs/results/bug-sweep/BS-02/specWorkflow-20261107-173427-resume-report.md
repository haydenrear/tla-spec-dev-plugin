# Validation report — 20261107-173427

**Graph**: `specWorkflow`

**Trace ID**: `e722830123c32848cf37f2e3a5060b98`

**Overall**: ERRORED

**Execution scope**: `resume-from-node` from `spec.workflow.failure_cleanup_probe`

**Source build**: `/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173107`

**Source closure SHA-256**: `56279ad465bb47aee233d8e1fbe14b5981e7087548b8500c989e635aa3aa1db3`

**Source context SHA-256**: `c8be41879e2bd3aea69d2c2124a79cf6ee36b7c7e86441526be4224ce3df4a77`

**Plan evidence**: 3/3 expected node envelopes observed

**Input-context evidence**: 3/3 expected node snapshots observed

**Execution error**: `java.lang.RuntimeException` — node spec.workflow.failure_cleanup_probe errored: node launcher exited with live descendants: 71016

**Nodes**: 3 (passed=0, failed=0, errored=1, skipped=2)

| Node | Status | Duration | Input context | Captured stdout |
|---|---|---|---|---|
| `spec.reference.adapters_resolve` | _skipped_ | 0ms | [context/spec.reference.adapters_resolve.input.json](context/spec.reference.adapters_resolve.input.json) | [node-logs/spec.reference.adapters_resolve.stdout.log](node-logs/spec.reference.adapters_resolve.stdout.log) |
| `spec.workflow.cleanup` | _skipped_ | 0ms | [context/spec.workflow.cleanup.input.json](context/spec.workflow.cleanup.input.json) | [node-logs/spec.workflow.cleanup.stdout.log](node-logs/spec.workflow.cleanup.stdout.log) |
| `spec.workflow.failure_cleanup_probe` | **ERROR** | 87519ms | [context/spec.workflow.failure_cleanup_probe.input.json](context/spec.workflow.failure_cleanup_probe.input.json) | [node-logs/spec.workflow.failure_cleanup_probe.stdout.log](node-logs/spec.workflow.failure_cleanup_probe.stdout.log) |

## `spec.reference.adapters_resolve` — _skipped_

**Failure**: node skipped after earlier graph failure

executor start: `2026-11-07T17:35:55.176036Z`

executor end: `2026-11-07T17:35:55.176036Z`

spawn exit code: -1

**Input context**: [context/spec.reference.adapters_resolve.input.json](context/spec.reference.adapters_resolve.input.json)

**Node-process stdout**: [node-logs/spec.reference.adapters_resolve.stdout.log](node-logs/spec.reference.adapters_resolve.stdout.log)

---

## `spec.workflow.cleanup` — _skipped_

**Failure**: node skipped after earlier graph failure

executor start: `2026-11-07T17:35:55.157976Z`

executor end: `2026-11-07T17:35:55.157976Z`

spawn exit code: -1

**Input context**: [context/spec.workflow.cleanup.input.json](context/spec.workflow.cleanup.input.json)

**Node-process stdout**: [node-logs/spec.workflow.cleanup.stdout.log](node-logs/spec.workflow.cleanup.stdout.log)

---

## `spec.workflow.failure_cleanup_probe` — **ERROR**

**Failure**: node launcher exited with live descendants: 71016

executor start: `2026-11-07T17:34:27.626160Z`

executor end: `2026-11-07T17:35:55.145176Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.failure_cleanup_probe.input.json](context/spec.workflow.failure_cleanup_probe.input.json)

### Rerun guidance

Saved input context: [`context/spec.workflow.failure_cleanup_probe.input.json`](context/spec.workflow.failure_cleanup_probe.input.json)

Resume graph:

```bash
./gradlew 'specWorkflow' --resume-from-build '/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173427' --resume-from-node 'spec.workflow.failure_cleanup_probe'
```

Run only this node:

```bash
./gradlew 'specWorkflow' --resume-from-build '/Users/hayde/IdeaProjects/tla-spec-dev-188-ledger-disposition/test_graph/build/validation-reports/20261107-173427' --run-only-node 'spec.workflow.failure_cleanup_probe'
```

**Node-process stdout**: [node-logs/spec.workflow.failure_cleanup_probe.stdout.log](node-logs/spec.workflow.failure_cleanup_probe.stdout.log)

---
