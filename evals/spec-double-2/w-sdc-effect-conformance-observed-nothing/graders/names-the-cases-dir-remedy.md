---
type: regex
pattern: '--cases-dir|cases[_ -]dir|generated case|case (package|corpus)'
weight: 2
---

THE REMEDY. To get a verdict that means anything, the run needs a corpus to
observe:

    run effect-conformance --target specs/current --cases-dir <generated case package>

and a package is produced by `generate cases`. The CLI names this itself in its
closing NOTE ("Supply --cases-dir to diff against a real corpus"), so an agent
that read to the end of the output has it.

Worth knowing and not required by this grader: on the tla-spec-dev checkout
itself there is no `specs/generated/` at all, so there is no package to point at
without generating one first. An answer that says so is more useful than one
that just names the flag, but naming the flag is enough to pass.

Reads the FINAL RESPONSE only.
