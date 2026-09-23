---
type: file_exists
path: .eval/forbid-bare-gradlew
weight: 2
---

Written by `lib/checks/expect.py` from the transcript when NO Bash call INVOKED
`gradlew`, and only when the agent made at least one tool call — an idle run
proves nothing, and that condition is the module's, not this grader's.

The rule matches `gradlew` only at the start of a command segment
(`(^|[;&|]\s*)(\./)?gradlew\b`), so `grep -rn gradlew skills/test-graph` — a
reasonable way to find the answer — does not trip it. What trips it is
`cd test_graph && ./gradlew cliWorkflow`, which is the move under test.

Paired with the two response graders deliberately: an agent that tries bare
Gradle first and then reports the runner has still done the thing this case is
about, and the reply alone cannot tell you that.
