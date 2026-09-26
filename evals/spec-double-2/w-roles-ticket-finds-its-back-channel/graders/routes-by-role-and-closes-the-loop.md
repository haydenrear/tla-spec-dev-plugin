---
type: llm
weight: 4
---

This grader reads the agent's FINAL RESPONSE ONLY and CANNOT SEE THE WORKSPACE,
the transcript, or which commands actually ran. Judge only what the response
says.

The prompt described a situation and never named a role, a file, or a section.

SCORE 1 if the response does all three of these:
  (a) identifies itself as the TICKET agent (that word, or "ticket-agent"
      role) rather than answering generically;
  (b) names a reading path as a file plus a section, not just a skill name; and
  (c) answers question 3 with a way of looking up what became of the finding
      LATER -- a command, or a named file plus what to read in it. It does not
      have to reproduce the exact command.

SCORE 0.5 if it gets (a) and (b) but treats question 3 as "open a PR and wait",
"ask the epic agent", or "check the review" without naming anything a reader
could actually run or open. Reporting with no way to see the outcome is the
write-only channel this routing exists to fix, so a half is the honest score.

SCORE 0 if it answers from general software practice -- file an issue, open a
discussion, add a TODO -- or names no role at all.

A response that also proposes improvements to the substrate still scores on the
three clauses above; extra correct material does not lower it.
