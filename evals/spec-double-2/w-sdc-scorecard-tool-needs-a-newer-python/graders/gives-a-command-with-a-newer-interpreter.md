---
type: regex
pattern: '(?:python\s?3\.1[1-9]|uv run|--python 3\.1[1-9])[^\n]{0,200}score_tools|score_tools[^\n]{0,200}(?:python\s?3\.1[1-9]|uv run)'
weight: 2
---

THE REMEDY, AS A COMMAND. The user asked for one. Anything that runs the same
script under an interpreter at 3.11 or newer passes:

    python3.14 examples/validation/scorecards/score_tools.py audit --root specs/results/scorecards
    uv run --python 3.12 examples/validation/scorecards/score_tools.py audit --root specs/results/scorecards

The grader requires the interpreter and the script in the same answer so that a
passing response is an actionable command rather than a general remark about
python versions.

`audit` takes `--root`, not a positional path, and the prompt already has it
right — this grader does not test that, and an agent that silently changes it to
a positional has broken a working command. That is checked nowhere here and is
worth knowing when reading a low score on this case.

Reads the FINAL RESPONSE only.
