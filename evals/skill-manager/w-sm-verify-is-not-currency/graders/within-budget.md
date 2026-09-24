---
type: file_exists
path: .eval/within-budget
weight: 1
---

At most nine Bash calls. Counts calls, not which ones; a rebuilt-by-hand
currency check over `git rev-parse` per unit still blows this, which is what
the budget is for.

WHY NINE AND NOT FIVE. Five was calibrated when this case shipped NO fixture:
there was no home to inspect, so an agent could only look around, find nothing
and say so, and five calls was generous for that. Adding the stale-home fixture
changed the task, and the budget was not moved with it -- measured three times
after the fixture landed, `within-budget` failed 3 of 3 while the judge passed
3 of 3. A grader that fails every run is not measuring efficiency; it is
recording that somebody moved the goalposts and left the flag behind.

The honest path now costs more than five, and the cost is legible:

    1  orient in the workspace
    2  find the home under cases/w-sm-verify-is-not-currency/
    3  read units.lock.toml -- what is pinned, and to what sha
    4  `cd` to the home and run `skt check`, which has no --home flag and
       resolves the home from the working directory
    5  read what it reported

Nine leaves room for an agent that checks `skt --help` first, or looks in one
wrong place before the right one, without leaving room for reconstructing
per-unit currency by hand -- that needs one `git` call per unit, and the
fixture's plugin alone contains eleven.

BUDGETS ARE PART OF THE FIXTURE, NOT INDEPENDENT OF IT. That is the general
lesson, and it is why this note exists rather than a silent number change: a
`max_calls` ceiling encodes an assumption about how much there is to look at,
so any change to what a case PLACES is also a change to what its budget should
be. Nothing checks that the two agree, and nothing warned when they stopped.
