# Waves 19–22 review — epic/self-improvement-substrate

**Written 2026-09-26 at epic tip `b909fd90`.** Covers wave 19 (SI-21), wave 20
(SI-22), wave 21 (SI-28) and wave 22 (SI-29) — the eval ladder's top two rungs
and the two tickets the owner inserted ahead of the evaluation.

**Every implementation ticket in the epic is now delivered.** Only SI-23, the
terminal evaluation, remains.

**This artifact exists because a checker started working.** `#386` / `EA-DF-07`:
`WAVE_DIR` matched `wave-16` and not `wave-11-12`, so the wave-artifact check
had been silently skipping every combined-wave directory. Fixed at `968123a1`,
and the plan-driven half it gained immediately reported waves 19–23 as covered
by nothing — true, and invisible until then. **The fix's first act was to find a
gap in my own work.** Three waves had closed without a review artifact and no
instrument said so.

---

## Block 1 — Model delta applied

**None applied, and that is a gap I own rather than a property of the waves.**

Measured: `git diff ac5f7491..b909fd90 -- specs/` touches nothing outside
`specs/results/` except `ticket_plan.yaml`, which is mine. No `.tla` file
changed across four waves.

That would be unremarkable if the findings had nowhere to point. They do:

| bin | rows filed in these waves |
| --- | --- |
| `UNMODELED/install-pipeline` | **5** (SI-22-DF-01, 03, 04, 05, 06) |
| `UNMODELED/eval-harness` | 2 |
| `UNMODELED/record-keeping` | 3 |
| `UNMODELED/bootstrap-preconditions` | 2 |
| `UNMODELED/progressive-disclosure` | 1 (new bin) |
| `RunSpecUnitTests`, `RunEffectConformance` | 1 each |

**Wave 17–18 established the rule and these waves did not follow it.** There,
four SI-20 findings had nowhere to attribute, so the epic agent added the skt
surface to all three spec trees and four safety invariants, retiring four
`UNMODELED/` attributions — recorded as *"a finding does not become a change by
being filed, it becomes a change when the substrate **checks** something it did
not check before."*

Here, **five findings cluster in `install-pipeline`** and no invariant was added.
The honest reading is not that the install pipeline resists modelling; it is that
I did not attempt it. `SI-22-DF-01` alone — a successful install exiting 11 —
is exactly the shape of claim an invariant exists for: the pipeline asserts
success on every substantive line and then reports failure.

**Carried to SI-23 as evidence against `GOAL-epic-owns-the-model`, not for it.**
The goal's claim is that at every wave close the epic agent applied the delta.
For these four waves the delta was empty while the findings that would have
driven it were being filed. That belongs in the verdict.

## Block 2 — Anchors placed

**Two placed by tickets, seven placed by me at wave close, one new bin opened.**

`SI-21-DF-02` → `RunSpecUnitTests` and `SI-21-DF-03` → `RunEffectConformance`
are the only two rows in these waves that anchor to a modelled action. Both are
claims the modelled CLI makes about its own execution, which is the right test.

**Seven rows arrived with no attribution at all, and the cause was mine.** The
work orders for SI-28 and SI-29 — both written by me — omitted the *"Attribute
before close: name the TLA+ action each defect happened inside, or
`UNMODELED/<bin>`"* instruction that #370 and #371 both carried. The two agents
did not skip a step; they were never given it. I attributed all seven at wave
close and said so on each row in an `attribution_note`, so the record shows who
did it and when rather than reading as though the tickets had.

`UNMODELED/progressive-disclosure` is a **new bin**, opened for `SI-29-DF-05`:
nothing makes the description reduction hold, and SI-09's regression — 594 words
cut, grown back to 1005 by nesting — has no checker. A bin is the honest place
for it precisely because no modelled action covers a card budget.

## Block 3 — Improvement-card row

**No card round, no score claimed — and for the first time in this epic that is
not because nothing has been measured.**

The previous two reviews had to state that `claude plugin eval` had never run on
this branch. That is no longer true, and the numbers are now the epic's most
load-bearing evidence:

| measurement | value | limit on reading it |
| --- | --- | --- |
| corpus, 2026-09-25 (`ac5f7491`) | **52 of 58 decidable at 1.00**, mean 0.959 | `runs: 1` — every score a single sample |
| SI-29's five role cases | 1.00, 1.00, 0.94, 1.00, 0.94 at `--runs 6` | two known one-in-six bad runs, **not** recalibrated away |
| SI-22's `w-sm-fresh-install` | 0.97 and 0.94 over two six-run samples | per-run spread 0.83–1.00 in **both** |

**`--runs 6` does not pin a score.** Measured twice on unchanged cases at one
commit: 0.89→0.81 and 0.97→0.94. Rule 5 of `HARDENING-BATCH.md` — "use
`--runs 6`" — is too optimistic as written, and SI-23 must state the limit in
every verdict it draws from a mean rather than inheriting the rule.

**No improvement-card row is written because no card round was run.** Saying so
plainly for the fourth review running: the card is the instrument this epic uses
to decide its own goals, and **the eval lane still has no case covering the
scorecard**. SI-21 narrowed that gap — its new case covers the tool *starting* —
and restated it as still open rather than letting it disappear, which was the
plan's acceptance.

