# Milestone 2 review — epic/bug-sweep (#199), waves 4–5

Range `be88e882..2f3e85c4` plus BS-23. Five tickets merged, zero conflicts, promotion order held.
Trigger: skill-manager 0.29.0 handoff (registry server removed, five tool defects, two red graphs).
Review policy: milestone, **gate**. No evaluation ticket is dispatched until the owner answers.
Tool versions: skill-manager 0.29.0 (48a07c1d) in brew, project and epic homes, and in the eval pin.

## 1. Hot spots

| File | Ticket | Why it matters |
|---|---|---|
| `skills/skt/src/skt/sweep.py` (+188) | BS-25 | decides which worktrees are destroyed; now accepts content as proof of landing |
| `.../testgraphsdk/tasks/RunReportWriter.kt` | BS-26 | closure format version 4; every graph's resume goes through it |
| `skills/skt/src/skt/check.py` | BS-25 | runs at every session start |
| `skills/unit-authoring/**`, `skills/skill-manager/**` | BS-23 | 26 files of text; agents read these to decide how to install |

## 2. Decisions made implicitly

| Decision | By | Default it set | Cite |
|---|---|---|---|
| "Landed" = every changed path byte-identical in target, or one target commit has the identical diff | BS-25 | no use of `gh` or branch names | #232 |
| A proven landing also clears the "not pushed" blocker, only if the landing commits are on a remote | BS-25 | not requested; without it delete-branch-on-merge blocks every squashed ticket | #232 |
| A plan deleted from the epic tip is read from epic history | BS-25 | history declares; a miss falls to the no-plan rule | #232 |
| A deleted epic branch still refuses `--epic` and points at `--target origin/main` | BS-25 | not auto-resolved | #232 |
| jbang budget miss reports `slow-launcher` rather than raising the 5 s budget | BS-25 | session start stays cheap | #232 |
| Closure v4 records `continueAfterFailure`; older closures stay strict | BS-26 | replay never reads the env var | #231 |
| Import validator documented as `skill-manager unit validate` | owner, BS-23 | shipped in 0.29.0 | #223 |
| BS-23..27 are guards on goals; GOAL-BS-BUGS stays 37/37 | epic agent | the five new issues do not change the agreed target | plan rev 3 |

## 3. Where the bugs probably are

- **`landed_by_content` route 1** treats "path identical in target" as landed, even if a different commit put it there. Nothing is lost when that happens, but the ticket's own commits were not what landed.
- **jbang detection** is a text search, comments included, so a hung CLI whose script mentions jbang is mislabelled. A real cold start over 5 s was never measured; warm launches took 1.2–1.7 s.
- **Doc-smoke and onboarding** were proven by running the two nodes against the branch in the installed layout. The full graphs read the installed skill and stay red until this reaches a home.
- **Closure write failure** now logs an error, but that log line has no unit test.

## 4. What the epic agent applied, and what it still owes

Applied directly: nothing to skills or code. Plan revisions 2 and 3; home close-out for BS-23..27; this review and the attribution rows.

#### Model delta applied
None. BS-23..27 are no-op model results; no `.tla`/`.cfg` changed.

#### Anchors placed
None. The five findings anchor to units.

#### Improvement-card row
| Epic | Tickets | Issues addressed | Red→green proven | Findings filed | Conflicts | Lane deviations |
|---|---|---|---|---|---|---|
| bug-sweep M2 | 5 | 5 (#222, #224–#227) | BS-25/26/27 red on base → green on branch; BS-23 by grep, BS-24 by materialised self-report | 1 new (BS-26-D1) + 5 catch rows (BS-HP-01..05) | 0 | 0 |

#### Skill changes applied or declined
Applied by tickets: BS-23 (registry text), BS-25 (`worktree-sweep.md`), BS-27 (`skill-manager/SKILL.md`, `provision.md`). Declined: none.

#### Model corrections owed by merged tickets
None new. Still owed at finalization: the no-op spec closes (now 24) and BS-08's `specs/current` promotion.

## 5. Suggested next steps

**Graphs on 2f3e85c4 (`sanity/`, load average 21–30 on 10 cores):** sktSurface, sktHooks, cliWorkflow, effectProviderExamples, specWorkflow all **PASSED**, 5/5. `failure_cleanup_probe` passed and `spec.reference.adapters_resolve` ran and passed, for the first time this epic (BS-07-DF-05's symptom did not recur). skt unit suite: 455 passed, 3 skipped.

**Goal trajectory (local signals; the evaluation tickets decide):**
| Goal | Baseline | Local signal now | Target | Outlook |
|---|---|---|---|---|
| GOAL-BS-BUGS | 0/37 | red→green per ticket | 37/37 | BS-16 decides |
| GOAL-BS-SUITE | 9 failed | last full run (before waves 4–5): 1 failed, the deliberately red test | 0 | will miss by 1, owner chose to keep it red |
| GOAL-BS-GRAPHS | 5/5 | 5/5 on the tip | 5/5 | met locally |
| GOAL-BS-EVALS | unmeasured | — | 0 regressions | BS-17, about $66 |
| GOAL-BS-MANUAL | unmeasured | — | owner accepts | BS-18 |

**Evaluation:** on the owner's answer, dispatch BS-16, then BS-17 (base 68922587 vs tip, pinned to skill-manager 0.29.0), then BS-18. Runs that sync then launch need `skill-manager home drift --ack --home=<home>`.

**Deferred findings:** 50 in the ledger plus 5 catch rows. New: BS-26-D1, a stale `ATTEMPT_CLOSURE_VERSION = 2` assertion. Keep batched.

**Standing worktrees:** 24 tickets plus the epic; 111 GiB free. BS-25's sweep can now retire the squash-merged ones at finalization.
