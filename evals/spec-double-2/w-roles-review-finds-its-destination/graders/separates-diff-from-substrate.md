---
type: llm
weight: 4
---

This grader reads the agent's FINAL RESPONSE ONLY and CANNOT SEE THE WORKSPACE,
the transcript, or which commands actually ran. Judge only what the response
says.

The prompt gave the agent TWO findings on purpose -- one in the diff under
review, one in the substrate -- and asked for a destination for each.

SCORE 1 if the response gives TWO DIFFERENT destinations and gets the split the
right way round: the diff finding goes into the wave review artifact (a review
comment, the artifact, its sections), and the substrate finding goes somewhere
else that is about changing a skill. It does not have to use the exact filenames.

SCORE 0.5 if it identifies itself as the review agent and names a reading path,
but sends both findings to the same place, or names two destinations without
saying which finding goes where.

SCORE 0 if it never identifies itself as the REVIEW agent, or answers from
general code-review practice with no reference to this plugin.

Apply these in order and STOP at the first that matches.