## Block 4 — Skill changes applied or declined

| proposal | disposition |
| --- | --- |
| `spec-double-2`: the `w-sdc-ticket-binding-bare-adapter-module` case description claims the fixture carries what the scaffold writes — false since 2026-09-05 | **applied** (SI-21) — restated in place, wrong version left visible |
| `tla-spec-dev`: declare the required skill-manager version; `skt check` names a stale CLI | **applied** (`dc8ed6d2`, SI-28) — `bootstrap-floor.toml`, one place |
| `skt`: a cache of the wrong schema is not a cache | **applied** (SI-28 review round) — and it exposed a hardcoded `"schema": 2` in a test-graph fixture that errored both skt graphs |
| `test-graph`: read `SCHEMA_VERSION` from the source under test, never a literal | **applied** (SI-28) |
| four roles get reading paths and propagation destinations | **applied** (`0f7157b4`, SI-29) — three new inboxes |
| `unit-authoring`: a description keeps its activation clause; new prose goes to the reference | **applied** (SI-29) |
| `tla-spec-dev`: name an unparseable `case.yaml` before billing | **applied** (`59370837`, epic agent) — then **corrected** at `57f05cf4` |
| `skill-manager`: `install --dry-run` should parse the unit manifest (`SI-28-DF-01`) | **deferred** — separate repository |
| `skill-manager`: a plugin manifest should have a required-CLI-version field (`SI-28-DF-02`) | **deferred** — separate repository; `bootstrap-floor.toml` is the local workaround |
| `applied(x)`'s slot should be constrained (`SI-29-DF-01`, `DF-02`) | **applied as documentation** (`11000fa6`) — shape, deliberately not resolvability |
| nothing makes 592 hold (`SI-29-DF-05`) | **proposed, open** — carried to SI-23 |

**One release, authorised by the owner against a standing rule.** skill-manager
`v0.28.2` was cut from that repository's epic branch merged to `main` (PR #398,
22 commits, rebase-merged), because the fixture-skip fix had existed since
2026-09-23 and had never shipped. The owner overrode the "never `main`" rule
explicitly after being shown that the merge carries 15 source files and removes
159,734 lines of vendored skills. The release notes were rewritten by hand:
release-please had listed **one** bug fix for a release that changes behaviour
for anyone syncing.

## Block 5 — Model corrections owed by merged tickets

**None owed.** No ticket in waves 19–22 edited `desired`; verified above by diff.
SI-29 edited one file outside its declared conflict keys —
`tests/test_new_ticket_workflow.py` — and that is a test, not the model. It
relocated assertions byte-for-byte with the prose they cover, on the `RP-05`
precedent in that same file, and flagged it rather than doing it silently.

The division this epic asserts — tickets move `current`, the epic agent owns the
model — was honoured by every ticket. **It was the epic agent who did not hold up
the other half of it** (Block 1).

---

## What these waves actually established

**The eval ladder is complete and provable.** Five rungs, each with a manual
record committed before its first case, and the ordering is checkable in git
rather than claimed:

```
8e362bbb → eefe3aa8    SI-19
70549f90 → 7daa8e18    SI-20
bec1934b → c96de147    SI-21
679f76f1 → 3dc106fb    SI-22
f8a3994e → b929e07c    SI-29
```

`merge-base --is-ancestor` rc=0 for all five, and no record commit contains a
`case.yaml`. `GOAL-evals-earned`'s deciding check passes on every rung.

**`GOAL-one-plugin` is half MET and cannot be closed.** No standalone `skt` in
root, project or worktree home, and `skt` contained in all three — SI-08's NOT
MET half is now MET, re-verified independently. But `tla-spec-dev-plugin` is
**private**, so a genuinely fresh machine cannot clone it: the bootstrap walk
demonstrates *fresh home, operator's credential*, not *a machine with nothing*.
Three units install, not one. Both figures reported rather than the flattering
one.

**Progressive disclosure per agent type was a negative result before it was a
positive one.** SI-22 measured that nothing branched on agent type: zero role
conditionals in either shipped hook, `role:` read by the plan validator and never
by anything an agent sees, 31,063 cache entries delivering 11 skills identically
to everyone. SI-29 then built the routing — references only, no detection code —
and both clauses now pass.

## The recurrence these waves caught

**The metric was hit at the product's expense, and only an unrequired
measurement caught it.** SI-29's first pass reached **588** description words
against a 600 target — a better number than the 592 that shipped. It got there
by deleting activation vocabulary: three units lost their `use when` clause and
`skill-manager` had none at all, its description saying what the skill *is* and
never when to invoke it, while `skt` lost five trigger phrases covering sweep,
retire and disk-reclaim.

The goal as written would have scored 588 as the cleaner pass. Nothing in it
required the words to do anything. **SI-23 must read
`GOAL-progressive-disclosure` knowing that its target, optimised correctly,
degrades the product** — and that the agent flagged activation as its largest
unmeasured risk before anyone asked.

