---
type: llm
weight: 4
---

This grader reads the agent's FINAL RESPONSE ONLY and CANNOT SEE THE WORKSPACE,
the transcript, or which commands actually ran. Judge only what the response
says.

Question 3 asked what the destination requires of a claim before it may be
written there.

SCORE 1 if the response states the rule in substance: name the observation that
would differ if the claim were false, or mark it explicitly as a belief rather
than a measurement. Any faithful paraphrase counts -- "it must be falsifiable
and say what would falsify it", "measured, or labelled as a guess".

SCORE 0.5 if it identifies itself as the TESTING agent and names both
destinations but gives only a generic quality bar for question 3 -- be accurate,
cite sources, keep it short -- without the falsifiability or belief-marking
requirement.

SCORE 0 if it never identifies itself as the TESTING agent, or sends a measured
correction about the harness only to a bug tracker or a PR comment with no
reference to this plugin.

Apply these in order and STOP at the first that matches.
