# Finalization — epic/evidence-sized-delivery (#234)

Integrated tip validated: `0beb5e83` (`tip.txt`), all six ticket PRs merged (#255–#260), origin/main
unchanged since the base `a1ff56cf` (no default-branch integration needed). Run 2026-11-10, serially
(no concurrent graph/eval/suite on the host — the epic's own F1 lesson).

## 1. Integration audit (finalize §1, §1a, §1b)

| Check | Result |
| --- | --- |
| Every ticket delivered, PR merged into the epic branch in promotion order 10→60 | yes — `../review/merges.md` |
| One close-history entry per ticket | `specs/.history/evidence-sized-delivery/ticket-00{0..5}-ESD-0{1..6}` |
| Plan status closed for all six; no `specs/tickets/<id>` left | yes |
| Evaluation ticket merged after every contributor | ESD-06 (#260) last |
| Retired tickets | none |
| Open PRs targeting the epic branch | none |
| Deferred backlog drained | 18/18 settled (census PASS): 7 fixed, 1 consumed, 1 wontfix, 9 carried as #261–#264 |
| Ticket worktree homes | 6/6 `close-out` clean at wave close; re-run immediately before the sweep |

## 2. Integrated validation (finalize §2)

| Instrument | Result | Evidence |
| --- | --- | --- |
| TLC `MC.cfg` on `specs/current` | no error; 3 041 105 distinct states, depth 27, 28 s | `tlc-current-MC.txt` |
| `tla-spec-dev run spec-unit-tests --scope project` | 2 failed / 54 passed — the same 2 known-red on the base (`../baseline/README.md`) | `spec-unit-project.txt` |
| `pytest tests` (full repository suite) | 1 failed / 1950 passed / 1 skipped, 19 m 38 s; the one failure is `test_architecture_tags.py::test_the_same_tag_control_holds`, **deliberately red** (RM-06-DF-01, recorded in `specs/results/bug-sweep/deferred-ledger.yaml`); the epic changed no test or example | `pytest-tests.txt` |
| `cliWorkflow` | PASSED | `graphs-default.txt` (run 20261110-153031) |
| `effectProviderExamples` | PASSED | `graphs-default.txt` (run 20261110-153057) |
| `specWorkflow` | **ERRORED** at `spec.workflow.failure_cleanup_probe` (`node launcher exited with live descendants: <pid>`); `spec.reference.adapters_resolve` not run | `graphs-default.txt` (run 20261110-152821) |
| `specWorkflow` control on untouched `main` `a1ff56cf` | **ERRORED identically** | `control-base-specWorkflow.txt` (run 20261110-153301) |
| `specWorkflow` rerun on tip | ERRORED identically | `rerun-tip-specWorkflow.txt` (run 20261110-153502) |
| `sktSurface`, `sktHooks` | not run (opt-in, net:external) | `graphs-default.txt` |
| `specs/current` ≡ `desired_program_model` ≡ `program_model` | byte-identical model, cfg, adapters, bindings | this session (`cmp`) |

**specWorkflow attribution (applying `bug_attribution.md` §6a, which this epic wrote).** Origin:
`UNMODELED/test-graph-nodes` (the probe node and the runner's process-ownership contract,
RP-07-DF-01). Channel: integrated graph. Effect: **false red** for this epic — exonerated by the
named control (red on the untouched base, and the epic touched nothing the probe executes:
`git diff a1ff56cf..HEAD -- test_graph skills/test-graph/scripts skills/spec-double-2/scripts` →
`test_graph/README.md` only). Not charged to the product. New fact versus ESD-01: the red is now
**deterministic** on this host (3/3 at load 6–19; it previously passed at load 21–30). Carried in #262.

## 3. Goals (finalize §2a)

Targets were set report-only at kickoff (owner: final review only) and were not edited
(`git log -p 9635bad2..HEAD -- specs/desired_program_model/ticket_plan.yaml` over `epic_goals`).
ESD-06 measured on `5404a3c1`+its own commits; every later commit is bookkeeping (no skill or eval
change), so its run applies to the integrated tip (evidence invalidation rule, `step-sizing.md` §8).

| Goal | Clause | Kind | Baseline | Measured | Target | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| GOAL-ESD-VELOCITY | — | perf | unmeasured (no start timestamps anywhere, ESD-01) | this epic: 5 tickets in 1 h 34 m, open→merge ≤ 44 s; ESD-06 ≈ 40 min, $15.67 | report-only | **unmeasured** — no comparable before-value; observation plan in `../goals/GOAL-ESD-VELOCITY/README.md` §4 |
| GOAL-ESD-CAPACITY | — | quality | unmeasured | held-out replay: 4/4 produce both estimates + defensible decision; vs outcome 1 agree / 2 partly / 1 disagree | report-only | **measured** — usable, weak predictive skill; ambiguities carried to #264 |
| GOAL-ESD-ARCH | — | quality | unmeasured (ESD-03 self-score 17 F / 13 P / 6 M of 36) | blind hold-out 10 F / 24 P / 14 M of 48; 0 F of 27 non-node defects; re-score of ESD-03 rows agrees 8/12 | report-only | **measured** — "flags most" does not hold blind; scope gap carried to #264 |
| GOAL-ESD-UPTAKE | guard | eval | unmeasured | 3/18 regress by score, **0/18 attributable** to the instructions (all three are grader false reds, traced) | report-only; guard 0 | **met** (n = 1 per arm) |
| GOAL-ESD-UPTAKE | uptake cases | eval | unmeasured | base 4/5, tip 5/5 | report-only | **measured** — small effect; the model mostly decides correctly without the guidance |
| GOAL-ESD-UPTAKE | retrieval/cost | eval | ESD-05 estimate +3.2–6.3 % mandatory lines | tip: right page first 5/5; searches 30→10, lines read −23 %, turns −41 %, cost −22 % | report-only | **measured** |

Uncovered scenarios (unmeasured): verification > review capacity; graph-origin defect caught by
another channel; attribution conservation through an architecture change; finalizer starting
estimate. Details: `../ESD-06/README.md`, `specs/evals/evidence-sized-delivery/README.md`.

### Improvement-card delta (beside, not inside, the goal table)

| Card | Epic | Dimension | Previous epic (bug-sweep) | This epic | Delta |
| --- | --- | --- | --- | --- | --- |
| this epic's reviews | evidence-sized-delivery | per-ticket spec close receipts | none: "per-ticket spec close receipts (no-op model, never opened)" — `specs/.history/bug-sweep/closed-snapshot/summary.md` | 6/6 | first carded |
| same | same | deferred findings settled at close | (see bug-sweep close) | 18/18 | unmeasured comparison |
| same | same | skill-change proposals with a disposition | unmeasured | 4/4 (`../review/wave-*/review.md` §4) | first carded |
| `improvement-ledger.txt` | repo-wide | recorded-local, filed nowhere | — | 0 | — |

The bug-sweep was not carded under this schema; its row is `unmeasured`, not backfilled.

## 4. Wave reviews (finalize §2b)

`review_policy`: milestone after waves 3 and 5, `gate: false`, merges by the epic agent,
walkthrough on request — the owner asked for final review only. Artifacts: `../review/wave-3/review.md`
(waves 1–3), `../review/wave-5/review.md` (waves 4–5). Waves 1, 2, 4 have no separate artifact by
policy; wave 6 (evaluation) is reviewed here. **No wave review was answered by the owner**, so every
implicit decision in them is listed for the final review (the epic PR's "Decisions awaiting your
acceptance").

## 5. Manual product-testing phase (finalize §2c) — agent pass done (§5a); owner disposition pending

The product here is instruction text, so the manual phase is the owner reading the routes an agent
takes. Prepared scenarios (tester: owner; build: the epic tip; record results in the PR):

1. **Planner path.** From `skills/git-epic-workflow/SKILL.md` → `references/plan-and-schedule.md` §3/§3a/§7 → `step-sizing.md` §1–§5: can you state separate review and verification estimates and a batch for a hypothetical 4-ticket epic using only those pages? Expected: yes, in ≤ 3 links, with fields written to `review_policy` / waves / validation matrix.
2. **Ticket path.** Rendered assignment bullets in `skills/git-epic-workflow/references/epic-ticket.md` → delivery line + Evidence slice; a red from a shared-host probe recorded per `bug_attribution.md` §4.3/§6a as instrument origin, false-red effect, no product charge.
3. **Review path.** `agent_roles.md` § Evidence routing → `skills/test-graph/references/graph-architecture-review.md` five questions applied to `spec.workflow.cleanup`; expected to flag the empty-path deletion (#261).
4. **Finalizer path.** `finalize.md` §2c *Next epic's starting estimate* → §6 below is the first instance; is it what the next planner needs?

Untested scenarios need an explicit owner disposition before the workflow is closed.

### 5a. Agent-executed pass (2026-11-10, at the owner's request)

Tester: the epic agent (Claude Opus 5.5, `claude-opus-5-5`, Claude Code 2.1.322); scenario 3 by a
fresh review subagent of the same model that was given only the pages, the node and the runner sources
(no issues, no `specs/results/`). Build: epic tip `70d31ac7`, detached scratch worktree. Every command
ran against scratch copies; nothing here changed the epic's plan, ledger or issues. **This pass does not
replace the owner's reading**; it records what the pages and their tools actually do when followed.

| # | Scenario | Result | What happened |
| --- | --- | --- | --- |
| 1 | Planner | **pass, with gaps** | `SKILL.md` → `plan-and-schedule.md` §3a → `step-sizing.md`: 2 links. From those pages alone I sized a hypothetical 4-ticket follow-up epic (#261/#262 as TGS-01..04): scope items listed per ticket with interacting pairs; review 3–5 independent / 2 coupled items (low confidence: prior is prose, this is code); verification 1–2 items until the probe is fixed (§9.2, `specWorkflow` deterministic red), so verification binds; batch 1 item/wave, instrument fix first, `cadence: wave`, `gate: true`, `eval_budget` 0 (no prose change, §4 cadence table). Written into `wave`/`depends_on`/`validation`/`review_policy`/`eval_budget`; `validate_epic_plan.py --strict` **OK**. My first draft drew 3 warnings (invented `walkthrough: always`, `blocks` not the reverse of `depends_on`, evaluation ticket with no goal); §4b and the validator caught each. |
| 2 | Ticket | **pass on the rules; two tool defects** | Rendered TGS-03's assignment from the `epic-ticket.md` template with the Evidence slice filled; `validate_assignment.py --strict` **OK**. Recorded the real `failure_cleanup_probe` red per `bug_attribution.md` §4.3/§6a with `census.py record`: origin (validation bin), channel (`test-graph`, run id), effect (false red, `adapters_resolve` skipped), the §6a item-3 control, cost as validation repair — all fit in existing prose, as §4.3 intends. `absorb` then `check`: **FAIL `dangling_duplicate`** (below). |
| 3 | Review | **pass: flagged #261 independently, plus two new defects** | Hops: `agent_roles.md` § review → § Evidence routing row → `graph-architecture-review.md` (3 links). Five questions on `spec.workflow.cleanup`: 3 defects, 1 partial, 1 nothing. The reviewer derived the empty-path deletion from the runner itself (`PlanExecutor.kt:181-184`: a skipped dependency counts as executed; finalizer runs after it), not from the page's own verdict. **Caveat:** the page's *Worked review* (line 376) already states this verdict for this node, so the test is not blind. |
| 4 | Finalizer | **partial** | §6 above carries the keyed estimate, binding constraint and uncertainty that §2c asks for. It lacks §2c's explicit *REACH and BLIND on the affected components* and *recurrence of attributed families* lines, and compares against "planned" rather than per-wave *Delivery velocity and step size* blocks (only wave 5 had one: this plan predates `step-sizing.md`). Discoverability: the estimate's home is "the epic PR" (`finalize.md` §2c, `agent_roles.md` row *epic: finalizer*), but the planner row only cites the page section; nothing says how to find that PR. A body search (`gh pr list --state all --search "\"Next epic's starting estimate\" in:body"`) finds #265 today, and only because the heading is quoted exactly. |

**New findings from this pass** (filed as noted; none blocks this epic, which changed no code):

| ID | Severity | Finding | Where |
| --- | --- | --- | --- |
| MAN-01 | minor | `census.py record --duplicate-of` resolves only within this epic's ledger. A recurrence of an earlier epic's finding — exactly §6a's recurrence case — passes `record` (rc 0) and then fails `check` with `dangling_duplicate`. `deferment.md` says "a finding seen before is recorded with `--duplicate-of`" with no cross-epic rule. Workaround used in this epic: say "recurrence of <id>" in prose (ESD-01-DF-02). | `census.py:203`, `deferment.md:151` → #262 (tool), #264 (docs) |
| MAN-02 | minor | `census.py record --surface` writes only `surface.production`; an instrument path (`test_graph/...`) lands under `production`, against §6a "an `area` on an instrument defect names the instrument". | `census.py:349,394` → #262 |
| MAN-03 | minor | `validate_assignment.py` passes an assignment whose prose bullets still hold template placeholders (`origin/epic/<slug>`, `open ticket <stable-ticket-id>`, `Refs #<issue-number>`). | `validate_assignment.py` → #264 |
| MAN-04 | **high** | `spec.workflow.cleanup` line 35 `.assertion("fixture repo path was published", bool(str(repo)))` is always true (`str(Path(""))` is `"."`): the node reports a published path exactly when it is about to delete `test_graph/`. | `test_graph/sources/spec_workflow_cleanup.py:35` → #261 |
| MAN-05 | medium (inferred) | The cleanup depends only on `spec.workflow.repo` but must run after start/complete/close; it does so only because the graph walks dependencies in list order (`GraphModel.kt:20-36`). Reordering would delete the fixture repo mid-run. | → #261 |
| MAN-06 | minor | Routing rows cite pages by bare filename and wrong section labels: `agent_roles.md:254` names `human-review.md` "§3.3 validation-specific rows" (§3.3 is *Where the bugs probably are*) and "§3.5 *Delivery velocity and step size*" (a bullet inside §3.5 *Suggested next steps*); the row points at checklist A–H, not the five questions, and the page never maps one to the other. `finalize.md` §2c's planner pointer names a page, not a findable location. | → #264 |

Owner disposition still needed: whether this agent-executed pass is accepted for the four scenarios, or
which you will read yourself.

## 6. Next epic's starting estimate (finalize §2c)

Keyed to: repository `haydenrear/tla-spec-dev-plugin`; components = skill reference prose
(git-epic-workflow, spec-double-2, test-graph, discovery, git-issue*); reviewer/verifier =
Claude Opus 5.5 (`claude-opus-5-5`) via Claude Code 2.1.322 subagents; epic-agent verification =
doc-contract pytest subset + spec-unit + TLC per ticket, one integrated eval checkpoint.

- **Planned vs actual.** Planned: six serial waves, one ticket each (conservative, from #234's
  drafting order — not a capacity estimate). Actual: 0 reopens, 0 conflicts, 0 guardrail overrides;
  per-ticket verification ≈ 1 min; integrated checkpoint ≈ 35 min / $16 for six tickets.
- **Review capacity (prose, this repo, this model):** at least one ticket of ≈ 400–1 000 added
  instruction lines per review point with no escape found at wave review; the blind ESD-06 checks
  found the *quality* gaps (#264) that self-review missed → review capacity for self-authored
  rules is lower than self-scores imply. Confidence: low (n = 6, one epic).
- **Verification capacity:** cheap per-ticket checks do not test prose uptake at all; the only
  real verifier is the eval checkpoint (≈ $0.34 per guard case, three grader false reds in 18 →
  instrument reliability ≈ 0.83 per case). Binding constraint for the next prose epic:
  **verification** (grader reliability), not review.
- **Starting recommendation:** for a similar prose epic, batch up to 2–3 independent tickets per
  wave (disjoint skill files), keep one predeclared eval checkpoint per epic, and fix the #263 grader
  false reds first (they would otherwise read as regressions). For code epics touching
  `test_graph/`, start at one ticket per wave until #261/#262 land — `specWorkflow` cannot currently
  go green on this host.
- **Uncertain:** whether the uptake gain survives without the agent having just read the pages;
  model-version sensitivity (only one model observed); velocity trend (first epic with start
  timestamps).

## 7. Deferred findings disposition

| ID | Severity | Disposition |
| --- | --- | --- |
| ESD-01-DF-01 | minor | fixed (ESD-05 delivery line) |
| ESD-01-DF-02 | minor | carried → #262 |
| ESD-02-DF-01 | minor | wontfix (sealed inventory; §7d governs future anchoring) |
| ESD-02-DF-02 | minor | fixed (epic agent, wave-3 review) |
| ESD-03-DF-01 | **major** | carried → **#261** |
| ESD-03-DF-02..05 | minor/trivial | carried → #262 |
| ESD-04-DF-01..03 | minor | fixed (ESD-05) |
| ESD-05-DF-01 | minor | fixed (epic agent, wave-5 review) |
| ESD-05-DF-02 | minor | consumed (ESD-06 base/tip checkout split) |
| ESD-06-DF-01, -04 | minor | carried → #263 |
| ESD-06-DF-02, -03 | minor | carried → #264 |

## 8. Not yet done (needs owner approval first)

- External semantic review of the draft epic PR (finalize §3), then workflow promotion/close with
  `close_tickets.py` (§4) — **the closed snapshot is irreversible and is written only after approval**.
- Owner disposition of the manual scenarios (§5; agent-executed pass recorded in §5a).
- Merge to `main` (owner only), then the one-pass worktree sweep (§6): 7 ticket/epic worktrees plus
  the detached measurement checkout `/Volumes/dev/tla-spec-dev-plugin-esd06-base` (local commit
  `14e3247c`, case data only) and ESD-06's `/private/tmp/esd06-view-*`, `/private/tmp/e-*`.
