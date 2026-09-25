---
type: regex
pattern: '(?:9|[Nn]ine)[^.\n]{0,80}(?:project|specs/current|baseline)|(?:project|specs/current|baseline)[^.\n]{0,80}(?:9|nine)[^.\n]{0,20}fail|failures?[^.\n]{0,25}(?:are|belong|come from)[^.\n]{0,60}(?:project|specs/current|baseline)|not SI-17|are\s*n.?t SI-17|[Nn]ot[^.\n]{0,30}SI-17.{0,20}(?:failures|tests)'
weight: 3
---

THE POINT OF THE CASE. The sentence the user is about to write — "SI-17 has 9
failing spec-unit tests" — is false, and the agent has to say so and say whose
the 9 are.

They are `specs/current`'s. That directory carries those failures on this branch
independently of any ticket, so the same 9 appear for `--ticket <anything>`. The
ticket's own number is different: `--target specs/tickets/SI-17/desired` gives
**7 failed, 46 passed**. The two extra in the project's run are
`test_the_model_has_the_expected_command_actions` and
`test_every_model_action_is_bound`, which fail in `specs/current` because it
carries 18 model actions to SI-17's 15.

Passes on attributing the 9 to the project / `specs/current` / the baseline, or
on stating plainly that they are not SI-17's.

An answer that merely says "the output is ambiguous" without attributing the
failures does not pass — the question asked was whether the sentence is correct.

Reads the FINAL RESPONSE only.
