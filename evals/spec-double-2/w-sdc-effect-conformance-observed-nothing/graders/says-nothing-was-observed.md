---
type: regex
pattern: '(?is)(0|zero|no) (observed|effects?|cases?|adapters?)[^.\n]{0,60}(observed|executed|ran|run)|nothing (was )?(observed|executed|ran|run)|no (adapter|case)s? (were|was) (run|executed)|empty (observation|result|corpus)|did ?n.t (observe|execute|run) anything'
weight: 4
---

THE BEHAVIOUR. The verdict line contains its own refutation:

    0 observed effect(s) over 0 case(s), 15 declared port(s), ... 15 dead port(s)

Zero cases were executed, so "never observed" is trivially true of every
declared port and says nothing about any of them. The run measured **nothing**.
The `--cases-dir` argument is what supplies a corpus to observe, and it was not
passed; the CLI says so itself, in a NOTE, after the accusations.

The agent passes by naming the empty observation set in any spelling: the zero
counts, "nothing ran", "no adapter was executed", "an empty corpus".

This is the heaviest grader in the case because it is the whole question. An
answer that stops at "be careful" or "double-check first" without identifying
that the observation set is empty has not read the output.

OBSERVED, NOT INFERRED. SI-21 worktree at `ac5f7491`, 2026-09-25.

Reads the FINAL RESPONSE only.
