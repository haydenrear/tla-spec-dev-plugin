# Milestone review — waves 4–5 (ESD-04, ESD-05)

Epic `evidence-sized-delivery` (#234). Range: `847aa4a9` (wave-3 review) → `cc8e4f99` (ESD-05 merge),
plus the epic-agent commit recorded below. Policy: `review_policy.cadence: milestone`, `gate: false`,
`walkthrough: on-request` (owner: final review only). Files: `diff.stat`, `diff.patch` (excludes
`specs/.history`), `merges.md`. Carry-forward from `../wave-3/review.md` is noted where it applies.

## 1. Hot spots

| # | Location | Why hot | Question for the reviewer |
| --- | --- | --- | --- |
| 1 | `skills/git-epic-workflow/references/step-sizing.md` §6 (+301, new) | The bounded update rule (halve on any override; increase only after two consecutive clean review points, by ≤ one step ≈ +50% of items; one instrument red never moves the batch) is the agent's judgement, **not fitted to data** | Keep the numbers as defaults, or make them qualitative? |
| 2 | `step-sizing.md` §2 scope-item unit (behaviour × boundary, +1 per interacting pair) | Becomes the unit every future capacity estimate and the new delivery line counts | Is "+1 per interacting pair" too coarse for coupled waves? |
| 3 | `skills/spec-double-2/references/agent_roles.md` § Evidence routing (+28) | The one table every role now reaches; rows link canonical sources by bare file name across skills | Can a reader in spec-double-2 resolve `step-sizing.md` / `finalize.md` without the skill name? |
| 4 | `skills/git-epic-workflow/references/epic-ticket.md` assignment bullets (+20/−1) | Prose every future rendered assignment carries (*Evidence slice*, delivery line); not read by `validate_assignment.py` | An empty Evidence slice is silent by design (no-gate mandate) — acceptable? |
| 5 | `human-review.md` §3.5 *Delivery velocity and step size*; `finalize.md` §2c *Next epic's starting estimate* | Closes the loop across epics through the epic PR body, not a new file | Will the next epic's planner actually find the previous epic PR? |
| 6 | `test_graph/sources/spec_workflow_cleanup.py:29-32` (carried from wave 3, ESD-03-DF-01, major) | Still unfixed and out of this epic's scope | Owner decision pending (see §5) |

No file was written by two tickets (serial waves). ESD-04 kept strictly to §3a/§4b of `plan-and-schedule.md`; ESD-05 edited outside them (§3, §7) — keys held.

## 2. Decisions made implicitly, and guardrails overridden

**Implicit decisions**

| Decision | Where | Alternative not taken | Cost to reverse later |
| --- | --- | --- | --- |
| Separate page `step-sizing.md` instead of growing `validation-review.md` to ~400 lines | ESD-04 | inline | Low |
| Capacity decisions recorded only in existing controls (`validation_acceleration_rule` prose, `review_policy`, waves, validation matrix, `eval_budget`) | `step-sizing.md` §5 | a new plan key | Medium — a key would need validator support |
| `eval_budget` named as an existing control although `validate_epic_plan.py` does not read it | `step-sizing.md` §5 | — | Low; it is plan prose-data |
| One **delivery line** (`started_at; agent; scope items`) at the top of `## Review input`, instead of a new PR section | ESD-05, `epic-ticket.md` §7, `complete.md` | new section / new fields | Low |
| Next-epic starting estimate lives in the epic PR body | `finalize.md` §2c, §5 | a new results file | Low |
| Extra `validation-review.md` reference-map row in `git-epic-workflow/SKILL.md` | ESD-05 | — | None |
| Epic agent added the delivery line to the duplicate PR-body contract in `git-issue-workflow/references/epic-ticket.md` §7 (ESD-05-DF-01) rather than replacing that list with a pointer | epic commit after `cc8e4f99` | pointer-only (−40 lines on the ticket path) | Low |

**Guardrail overrides**

| Override | How checked | Result |
| --- | --- | --- |
| `--allow-open` / `--accept-new` / `--no-promote-current` / forced close | `grep -rn 'allow.open\|accept.new' specs/.history/evidence-sized-delivery/*/manifest.json` (non-false values) | none |
| skipped/xfailed tests | `git diff 847aa4a9..cc8e4f99 -- '*test*'` | no test changed |
| REQUIRED matrix entry downgraded | assignment vs plan | none |
| TLA/cfg change | `git diff 847aa4a9..cc8e4f99 -- '*.tla' '*.cfg' ':(exclude)specs/.history'` | none |
| close-out over a non-custody blocker | PR verdicts | none; both clean |
| inline out-of-scope fix | ledger `fixed-inline` | none; ESD-05 fixed four routed rows inside its own keys (ESD-01-DF-01, ESD-04-DF-01..03) as assigned |
| deferral budget | rows per ticket | ESD-04 3/5, ESD-05 2/5 |
| goal target edited after dispatch | `git log -p 847aa4a9..HEAD -- specs/desired_program_model/ticket_plan.yaml` over `epic_goals` | none |

**Product-contract conformance** (#234 design contract)

| Core element | State after wave 5 | Evidence | Scheduled where, if not yet |
| --- | --- | --- | --- |
| No new scripts / controller / runner / CLI / validator / gate | holds | `git diff --name-status 9635bad2..cc8e4f99 --diff-filter=A -- '*.py' '*.sh' ':(exclude)specs/.history'` → none | — |
| Origin separate from detection channel; false reds/greens; unknown attribution | implemented | `bug_attribution.md` §4.3, §6a, §7e | — |
| Provisional safe step from the tighter of review/verification capacity, adjusted for coupling, history, coverage, model identity, evidence reliability | implemented | `step-sizing.md` §1–§3 | — |
| Total cost of candidate batches incl. fixed eval/setup and expected rework; separate cadences | implemented | `step-sizing.md` §4 | — |
| Cautious increase / reduction on escapes, recurring faults, unstable oracles, changed models; unknown ≠ zero risk | implemented | `step-sizing.md` §6, §7 | — |
| Regression only as optional analysis with caveats | implemented | `step-sizing.md` §7 | — |
| Final integrated confirmation and manual acceptance kept; evidence reuse invalidation | implemented | `step-sizing.md` §8; `finalize.md` unchanged sequence | — |
| Guidance names actual graph nodes | implemented | `graph-architecture-review.md` worked review | — |
| Short entry points route to bounded evidence; no growing mandatory reading pack | implemented, measured | `agent_roles.md` § Evidence routing; ESD-05 reading burden +3.2% to +6.3% per role path (upper bound) | ESD-06 measures actual reading |
| Instruction uptake measured | absent | — | ESD-06 (#240) |

## 3. Where the bugs probably are

| Location | Why suspicious | Cheapest settling experiment |
| --- | --- | --- |
| `step-sizing.md` §6 thresholds | Judgement, not fitted; a single replay (R1–R4) is not blind | ESD-06 blind replay on held-out episodes (polymarket E02, effectful-learning epic-10, MH finalization, CDC #234) |
| ESD-05 reading-burden table | Role→file mapping is the author's reading of `agent_roles.md`; a real agent may read more (suspicion) | ESD-06: count lines actually opened in eval transcripts |
| ESD-05 finding walk-through (all 5 roles reached ESD-03-DF-01 in ≤ 3 links) | Self-applied → biased toward "reached" | ESD-06 uptake case with no answer in the prompt |
| Bare cross-skill file names in the `agent_roles.md` routing table | May not resolve from spec-double-2 | Open the table as a spec-double-2 reader and follow each link |
| ESD-04 replay "known then" columns R2–R4 | Drawn from ESD-01 summaries, not decision-time records | Re-open the primary record for one of them |

## 4. What the epic agent applied, and what it still owes

**Model delta applied.** None to `desired_program_model`, `current` or `program_model`. No-op spec closes: `specs/.history/evidence-sized-delivery/ticket-003-ESD-04`, `ticket-004-ESD-05`; TLC MCsmall green before/after, complexity delta zero. No `UNMODELED/<bin>` reached `MODELABLE`.

**Anchors placed** (ledger rows carry `area` only; anchors placed here):

| Finding | Anchor |
| --- | --- |
| ESD-04-DF-01 (no reviewer/verifier model identity in records) | `UNMODELED/workflow-records` — fixed by ESD-05 |
| ESD-04-DF-02 (SKILL.md missing `step-sizing.md` row) | `UNMODELED/skill-instructions` — fixed by ESD-05 |
| ESD-04-DF-03 (no per-batch scope-item count) | `UNMODELED/workflow-records` — fixed by ESD-05 |
| ESD-05-DF-01 (PR-body contract written twice) | `UNMODELED/skill-instructions` — fixed by the epic agent |
| ESD-05-DF-02 (eval home from the installed plugin measures main in both arms) | `UNMODELED/eval-harness` — handed to ESD-06's assignment brief |

Count moved into program-model anchors: 0.

**Improvement-card row.** Waves 4–5: 2 tickets delivered, 0 reopened, 0 conflicts, 0 overrides; 5 findings filed, 4 fixed in-epic (routed), 1 handed to ESD-06. Cumulative waves 1–5: 14 findings, 6 fixed in-epic, 1 major pending owner decision.

**Skill changes applied or declined.**

| From | Unit | What was hit | Disposition |
| --- | --- | --- | --- |
| PR #258 | — | none met | — |
| PR #259 | `tla-spec-dev/git-issue-workflow` | `epic-ticket.md` §7 duplicates the PR-body contract and lacked the delivery line | applied(epic commit after `cc8e4f99`: delivery line + checklist item; ESD-05-DF-01 `disposition: fixed`). Pointer-only consolidation declined(this epic avoids removing prose a later reader may rely on; recorded as a recommendation) |

**Model corrections owed by merged tickets.** None (no ticket edited `specs/tickets/<id>/desired`). Carried rows from wave 3: none.

**Recommendations that remain.**

| Observed | Shape | Door | Owner | Cost |
| --- | --- | --- | --- | --- |
| PR-body contract stated in two skills (ESD-05-DF-01) | one canonical list, pointer in the other | new issue | plugin maintainer | low |
| No-op closes snapshot ≈16 k lines each (wave 3) | reference unchanged snapshots by digest | new issue | spec-double-2 maintainer | medium |
| The CLI's plan parser refuses YAML anchors | document "no anchors" or accept them | new issue | spec-double-2 maintainer | low |
| ESD-03-DF-01 data-loss risk | guard `repoPath` absent → refuse | new bug issue (owner decision) | owner | low |

### Delivery velocity and step size (human-review §3.5, as ESD-05 defines it)

`started_at` for this epic: plan commit `9635bad2` at 2026-11-10T12:58Z. Merges: #255 13:31Z, #256 13:45Z, #257 14:01Z, #258 14:16Z, #259 14:32Z — five serial tickets in 1 h 34 m elapsed, each PR merged within 45 s of opening (no human wait, `gate: false`). Validation per ticket ≈ 1 min (doc-contract ≈ 44 s, spec-unit ≈ 20 s, TLC ≈ 2 s) plus the epic close (≈ 30 s); agent work dominates (≈ 9–28 min per ticket). Review capacity was not the binding constraint (serial prose, no conflicts); verification capacity for prose is the ESD-06 eval, which this epic amortizes once. Decision: **hold** — run ESD-06 as the single predeclared integrated checkpoint; no batch change. Falsifier: ESD-06 finds a regression or an uptake miss that a per-ticket check would have caught.

## 5. Suggested next steps

**Ready next:** #240 ESD-06 (all five dependencies merged) — owns all four goals; budget ≤ 48 billed case-runs / $40; eval home built and `setup-eval-home.sh --check` all green (offline wheels added by the epic agent before dispatch). Brief must carry ESD-05-DF-02: the base arm runs from a `main` checkout (`a1ff56cf`) and the tip arm from the epic tip, because `evals/run.sh` stages the checkout it runs from.

**Deferred findings (pending only)**

| ID | Found by | Severity | Summary | Blast radius | Disposition (recommended) |
| --- | --- | --- | --- | --- | --- |
| ESD-03-DF-01 | ESD-03 | major | `spec.workflow.cleanup` rmtree of `Path("")` | deletes `test_graph/` | promote to a bug issue outside this epic — owner decision pending |
| ESD-03-DF-02..05 | ESD-03 | minor/trivial | probe node shape; nested 900 s timeout; root-home fallback; evidence in checkout | false reds / wrong home / dirty tree | keep batched |
| ESD-01-DF-02 | ESD-01 | minor | RP-07-DF-01 general half recurred | false reds | keep batched |
| ESD-02-DF-01 | ESD-02 | minor | #233 fixture and #226 share a bin | attribution detail | keep batched |
| ESD-05-DF-02 | ESD-05 | minor | eval arms must come from different checkouts | ESD-06 validity | consumed by ESD-06's brief |

**Goal trajectory**

| Goal | Baseline | Contributor signals | Implication for ESD-06 |
| --- | --- | --- | --- |
| GOAL-ESD-VELOCITY | unmeasured | ESD-01: implementation start unknown everywhere; ESD-05 adds a `started_at` convention from now on; this epic's own timeline above | Longitudinal velocity will be **unmeasured**; report this epic's timeline and the observation plan |
| GOAL-ESD-CAPACITY | unmeasured | ESD-04 replay: 3 agree / 1 undecided of 4 (not blind) | Needs blind held-out replay |
| GOAL-ESD-ARCH | unmeasured | ESD-03: 17 F / 13 P / 6 M of 37 (self-applied) | Needs blind application |
| GOAL-ESD-UPTAKE | unmeasured | ESD-05: +3.2–6.3% mandatory-path lines; self-walk reached in ≤ 3 links | Eval cases decide; guard on existing affected cases |

**More expensive if deferred:** ESD-03-DF-01.

**Standing worktrees and headroom:** 6 (epic + ESD-01..05), all homes clean; `/Volumes/dev` 2.6 TiB free.

**Recommendation (default):** dispatch ESD-06 now with the base/tip checkout split and the declared budget.
