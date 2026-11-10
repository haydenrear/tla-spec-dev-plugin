# Validation report — 20261107-174044

**Graph**: `specWorkflow`

**Trace ID**: `1ec41a93bb7bbe81455334f1548740ee`

**Overall**: ERRORED

**Execution scope**: `resume-from-node` from `spec.workflow.failure_cleanup_probe`

**Source build**: `/Users/hayde/IdeaProjects/tla-spec-dev-187-close-records/test_graph/build/validation-reports/20261107-173712`

**Source closure SHA-256**: `cbb2e4b6b7d0ec68fffa9758da16ae9da40dac0184d2ba8214cd1adb3fd65e29`

**Source context SHA-256**: `2d94489ebffd1730c55be6269cbf959b59daf320f915ef0f31139c89a425e28f`

**Plan evidence**: 3/3 expected node envelopes observed

**Input-context evidence**: 3/3 expected node snapshots observed

**Execution error**: `java.lang.RuntimeException` — node spec.workflow.failure_cleanup_probe errored: node launcher exited with live descendants: 35911

**Nodes**: 3 (passed=0, failed=0, errored=1, skipped=2)

| Node | Status | Duration | Input context | Captured stdout |
|---|---|---|---|---|
| `spec.reference.adapters_resolve` | _skipped_ | 0ms | [context/spec.reference.adapters_resolve.input.json](context/spec.reference.adapters_resolve.input.json) | [node-logs/spec.reference.adapters_resolve.stdout.log](node-logs/spec.reference.adapters_resolve.stdout.log) |
| `spec.workflow.cleanup` | _skipped_ | 0ms | [context/spec.workflow.cleanup.input.json](context/spec.workflow.cleanup.input.json) | [node-logs/spec.workflow.cleanup.stdout.log](node-logs/spec.workflow.cleanup.stdout.log) |
| `spec.workflow.failure_cleanup_probe` | **ERROR** | 86585ms | [context/spec.workflow.failure_cleanup_probe.input.json](context/spec.workflow.failure_cleanup_probe.input.json) | [node-logs/spec.workflow.failure_cleanup_probe.stdout.log](node-logs/spec.workflow.failure_cleanup_probe.stdout.log) |

## `spec.reference.adapters_resolve` — _skipped_

**Failure**: node skipped after earlier graph failure

executor start: `2026-11-07T17:42:11.307886Z`

executor end: `2026-11-07T17:42:11.307886Z`

spawn exit code: -1

**Input context**: [context/spec.reference.adapters_resolve.input.json](context/spec.reference.adapters_resolve.input.json)

**Node-process stdout**: [node-logs/spec.reference.adapters_resolve.stdout.log](node-logs/spec.reference.adapters_resolve.stdout.log)

---

## `spec.workflow.cleanup` — _skipped_

**Failure**: node skipped after earlier graph failure

executor start: `2026-11-07T17:42:11.278397Z`

executor end: `2026-11-07T17:42:11.278397Z`

spawn exit code: -1

**Input context**: [context/spec.workflow.cleanup.input.json](context/spec.workflow.cleanup.input.json)

**Node-process stdout**: [node-logs/spec.workflow.cleanup.stdout.log](node-logs/spec.workflow.cleanup.stdout.log)

---

## `spec.workflow.failure_cleanup_probe` — **ERROR**

**Failure**: node launcher exited with live descendants: 35911

executor start: `2026-11-07T17:40:44.671907Z`

executor end: `2026-11-07T17:42:11.256576Z`

spawn exit code: 0

**Input context**: [context/spec.workflow.failure_cleanup_probe.input.json](context/spec.workflow.failure_cleanup_probe.input.json)

### Rerun guidance

Saved input context: [`context/spec.workflow.failure_cleanup_probe.input.json`](context/spec.workflow.failure_cleanup_probe.input.json)

Resume graph:

```bash
./gradlew 'specWorkflow' --resume-from-build '/Users/hayde/IdeaProjects/tla-spec-dev-187-close-records/test_graph/build/validation-reports/20261107-174044' --resume-from-node 'spec.workflow.failure_cleanup_probe'
```

Run only this node:

```bash
./gradlew 'specWorkflow' --resume-from-build '/Users/hayde/IdeaProjects/tla-spec-dev-187-close-records/test_graph/build/validation-reports/20261107-174044' --run-only-node 'spec.workflow.failure_cleanup_probe'
```

**Node-process stdout**: [node-logs/spec.workflow.failure_cleanup_probe.stdout.log](node-logs/spec.workflow.failure_cleanup_probe.stdout.log)

---
