# Validation report — 20261107-180244

**Graph**: `specWorkflow`

**Trace ID**: `719fc6bfbdcf4109a9d2a5c081d0d710`

**Overall**: ERRORED

**Execution scope**: `run-only-node` from `spec.workflow.failure_cleanup_probe`

**Source build**: `/Users/hayde/IdeaProjects/tla-spec-dev-192-tlc-parsing-casegen/test_graph/build/validation-reports/20261107-175652`

**Source closure SHA-256**: `8d639483dc5bc5a48d97513fdb64499c815534d7f11842f5e91ffd70a95f256b`

**Source context SHA-256**: `b9760b4178240c9db06e64fcb31f8adbd4545d1e69315956d8375bfab70b3dbe`

**Plan evidence**: 1/1 expected node envelopes observed

**Input-context evidence**: 1/1 expected node snapshots observed

**Execution error**: `java.lang.RuntimeException` — node spec.workflow.failure_cleanup_probe errored: node launcher exited with live descendants: 96325

**Nodes**: 1 (passed=0, failed=0, errored=1)

| Node | Status | Duration | Input context | Captured stdout |
|---|---|---|---|---|
| `spec.workflow.failure_cleanup_probe` | **ERROR** | 93174ms | [context/spec.workflow.failure_cleanup_probe.input.json](context/spec.workflow.failure_cleanup_probe.input.json) | [node-logs/spec.workflow.failure_cleanup_probe.stdout.log](node-logs/spec.workflow.failure_cleanup_probe.stdout.log) |

## `spec.workflow.failure_cleanup_probe` — **ERROR**

**Failure**: node launcher exited with live descendants: 96325

executor start: `2026-11-07T18:02:44.737312Z`

executor end: `2026-11-07T18:04:17.911420Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.failure_cleanup_probe.input.json](context/spec.workflow.failure_cleanup_probe.input.json)

### Rerun guidance

Saved input context: [`context/spec.workflow.failure_cleanup_probe.input.json`](context/spec.workflow.failure_cleanup_probe.input.json)

Resume graph:

```bash
./gradlew 'specWorkflow' --resume-from-build '/Users/hayde/IdeaProjects/tla-spec-dev-192-tlc-parsing-casegen/test_graph/build/validation-reports/20261107-180244' --resume-from-node 'spec.workflow.failure_cleanup_probe'
```

Run only this node:

```bash
./gradlew 'specWorkflow' --resume-from-build '/Users/hayde/IdeaProjects/tla-spec-dev-192-tlc-parsing-casegen/test_graph/build/validation-reports/20261107-180244' --run-only-node 'spec.workflow.failure_cleanup_probe'
```

**Node-process stdout**: [node-logs/spec.workflow.failure_cleanup_probe.stdout.log](node-logs/spec.workflow.failure_cleanup_probe.stdout.log)

---
