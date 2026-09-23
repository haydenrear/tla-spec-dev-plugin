---
type: regex
pattern: '(provider[- ]binding|build-logic|standard-nodes|materiali[sz])'
weight: 2
---

THE REASON, WHICH IS THE PART THAT TRANSFERS. Naming the right script can be
luck; naming what it does before Gradle starts cannot. The runner materialises
the three managed provider bindings — `sdk`, `build-logic`, `standard-nodes` —
which are generated runtime links that NO checkout carries, because commit
`175f5c7c` removed them as tracked symlinks holding one developer's absolute
home path. `run_gradle()` calls `prepare_provider_bindings_or_warn(root)` first
(`skills/test-graph/scripts/_common.py:680
(prepare_provider_bindings_or_warn)`), and `references/workflows.md:525
(materialize the links before Gradle starts)` is where the skill says so.

OBSERVED: in the SI-19 worktree the three paths were ABSENT before anything ran
and were relative symlinks afterwards
(`.../SI-19/transcripts/step-B-prepare-bindings.txt`). An answer that explains
the wrapper as "it detects the project root" or "it is the documented command"
is not wrong about the command and has not learned the thing that makes bare
Gradle fail.

Reads the FINAL RESPONSE only. Weight 2, below the command itself: this is the
understanding behind a correct answer, not the answer.
