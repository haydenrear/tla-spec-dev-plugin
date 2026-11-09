# Validation report — 20261107-175652

**Graph**: `specWorkflow`

**Trace ID**: `719fc6bfbdcf4109a9d2a5c081d0d710`

**Overall**: ERRORED

**Execution scope**: `resume-from-node` from `spec.workflow.failure_cleanup_probe`

**Source build**: `/Users/hayde/IdeaProjects/tla-spec-dev-192-tlc-parsing-casegen/test_graph/build/validation-reports/20261107-175029`

**Source closure SHA-256**: `d9b6f367e0ba8f6a4ed4f43fc3a122c8c01d6c19003a3aa2d493a8bad16f912e`

**Source context SHA-256**: `b9760b4178240c9db06e64fcb31f8adbd4545d1e69315956d8375bfab70b3dbe`

**Plan evidence**: 3/3 expected node envelopes observed

**Input-context evidence**: 3/3 expected node snapshots observed

**Execution error**: `java.lang.RuntimeException` — node spec.workflow.failure_cleanup_probe errored: node launcher exited with live descendants: 93071

**Nodes**: 3 (passed=0, failed=0, errored=1, skipped=2)

| Node | Status | Duration | Input context | Captured stdout |
|---|---|---|---|---|
| `spec.reference.adapters_resolve` | _skipped_ | 0ms | [context/spec.reference.adapters_resolve.input.json](context/spec.reference.adapters_resolve.input.json) | [node-logs/spec.reference.adapters_resolve.stdout.log](node-logs/spec.reference.adapters_resolve.stdout.log) |
| `spec.workflow.cleanup` | _skipped_ | 0ms | [context/spec.workflow.cleanup.input.json](context/spec.workflow.cleanup.input.json) | [node-logs/spec.workflow.cleanup.stdout.log](node-logs/spec.workflow.cleanup.stdout.log) |
| `spec.workflow.failure_cleanup_probe` | **ERROR** | 98468ms | [context/spec.workflow.failure_cleanup_probe.input.json](context/spec.workflow.failure_cleanup_probe.input.json) | [node-logs/spec.workflow.failure_cleanup_probe.stdout.log](node-logs/spec.workflow.failure_cleanup_probe.stdout.log) |

## `spec.reference.adapters_resolve` — _skipped_

**Failure**: node skipped after earlier graph failure

executor start: `2026-11-07T17:58:31.554440Z`

executor end: `2026-11-07T17:58:31.554440Z`

spawn exit code: -1

**Input context**: [context/spec.reference.adapters_resolve.input.json](context/spec.reference.adapters_resolve.input.json)

**Node-process stdout**: [node-logs/spec.reference.adapters_resolve.stdout.log](node-logs/spec.reference.adapters_resolve.stdout.log)

---

## `spec.workflow.cleanup` — _skipped_

**Failure**: node skipped after earlier graph failure

executor start: `2026-11-07T17:58:31.541082Z`

executor end: `2026-11-07T17:58:31.541082Z`

spawn exit code: -1

**Input context**: [context/spec.workflow.cleanup.input.json](context/spec.workflow.cleanup.input.json)

**Node-process stdout**: [node-logs/spec.workflow.cleanup.stdout.log](node-logs/spec.workflow.cleanup.stdout.log)

---

## `spec.workflow.failure_cleanup_probe` — **ERROR**

**Failure**: node launcher exited with live descendants: 93071

executor start: `2026-11-07T17:56:53.035830Z`

executor end: `2026-11-07T17:58:31.503799Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.failure_cleanup_probe.input.json](context/spec.workflow.failure_cleanup_probe.input.json)

### Rerun guidance

Saved input context: [`context/spec.workflow.failure_cleanup_probe.input.json`](context/spec.workflow.failure_cleanup_probe.input.json)

Resume graph:

```bash
./gradlew 'specWorkflow' --resume-from-build '/Users/hayde/IdeaProjects/tla-spec-dev-192-tlc-parsing-casegen/test_graph/build/validation-reports/20261107-175652' --resume-from-node 'spec.workflow.failure_cleanup_probe'
```

Run only this node:

```bash
./gradlew 'specWorkflow' --resume-from-build '/Users/hayde/IdeaProjects/tla-spec-dev-192-tlc-parsing-casegen/test_graph/build/validation-reports/20261107-175652' --run-only-node 'spec.workflow.failure_cleanup_probe'
```

**Node-process stdout**: [node-logs/spec.workflow.failure_cleanup_probe.stdout.log](node-logs/spec.workflow.failure_cleanup_probe.stdout.log)

---