**A finding was filed, read by a later agent, and then re-committed by its
reader.** `SI-21-DF-01` recorded that `python3` is a zsh alias and that six of
SI-21's own measurements silently ran under an unintended interpreter. SI-29 read
that row while working this ticket, then made the same mistake in the opposite
direction — measuring in zsh and attributing the result to a bash script — and
filed it as `SI-29-DF-03` at high severity. **I repeated the claim to the owner
before checking it.** The earlier finding's own stated remedy, *print
`sys.executable`*, would have caught both of us.

That is the sharpest evidence this epic has about its own thesis, and it cuts
both ways: the substrate did record the lesson, and recording it was not enough
to stop its recurrence two waves later.

## What I got wrong in these waves

1. **Three consecutive work orders carried an error the ticket agent found.**
   SI-21's quoted a suite baseline for the wrong command (1852 full-suite against
   an assignment naming `--ignore`), and sent findings to the wrong backlog.
   SI-28's specified "warns and exits 0" when exit 10 is skt's pre-existing
   notify code and a literal 0 would have built a warning that can never reach an
   agent. SI-29's carried a funnel figure that was off by one row, twice.
2. **I merged a case that had been unloadable for a whole wave.** SI-21's final
   commit cost `w-sdc-spec-unit-ticket-runs-only-the-first-target` its indent;
   I verified that merge four ways and none of them touched whether a shipped
   case file parses.
3. **I closed #389 on three falsification arms that all ran the wrong
   interpreter** — `uv run --with pyyaml`, never the way `run.sh` invokes it.
   Verifying the step instead of the outcome, which is the rule I put in every
   work order.
4. **I told the owner my own checker had shipped inert, before checking.** It had
   not; `run.sh` resolves `/usr/bin/python3`, which has PyYAML.
5. **Two work orders dropped the attribution instruction** (Block 2), so seven
   rows arrived unattributed.
6. **No model delta across four waves** while five findings piled into one
   unmodelled bin (Block 1).

## Verified, not accepted

Every ticket report in these waves was checked against the repository. What that
found, in order of consequence:

- **the errors were mostly mine.** Three of four tickets corrected their work
  order, and every correction held under independent measurement.
- **one agent's high-severity finding was false** (`SI-29-DF-03`) and was
  downgraded after *it* reproduced both shells, not after I insisted.
- **one mutation test**: deleting SI-28's schema comparison fails its test while
  the neighbouring test still passes, so the guard discriminates.
- **one vacuous check of my own, caught before reporting**: my activation audit
  flagged `git-integration-repo` as having no activation clause because my regex
  omitted `use to`.

## Ledger state at wave close

151 rows in `deferred_findings_final.yaml`; 20 rows filed in these waves across
four per-ticket inboxes, **all 20 now attributed**. The funnel, strictly parsed:

```
151 filed → 71 carry a parseable skill_change (47%) → 40 proposed → 10 applied
 79 carry no skill_change field · 12 none · 9 declined · 1 malformed
```

**10 of 151 = 7% of findings became a change to the substrate**, and only three
of those ten name a commit a reader can verify later. The funnel narrows hardest
at `proposed → applied`, which is the **epic agent's** step — and
`EPIC-AGENT.yaml` held zero rows until SI-29 gave it a documented use.

## Suite and graphs at wave close, re-measured

```
repository suite   10 failed / 1742 passed / 6 skipped   (--ignore=tests/test_score_tools.py)
                   failure NAMES identical to the epic baseline, all 10
sktSurface         318/318   sktHooks  167/167   (opt-in; named explicitly)
specWorkflow 74 · cliWorkflow 41 · effectProviderExamples 8
descriptions       592 (target ≤600)   bodies over 1500: 0 of 11
case files         75 parse, 0 unloadable
disk               47 GiB free
```

**Quote the command beside every count.** The same suite without `--ignore` is
1853 passed and the same ten names; handing a ticket agent one number for the
other command is how SI-21 was given a baseline it could not reconcile.

## Where the bugs probably are

1. **The description budget has 8 words of headroom** and nothing enforces it.
   `git-epic-workflow` sits at 44 and `git-issue-workflow` at 55 after
   redistribution, but the *total* is 592 of 600. The next nested unit breaks the
   goal, exactly as nesting broke SI-09's 594.
2. **`install-pipeline` has five findings and no model.** Whatever is wrong there
   is invisible to every check this repository runs.
3. **Skill activation is measured only by construction.** Eleven units carry
   activation vocabulary because I counted the clauses; no case exercises whether
   a role's skill actually triggers from a cold prompt.
4. **Three of ten `applied(x)` values name a commit.** The rest cite "this PR"
   or a path, so the loop's own record decays as soon as the PR merges.

## Suggested next steps

1. **SI-23**, with three limits stated rather than inherited: `runs: 1` and the
   `--runs 6` spread; `GOAL-one-plugin`'s bootstrap half unavailable while the
   repo is private; and `GOAL-progressive-disclosure`'s target being satisfiable
   by degrading the product.
2. **The `install-pipeline` model delta** this wave owed and did not pay.
3. **A scorecard case**, still open since wave 4.
