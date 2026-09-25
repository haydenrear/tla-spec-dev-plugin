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

MEASURED, AND A KNOWN WEAKNESS OF THIS GRADER. Over 6 runs at ac5f7491+ it
passed 3 of 6, while the case's two heavy graders passed 6 of 6. The prompt asks
"tell me what this run actually measured"; it does not ask for the remedy. So
this grader wants something the question did not request -- the README's
*over-specifies the means* class, and the reason the case means 0.89 rather
than 1.00.

It is LEFT UNCHANGED ON PURPOSE. Loosening a pattern or dropping a weight after
seeing the score is how four changes were made to one case reading noise as
signal earlier in this epic. Either the prompt should ask for the remedy or this
grader should go; that is a decision with a measurement behind it, for SI-23,
not an edit to make the number look better.

Reads the FINAL RESPONSE only.
