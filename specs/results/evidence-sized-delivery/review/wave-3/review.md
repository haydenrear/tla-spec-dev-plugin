# Milestone review — waves 1–3 (ESD-01, ESD-02, ESD-03)

Epic `evidence-sized-delivery` (#234). Range: `9635bad2` (plan commit) → `6380abe3` (ESD-03 merge),
plus the epic-agent commits recorded below. Policy in force: `review_policy.cadence: milestone`,
`gate: false`, `walkthrough: on-request` — the owner asked for final review only, so this artifact
is written and the epic keeps dispatching. Files here: `diff.stat` (full, incl. history),
`diff.patch` (excludes `specs/.history`, which is 48 858 added lines of append-only close snapshots),
`../merges.md`.

## 1. Hot spots

| # | Location | Why hot | Question for the reviewer |
| --- | --- | --- | --- |
| 1 | `skills/test-graph/references/graph-architecture-review.md` (+399, new) | Largest instruction change; carries code-level claims about the runner (`PlanExecutor.shouldRunAfterFailure`, `UvExecutor` cwd, `procs.run` without timeout) and the worked review of real nodes | Do the runner claims hold against the installed test-graph at `a1ff56cf`? Should the worked review be its own page so the checklist stays short? |
| 2 | `skills/spec-double-2/references/bug_attribution.md` (+177/−6; now 943 lines) | New §4.3 (origin/channel/effect axes), §6a false-red resolution, §7b migration map, §7d TLA+ substrate + `UNMODELED/<instrument>`, §7e worked examples | Is §6a item 3's exoneration bar ("red on the untouched base and the touched path passed") right? Is §4.3's "origin is relative to the repository keeping the record" rule acceptable (ESD-02's own inference, not ESD-01's)? |
| 3 | `specs/results/evidence-sized-delivery/ESD-01/inventory.yaml` (1 837 lines, 117 rows) | Every later ticket cites it; rows 46–117 were extracted by delegated readers and spot-checked | Spot-check a consumer row against its primary record before trusting a family count. |
| 4 | `skills/discovery/SKILL.md` (+33/−2 ESD-02, +6 epic agent) | Entry-point skill; ESD-02 added the "model is the architecture anchor" section; the epic agent added the single-module exception (ESD-02-DF-02) | Does the exception weaken the stop rule for genuinely partial baselines? |
| 5 | `test_graph/sources/spec_workflow_cleanup.py:29-32` (not changed; ESD-03-DF-01, major) | `Path(ctx.get(...) or "")` → `Path(".")`; `shutil.rmtree` on the node cwd when `repoPath` is absent; runs as a finalizer and under continue-after-failure. Verified by reading the source; not reproduced (it would delete `test_graph/`) | Promote now? See §5. |
| 6 | `specs/.history/evidence-sized-delivery/ticket-00{0,1,2}-*` (≈16 k lines per no-op close) | Each no-op close snapshots four full model copies; this is the dominant line count of the epic | Cost observation for ESD-04/06, not a defect. |

No file was written by two tickets (serial waves). No net-new production code.

## 2. Decisions made implicitly, and guardrails overridden

**Implicit decisions**

| Decision | Where | Alternative not taken | Cost to reverse later |
| --- | --- | --- | --- |
| Goal targets report-only (no numeric thresholds) | `ticket_plan.yaml` `epic_goals[*].target` | Ask the owner for thresholds at kickoff | Low: a later amendment can add targets before ESD-06 runs; never after |
| ESD-06 eval budget ≤ 48 billed case-runs / $40 | `ticket_plan.yaml` `eval_budget` | No cap, or owner-set cap | Low before wave 6 |
| Epic agent provisions worktrees and launches ticket agents (subagents) | this session | Hand issue URLs to the owner | None for the artifacts |
| Effect axis lives in prose (`consequence:`/`observed`), not a new field | `bug_attribution.md` §4.3 | A new `effect:` token | A future ticket if the prose proves unqueryable |
| False reds: correction is one CATCH against the instrument listing charged runs; no new record kind | `bug_attribution.md` §6a | A dedicated false-red record shape | Medium: changes how every ledger records false reds |
| One new test-graph reference page rather than extending `workflows.md` | `skills/test-graph/references/graph-architecture-review.md` | Inline in `workflows.md` / `failure-loop.md` | Low |
| Ticket plan regenerated without YAML aliases (CLI parser refused `&id001`) | epic commit `515f0af4` | — | None; content unchanged |
| Spec tickets opened and closed by the epic agent with a filled complexity ledger (`refinement.searched: true, outcome: none`) | `specs/.history/evidence-sized-delivery/ticket-00*` | Skip per-ticket closes as bug-sweep did | None |
| Applied ESD-02-DF-02 (single-module baseline is complete) in the epic worktree | `skills/discovery/SKILL.md`, `references/layout.md` | Leave deferred | Low |

**Guardrail overrides**

| Override | How checked | Result |
| --- | --- | --- |
| `--allow-open`, `--accept-new`, `--no-promote-current`, `--force` on close | `grep -rn 'allow.open\|accept.new\|"force": true' specs/.history/evidence-sized-delivery/*/manifest.json` | none |
| skipped / xfailed tests | `git diff 9635bad2..6380abe3 -- '*test*'` | no test file changed |
| REQUIRED matrix entry downgraded | assignment `validation` vs plan entry | none; `validation.graphs: []` is the dispatched value (validator warning accepted at kickoff: prose has no graph proof) |
| weakened invariant / TLC property | `git diff 9635bad2..6380abe3 -- '*.tla' '*.cfg' ':(exclude)specs/.history'` | none |
| `close --force` over a non-custody blocker | close-out verdicts | none; three clean close-outs |
| inline out-of-scope fixes | ledger `fixed-inline` | none (ESD-03's README graph-count fix is inside its own conflict key) |
| ticket over deferral budget | ledger rows per `found_by` | ESD-03 at 5/5 (budget used, not exceeded) |
| goal target edited after dispatch | `git log -p 9635bad2..HEAD -- specs/desired_program_model/ticket_plan.yaml` over `epic_goals` | none (only `status` fields and the alias-free regeneration) |

**Product-contract conformance.** The product contract is #234's design contract and mandate.

| Core element | State after wave 3 | Evidence | Scheduled where, if not yet |
| --- | --- | --- | --- |
| No new scripts/controller/runner/CLI/validator/gate | holds | `git diff --name-status 9635bad2..6380abe3 --diff-filter=A -- '*.py' '*.sh' ':(exclude)specs/.history'` → none | — |
| Origin recorded separately from detection channel; false reds/greens, setup failures, unknown | implemented | `bug_attribution.md` §4.3, §6a, §7e | — |
| TLA+ as stable architecture map; conservation through model evolution | implemented | `bug_attribution.md` §7b, §7d | — |
| Graph guidance names actual nodes and fault boundaries | implemented | `graph-architecture-review.md` worked review (5 nodes) | — |
| Provisional safe step from tighter of review/verification capacity | absent | — | ESD-04 (#238) |
| Separate commit/review/integration/eval/deployment cadence; total cost of candidate batches | absent | — | ESD-04 |
| Short entry-point instructions route to bounded evidence | partial | `test-graph/SKILL.md` +8 trigger; discovery section | ESD-05 (#239) |
| Final integrated confirmation and manual acceptance kept | not yet applicable | — | finalization |

## 3. Where the bugs probably are

| Location | Why suspicious | Cheapest settling experiment |
| --- | --- | --- |
| `graph-architecture-review.md` worked-review claims about runner internals | Written from reading, not running; installed runner version may differ | `grep -n shouldRunAfterFailure` and read `procs.run` in the home's test-graph copy at the pinned revision |
| ESD-03 local-signal flag/miss table (17 flagged / 13 partial / 6 missed of 37) | Same author wrote and applied the checklist → bias toward "flagged" | ESD-06 applies it blind to held-out rows |
| ESD-01 F1 (`failure_cleanup_probe`) cause | Still **inferred**; passed at load 21–30 | Re-run the probe concurrently with a held Gradle daemon (ESD-01-DF-02 / RP-07-DF-01 owner) |
| `bug_attribution.md` §7d claim about `SpecUnitTestsRequireMeasuredCorpus` vs DEF-124 | Possible overclaim of model coverage (suspicion) | Read the invariant against meta-harness DEF-124's record |
| ESD-01 consumer rows marked `not read` | Classification from summaries | Open 3 primary records |

## 4. What the epic agent applied, and what it still owes

**Model delta applied.** None to `specs/desired_program_model`, `specs/current` or `specs/program_model`. Three no-op spec closes: `specs/.history/evidence-sized-delivery/ticket-000-ESD-01`, `ticket-001-ESD-02`, `ticket-002-ESD-03`; TLC MCsmall green before/after (`specs/results/evidence-sized-delivery/ESD-0*/epic-close/`), complexity delta zero. No `UNMODELED/<bin>` reached `MODELABLE`.

**Anchors placed.** 9 findings filed this milestone. The ledger rows carry an `area` but no model anchor, so the epic agent places them here, all outside the program model, consistent with ESD-02 §7d (validation infrastructure is its own area):

| Finding | Anchor |
| --- | --- |
| ESD-01-DF-01 (no start timestamps) | `UNMODELED/workflow-records` |
| ESD-01-DF-02 (RP-07-DF-01 general half recurred) | `UNMODELED/test-graph-runner` |
| ESD-02-DF-01 (#233 fixture vs #226 product in one bin) | `UNMODELED/attribution-records` |
| ESD-02-DF-02 (discovery assumes split layout) | `UNMODELED/skill-instructions` — fixed by the epic agent |
| ESD-03-DF-01..05 (cleanup rmtree, probe node shape, wrapper-installed timeout, ticket-roundtrip home fallback, effect-provider evidence path) | `UNMODELED/test-graph-nodes` |

Count moved into program-model anchors: 0.

**Improvement-card row.** Waves 1–3: 3 tickets delivered, 0 reopened, 0 merge conflicts, 0 guardrail overrides; validation per ticket = doc-contract subset (≈44 s) + spec-unit (≈20 s) + epic TLC (≈2 s); 9 deferred findings (1 major); ticket wall time ≈ 28 min (ESD-01), ≈ 9 min (ESD-02), ≈ 12 min (ESD-03) of agent time.

**Skill changes applied or declined.**

| From | Unit | What was hit | Disposition |
| --- | --- | --- | --- |
| PR #255 | — | none met | — |
| PR #256 | `tla-spec-dev/discovery` | layout assumes Core/Internal/External; this repo is single-module | applied(epic worktree commit after `6380abe3`; ESD-02-DF-02 `disposition: fixed`) |
| PR #257 | `tla-spec-dev/test-graph` | no graph architecture/review guidance | applied in PR #257 (`b37045ca`) |
| PR #257 | repo `test_graph/README.md` | stale graph count | applied in PR #257 |
| epic agent | `tla-spec-dev` CLI (simple YAML parser) | refuses YAML anchors in `ticket_plan.yaml` with "unexpected indentation" | declined(cost: an anchor-free plan is the convention; noted for ESD-06 friction) |

These ship to other homes when the epic merges to `main` and the plugin is synced; no `unit publish` was needed (the units are tracked files in this repository).

**Model corrections owed by merged tickets.** None: no ticket edited `specs/tickets/<id>/desired`.

**Recommendations that remain.**

- Close snapshots dominate the epic diff (≈16 k lines per no-op close) → an option for history to reference unchanged snapshots by digest → new issue → medium. Evidence for ESD-04's fixed-cost accounting.
- No record timestamps the start of ticket work (ESD-01-DF-01) → add a start time to the assignment/PR body convention → ESD-05 can route it in prose → low.

## 5. Suggested next steps

**Ready next:** #238 ESD-04 (deps ESD-01..03 merged) — GOAL-ESD-CAPACITY (direct), GOAL-ESD-VELOCITY (direct), GOAL-ESD-UPTAKE (guard).

**Deferred findings**

| ID | Found by | Severity | Summary | Blast radius | Disposition (recommended) |
| --- | --- | --- | --- | --- | --- |
| ESD-03-DF-01 | ESD-03 | major | `spec.workflow.cleanup` rmtree of `Path("")` = node cwd when `repoPath` absent | data loss in a checkout's `test_graph/` on an upstream failure | **promote to an issue outside this epic** (runtime fix is out of #234 scope); owner decision pending — kept batched meanwhile |
| ESD-03-DF-02 | ESD-03 | minor | probe is an assertion doing setup; undeclared `process:gradle` | false reds across tickets | keep batched (RP-07-DF-01 successor) |
| ESD-03-DF-03 | ESD-03 | minor | `skt.wrapper-installed` nested 900 s inside 900 s timeout | timeouts misattributed | keep batched |
| ESD-03-DF-04 | ESD-03 | minor | `skt.ticket-roundtrip` falls back to root home | wrong-home runs | keep batched |
| ESD-03-DF-05 | ESD-03 | trivial | effect-provider evidence written into checkout | dirty tree | keep batched |
| ESD-01-DF-01 | ESD-01 | minor | no start timestamps anywhere | velocity unmeasurable | keep batched; ESD-05 may route a convention |
| ESD-01-DF-02 | ESD-01 | minor | RP-07-DF-01 general half recurred | false reds | keep batched |
| ESD-02-DF-01 | ESD-02 | minor | #233 fixture and #226 share a bin | attribution detail | keep batched |
| ESD-02-DF-02 | ESD-02 | minor | discovery layout | — | fixed (epic agent) |

**Goal trajectory**

| Goal | Baseline | Contributor signals so far | Implication |
| --- | --- | --- | --- |
| GOAL-ESD-VELOCITY | unmeasured | ESD-01: 23/30 cost rows primary-sourced, 6 unknown; implementation start time unknown everywhere | ESD-06 will very likely report velocity **unmeasured** for longitudinal improvement; plan an observation convention |
| GOAL-ESD-CAPACITY | unmeasured | none yet (ESD-04 is the direct contributor) | — |
| GOAL-ESD-ARCH | unmeasured | ESD-03 self-applied: 17 flagged / 13 partial / 6 missed of 37 rows; ESD-02 enabling (0/5 origin-channel confusions) | Plausible; needs ESD-06 blind application |
| GOAL-ESD-UPTAKE | unmeasured | reading cost grew: `bug_attribution.md` 772→943, new 399-line test-graph page | ESD-05 must keep entry points short; ESD-06 measures it |

**More expensive if deferred:** ESD-03-DF-01 (any run with a missing `repoPath` deletes `test_graph/`).

**Standing worktrees and headroom:** 4 (epic + ESD-01..03), clean home close-outs; `/Volumes/dev` has 2.6 TiB free (`df -h`). All stay until the final sweep.

**Recommendation (default):** dispatch ESD-04 now; file ESD-03-DF-01 as a separate bug issue after owner confirmation, keeping it out of this prose-only epic.
