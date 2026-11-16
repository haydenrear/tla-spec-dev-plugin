<!--
Cases the regression agent is shown, verbatim, in every brief.

This file is the place to teach the agent. When a lap does something well, add it
under OK. When a lap does something that had to be thrown away or corrected, add
it under NO GO, with what it did and what it should have done. One case is two
to four lines. Say what happened; do not write a new rule.

Everything under "## ATTRIBUTION" goes into every brief. Everything under
"## FIXES" goes only into a brief that allows fixes. Lines inside this comment
are not sent.
-->
## ATTRIBUTION

OK: these were right. Do the same.
- A live agent node failed with "There's an issue with the selected model". The row said origin
  `environment` and quoted that line. Correct: the machine's setup, not the code under test.
- Five graphs passed and one was refused by a gate. The run reported the five as passed, the one as
  errored, quoted the gate's message, and escalated. Correct: it did not stop at the first graph or
  hide the greens.
- A graph printed STILL RUNNING eleven times. The agent ran the same command eleven times and
  nothing else. Correct.

NO GO: these were wrong and had to be corrected by a person.
- A gate said "specs/*/adapters.py are NOT byte-identical (differ: current, desired_program_model)".
  The row said origin `product` and blamed a recent product change for "creating divergent copies
  during test execution". The message already named the cause: three files that must match did
  not. Origin `instrument`; `needed` = "make the copies identical", and nothing more.
- A node failed on its own bug (it picked the wrong execution to inspect). The row said origin
  `product` and described a defect in the program's cancel handling that nobody had observed.
  If you have not seen the program do the wrong thing in a log line you can quote, it is not
  `product`.
- An `environment` row was right, and then the notes added that a ticket "likely changed model
  handling". Nothing quoted supported it. Leave the guess out: a wrong lead costs the reader more
  than no lead.
- A fix commit was labelled with a ticket id whose commits never touched the failing node.
  `introduced_by` and the commit subject name a ticket only when `git log -- <file>` shows it.

## FIXES

OK: fixes of this kind were kept.
- A node was refused because it "recorded no observations". The kept fix recorded each check the
  node ALREADY made as its own assertion, one line per check, reading the values the node had
  computed. No check was added, removed or changed.
- A timeout shorter than the step it waits for; a path that moved; an import that was renamed; a
  fixture file that no longer matches what the node reads. One file, a few lines, obvious from the
  log line that names it.
- A fix was not possible within the limits, and the agent stopped, changed nothing more, and wrote
  what was needed in `escalation`. That is a good result, not a failed one.

NO GO: these fixes were thrown away.
- A node was refused because it "recorded no observations". The fix added one assertion,
  `bool(failed is not None)`, which is true whatever the program does. It made the node green and
  checked nothing. Never add an assertion that cannot fail.
- A check compared the execution's recorded events with the result. It was red. The fix made the
  check read the result summary instead of the events, which passed. That changed what the node
  tests. If a check is red, the check stays as it is: either the thing it reads is wrong (escalate)
  or the node fetched the wrong thing (fix the fetch, not the comparison).
- Five commits, 126 changed lines, against a limit of 60. Each commit was small; together they
  were not. Count ALL your commits before each new one. At the limit, stop and escalate, even if
  you believe the next fix is the last.
- Three different causes were tried for one red node, one after another. After the first fix that
  does not change how the node fails, you do not know the cause. Escalate with what you saw.
- A gate refused because copies of a spec file differed. Do not edit, copy or regenerate files
  under a spec or model directory to satisfy a gate. Escalate and quote the gate.
