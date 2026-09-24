---
type: regex
pattern: '\b(Yes|yes|YES)\b'
weight: 2
---

Reads the final response only. The answer is yes, and the fixture is what makes
it so.

WHY THIS GRADER WAS UNEARNABLE UNTIL 2026-09-24 (EA-DF-09). It used to read:
"the shared fixture's home is branched from a home carrying the skt plugin, so
the true answer is yes." That home was real on the OTHER side of SI-15's move --
skill-manager's harness placed it with a `fixture` plugin whose SessionStart
hook copied a prebuilt workspace in. That plugin could not come with the cases
(a case declaring `plugins:` silently loses this plugin's hooks, SI-14-DF-01),
so the home never arrived and nothing replaced it. `place_moved_fixture` then
printed "ships no fixture/ -- by design", which is the one thing it exists to
tell apart from "the fixture was lost in the move". This case was the second
kind and was reported as the first.

With no home anywhere, the honest answer to the prompt was NO. The agent gave
it, with five cited read-only checks, and lost two weight-units for being right.
Measured twice at 0.67 on this epic's first billed rung.

The fixture now carries the EVIDENCE rather than the live tree: a real listing
of a real project home, and the real generated wrapper that home ships. Neither
is invented -- both were taken from `.skill-manager/` on 2026-09-24 -- and
together they are what the question is actually about. This also keeps the case
inside the corpus convention (fixtures here are one or two recorded files) and
away from the 20,000-entry ceiling that leaves six other cases UNDECIDED.

THE DISCRIMINATION THIS CASE MEASURES. In the listing, `skills/` holds ten
units and skt is NOT among them. skt appears only under
`plugins/tla-spec-dev/skills/skt`, because it is a CONTAINED skill of the
tla-spec-dev plugin, and `bin/cli/skt` is the front door that resolves it --
the wrapper's own line reads
`rel="plugins/tla-spec-dev/skills/skt/src/skt/cli.py"`.

So an agent that looks only under `skills/` finds nothing and answers no. That
is not hypothetical: four eval runs did exactly this, concluded skt was absent,
and replayed `wt/bootstrap-home.sh` by hand. An agent that knows a unit resolves
at three rungs finds it at the third and answers yes. The `Yes` this grader
looks for is that discrimination, and it is now decidable from what the case
actually places.
