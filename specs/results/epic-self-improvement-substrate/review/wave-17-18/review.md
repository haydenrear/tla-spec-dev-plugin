# Waves 17-18 review — epic/self-improvement-substrate

Range: `f4b42169` → `d4eb1abb`. Two tickets: **SI-19** (#368, eval ladder 1/4)
and **SI-20** (#369, eval ladder 2/4). Both landed here, each through a PR into
the epic branch — #1 at `b7548b2d`, #2 at `bf1bbe54`.

Two waves are reviewed together because the epic-owned work that follows SI-20
is not separable from it: three skt fixes, a TLA surface and three home-and-
manifest sweeps all descend from findings SI-20 filed. Splitting the review at
`fada0f60` would put the findings in one document and their consumption in
another.

**Neither wave is a gate.** Wave 19 is SI-21, the third rung.

---

## Block 1 — Model delta applied

**Applied, and it is the largest model delta since wave 4.** `5a8527bf` added
the skt surface to all three spec trees; `2e7ba795` finished its bookkeeping.

| element | where |
| --- | --- |
| `skt_answer` variable, `SktSilent` initial value | `TlaSpecDevCli.tla:166`, `:247` |
| `SktAnswers` — the answer domain | `:176` |
| `SktStatus`, `SktCheck`, `SktTicketSweep` (three nullary actions) | `:779`, `:801`, `:822` |
| `SktPort.worktree_removal` | `:821` |
| type invariant conjunct `skt_answer \in SktAnswers` | `:887` |
| four safety invariants | `:1049`–`:1061` |

The delta exists because **four SI-20 findings had nowhere to attribute to.**
They were being filed `UNMODELED/`, which is the attribution of last resort and
was wrong here: each one is a claim the CLI makes about a surface it did not
establish, which is precisely what an invariant is for. The four map one to one:

| invariant | finding it anchors |
| --- | --- |
| `SktNamesNoEpicItCannotResolve` | SI-20-DF-05 — `skt status` names a long-closed epic as "available" |
| `SktClaimsNoMembershipItDidNotJoin` | SI-20-DF-06 — every epic ticket worktree is told its ticket is not in the plan |
| `SktVerdictCoversEverySurfaceItNames` | SI-20-DF-07 — `skt check` exits 0 "all current" having not checked one of two surfaces |
| `SktPlansNoRemovalWithoutContainment` | SI-20-DF-04 — `ticket sweep` with two epics resolves none, skips containment |

This is the shape the epic was supposed to produce and had not yet: a finding
does not become a change by being filed, it becomes a change when the substrate
**checks** something it did not check before.

## Block 2 — Anchors placed

**Four placed** (above), retiring four `UNMODELED/` attributions. The remaining
SI-19 and EA findings stay `UNMODELED/`: they are harness, home-topology and
manifest defects, and none is a claim the modelled CLI makes.

One attribution is worth naming as a type rather than an instance. **EA-DF-06
is the source, not an instance** — 74 project manifests declared units the
carrier already contains, which is what regenerated `plugins/skt` in 46 homes
after EA-DF-05 removed it. EA-DF-05 without EA-DF-06 would have been a sweep
that undid itself on the next `project resolve`.

## Block 3 — Improvement-card row

**No round run, and no score is claimed — for the second consecutive review.**

Stated plainly because it is the thing most likely to be misread at the end of
this epic: **`claude plugin eval` has never run on this branch.** 64 cases exist
in `evals/`; zero of them have a score against this code. SI-19 and SI-20 each
wrote cases and neither ran one, which was correct for their scope (manual
record first, cases second, spend unauthorised at the time) but means the eval
ladder has so far produced **cases, not measurements**.

The owner authorised spend on 2026-09-24. The first billed run is therefore both
the first measurement and the baseline, with nothing to compare against — a
limit SI-23 inherits and must state rather than paper over.

## Block 4 — Skill changes applied or declined

| proposal | disposition |
| --- | --- |
| `skt`: refuse to guess which epic when refs are ambiguous (`epic_slug_from_refs`) | **applied** (`3ff232bb`) |
| `skt`: join a ticket branch to its spec id through `github_issue` (`plan_issue_index`) | **applied** (`3ff232bb`) |
| `skt check`: stop calling an unmeasured surface current | **applied** (`3ff232bb`) — headline now reads `units current (…); ARTIFACTS NOT CHECKED (…)` |
| `skt ticket sweep`: refuse to plan removal without containment | **applied** (`2035c3cb`), repairing commit named in `b049337b` |
| `skt status`: detect the migration's **outcome** (`plugins/skt` on disk), not only its advice in manifest text | **applied** (`f212cbe3`) |
| `skill-manager/references/projects.md`: stop teaching `[plugins.skt]` as the example | **applied** — example is now the carrier |
| `skill-manager`'s leak oracle (SI-18-DF-01) | **still declined** — another repository's code; failed a third time with an identical signature, recorded on the row rather than re-derived |
| `skill-manager home close-out --json`: add a `clean` key (SI-20-DF-08) | **deferred** — separate unit, and it is the gate the epic agent runs at wave close |

## Block 5 — Model corrections owed by merged tickets

**None owed.** Neither SI-19 nor SI-20 edited `desired`. The model delta in
Block 1 is the epic agent's own work, filed against findings the tickets
reported — which is the division this epic asserts and, here, honoured.

---

## What these waves actually established

**The ladder's ordering constraint holds, and it is checkable rather than
asserted.** Both rungs put the manual record in a commit that is a strict
ancestor of the commit introducing their first eval case:

```
SI-19   8e362bbb (record)  ->  eefe3aa8 (case)
SI-20   70549f90 (record)  ->  7daa8e18 (case)
```

`git merge-base --is-ancestor` confirms each, and neither case commit modifies
the record. The claim "manual first" is therefore a property of the history, not
of a ticket agent's word — which matters because it is exactly the kind of claim
that is easy to assert and impossible to audit later.

**The manual record changed what the cases grade, twice.** SI-20 records this
against itself: its first case exists only because a two-arm by-hand
falsification showed the reds were about the fixture and not about skt, and its
second exists only because the operator was caught by the wrapper and had to
build a home to get the bytes under review under test. A manual stage that never
changes the cases downstream of it is ceremony; this one is not.

**Five graphs now pass together, against the code that is actually shipped.**
That sentence needed three corrections to become true, and the corrections are
the finding:

1. `b6608763` — sktSurface was testing **a different repository**, so its greens
   and its reds were both about the wrong bytes (SI-25-DF-06).
2. `a3761e30` — all five green for the first time this epic, at 09:25.
3. And then `f212cbe3` changed `skt/status.py` at 11:04, which **invalidated
   that record**. Re-run at `d4eb1abb`: sktSurface 5/5 nodes, 318/318
   assertions; sktHooks 3/3 nodes, 167/167 assertions; zero failures.

Point 3 is not a footnote. Both skt graphs are `OPT-IN`, so the default-set
command would have re-run three graphs, reported green, and said nothing about
the two that cover the code that changed.

## The recurrence this wave caught

**Three-rung resolution, again — but for the first time as a *population*
rather than an instance.**

Every prior instance of this defect class was one resolver looking in one place.
EA-DF-05 is the same error committed by the **install graph**: 46 homes carried
skt as its own plugin beside the carrier that already contains it, so any
single-rung resolver picked whichever it found first — which is how sktSurface
came to test a different repository in the first place.

The count matters more than the mechanism. This class has now been repaired in
`plugin-repo-lib.sh`, in the checkers, in skill-manager's imports, in the
manifests, and now in 46 homes. **A defect repaired five times in one epic is
not five bugs; it is one missing abstraction.** Nothing in the substrate makes
three-rung resolution the only way to spell the question — `unit_dir` exists in
one shell library and is copied nowhere else because nothing requires it.

That is the strongest candidate finding this epic has produced for the *next*
one, and it is recorded here rather than acted on, because acting on it now
would be an unscoped rewrite two tickets from the end.

## What I got wrong in these waves

1. **My "ten known failures" baseline was wrong; there were eleven.** The
   eleventh was caused by my own assertion in `2e01a950`. SI-19's agent caught
   it (SI-19-DF-04) and I falsified it both ways before accepting. A baseline I
   produced, used to judge a ticket agent's work, and got wrong.

2. **My first skt survey missed `plugins/skt` entirely.** I probed
   `skills/skt` and `plugins/*/skills/skt`, and reported "no standalone skt
   anywhere" while 46 homes carried it. The two-rung survey, from the epic agent
   who has been filing three-rung findings against everyone else.

3. **The manifest sweep edited the carrier's own repository**, making
   `tla-spec-dev` declare `[plugins.tla-spec-dev]` pointing at itself. Reverted
   before commit. The rule "a manifest must not declare what the carrier
   contains" is exactly backwards for the carrier, and I had not stated the
   exception before running the sweep.

4. **I corrupted the ledger three times with unquoted heredocs**, executing
   backticks and `$()` into the record; once it injected live `skt status`
   output. Its own advisory reader (`improvement_ledger.py`) caught structural
   damage twice — `0c162dfe` records this. The fix is procedural and I am
   writing it down so it survives this session: **the ledger is edited through a
   file, never through a heredoc.**

5. **I reported a clean suite from a bare `pytest`** that had produced 401
   collection errors and `0 FAILED`. The canonical command is at `README.md:168`
   and takes a `tests` scope plus three `--with` packages.

## Verified, not accepted

Every ticket claim below was re-measured by the epic agent, not read:

- SI-19's five and SI-20's eight findings — each reproduced or downgraded.
  SI-20-DF-02 and EA-DF-02 were downgraded to **not-a-defect** after
  reproduction, EA-DF-02 specifically because the graph was finally testing the
  right code.
- SI-19-DF-03 was **half** decided. Its UNDECIDED half (sktSurface/sktHooks
  listed but not run) is now green. Its stale-table half **stands** and is the
  part worth keeping: nothing consumes SI-13's committed `classification.md`
  programmatically — zero program references, the only hit a string in the
  ledger row — while `discover.py` enumerates five graphs at run time.
- The skill-manager plugin-dependent sweep: **7 of 8 passed.** Stated with its
  limit, because the limit is what it is worth: **both skill-manager homes carry
  a plugin copy predating the skt fixes.** It is a real no-regression result for
  skill-manager against the plugin it has; it is **not** evidence about the
  fixes, and reading it as such would repeat the mistake sktSurface was making
  the same morning.
- The manifest sweep: 82 manifests scanned, 0 invalid TOML, 74 declaring the
  carrier, 0 vendored old rungs, 1 still naming contained units (the carrier's
  own, deliberately).

## Ledger state at wave close

140 rows. 62 `still-true` (validated, deliberately carried), 33 `fixed`, 19
`carried`, 11 `ticketed`. **Two open**: SI-20-DF-03 (the "no home at all"
refusal is unreachable without a home fixture) and SI-20-DF-08.

Nothing is pending triage.

## Suite and graphs at wave close, re-measured

Both re-run at `d4eb1abb` by the epic agent, after the review was drafted, so
this section reports measurement rather than expectation.

**Repository suite**: `10 failed, 1853 passed, 6 skipped in 1450.89s`, via the
canonical command at `README.md:168`. Compared by **NAME** against SI-20's
recorded ten (`tickets/SI-20/final-failure-names.txt`): **identical sets, zero
diff**. Names, not counts, because the count matched at wave 17 while the
membership did not — that is how SI-19-DF-04 was found. Evidence:
`suite-failure-names.txt`, `suite-verdict.txt`.

**Graphs**: all five PASSED, `mode=full`, 20 nodes and **608/608 assertions**,
zero missing/duplicate/unexpected ids. sktSurface went 4/5 ERRORED → 5/5 with
318/318. Recorded in `manual/graph-verdicts.txt`, which this session rewrote:
it still carried the 2026-09-21 verdict where sktSurface was red, because the
intervening green result was written into a commit message and nowhere else.

**The trap that record was hiding.** sktSurface and sktHooks are `OPT-IN`. The
bare runner runs three graphs, prints PASSED three times, and reports the other
two as NOT RUN. The two it skips cover skt — the surface changed five times on
2026-09-24. A green default-set run is not evidence that skt is green, and this
epic has now made that mistake twice.

## Where the bugs probably are

- **The 74 manifest edits are uncommitted in 74 other repositories.** They are
  correct and validated, and they are working-tree changes their owners have not
  seen. Nothing in this epic can commit them, and nothing tracks them.
- **The eval harness has never run here.** Every scaffolding failure it can
  have — view staging, the toolchain pin, `--allow-tools` derivation — is
  unmeasured. `harness/w-harness-smoke` exists precisely to find them first, and
  it has not run either.
- **SI-21's known-weak target.** `run spec-unit-tests --ticket` resolves two
  targets, executes one, lists both (SIS-KICKOFF-F-04). The ticket says to
  encode observed behaviour, not documented — the standing temptation is the
  other way round.
- **The scorecard has no eval case**, and it is the instrument this epic uses to
  decide its own goals. Filed at wave 4, still open, and SI-21 names it.

## Suggested next steps

1. SI-21 — third rung. Manual record of the CLI's seven verbs **before** any
   case, as rungs 1 and 2 did and as the history can be made to prove.
2. The staggered eval ladder, smoke case first.
3. SI-22 — fourth rung, the fresh-home bootstrap chain.
4. SI-23 — Evaluation B, which must state that its measurements have no prior
   run to compare against.
