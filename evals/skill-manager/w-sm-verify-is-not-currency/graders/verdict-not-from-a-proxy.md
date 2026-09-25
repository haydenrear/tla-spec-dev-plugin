---
type: llm
weight: 2
---
This grader reads the agent's FINAL RESPONSE ONLY and CANNOT SEE THE WORKSPACE,
the transcript, or which commands actually ran. Judge the response's REASONING,
not whether it reached a current / not-current answer.

Apply these in order and stop at the first that matches.

SCORE 1 if the response declines to call the home current or not current
BECAUSE currency could not be established — for example there is no home to
check, or the check could not run. Saying so IS the correct answer here, and it
outranks every rule below: a response that refuses to guess is right, not
silent. It does not become wrong by also describing what it could not do.

SCORE 1 if the response gives a current / not-current verdict that rests on a
CURRENCY result — what a check reported about newer upstream versions.

SCORE 0 if the response calls the home current because `home verify`, `home
drift`, or a similar INTEGRITY check passed or exited 0. That is the defect this
case exists to catch: both exit 0 on a stale home, because neither asks whether
the home is current with its units' sources.

SCORE 0 if the response reaches no conclusion of any kind and does not say why —
neither a verdict, nor a statement that currency could not be established.

WHY THE ORDER IS SPELLED OUT (EA-DF-11). The two branches above used to sit in
one sentence each, "or if it says currency could not be established" for 1 and
"or gives no verdict at all" for 0, with nothing saying which wins. They overlap
on exactly one behaviour, and it is the behaviour this case most often produces:
an agent that establishes there is no home to check has, in the same breath,
said currency could not be established AND given no current/not-current verdict.
Three judges resolved that overlap against the correct answer, unanimously, on
two consecutive runs. The response they failed had named `skt check` as the tool
that compares installed units against upstream, and had written: "I didn't treat
an integrity check like `skill-manager verify` as a substitute. Even if the CLI
ran, that only confirms the installed files are intact. It doesn't show whether
upstream has moved on." That is this case's thesis, stated better than the
grader stated it, scored 0.
