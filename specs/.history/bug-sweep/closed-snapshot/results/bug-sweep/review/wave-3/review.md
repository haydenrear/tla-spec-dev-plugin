# Milestone 1 review — epic/bug-sweep (#199), waves 1–3

Range `df48724c..a783c57d`. 19 fix tickets merged (PRs #176, #204–#221), zero merge conflicts.
Evidence: `merges.md`, `diff.stat`, `diff.patch` (excludes the 789 deleted `specs/tickets/*` files), `sanity/`.
Review policy: milestone after wave 3, **gate** — no evaluation ticket is dispatched until the owner answers.

Code churn outside evidence and the ticket deletion: 99 files, +9 888 / −484. By surface (lines changed):
tests/ 2 435 · test-graph 2 193 · skt 2 190 · git-epic-workflow 1 747 · spec-double-2 995 · spec model 310 ·
git-issue-workflow 227 · examples 213 · test_graph 41 · skill-manager refs 12.

## 1. Hot spots

| File | Tickets that wrote it | Why it matters |
|---|---|---|
| `skills/spec-double-2/scripts/close_tickets.py` | BS-01, BS-12, BS-21 | three serial changes to the workflow close: refusal of foreign/rejected ledger input, desired carry, missing-result guard. Every refusal is forceable. |
| `skills/spec-double-2/scripts/tla_spec_dev.py` | BS-01, BS-12, BS-15 | `close ticket` gained `--feedback`, `--tlc-report`, `--closure`, automatic desired carry, mutation-path refusal |
| `skills/test-graph/scripts/run.py` | BS-03, BS-11, BS-13 | errored vs failed → `outcome.json` → `--resume`. 86 script tests pass. |
| `skills/skt/src/skt/{sync,ticket,sweep,build_cmd,artifacts,ticket_integrity}.py` | BS-05, BS-06, BS-19, BS-20 | the whole worktree front door changed in one milestone |
| `skills/git-epic-workflow/scripts/` | BS-12, BS-14, BS-15, BS-22 | two new scripts (`milestone.py`, `census.py`) against the owner's "instructions over scripts" preference — both small, tested, forceable |

## 2. Decisions made implicitly, and guardrails overridden

| Decision | By | Default it set | Cite |
|---|---|---|---|
| Desired carry is **automatic** on every `close ticket` (opt out `--no-carry-desired`) | BS-12 | `desired_program_model/` changes on each ticket close | #214, `tests/test_close_carries_desired.py` |
| #134: a rejected ledger input now **refuses** the close (forceable) — reverses "the ledger never refuses" | BS-01 | refusal + `--force` | #208 |
| Intact declared evidence **blocks** worktree removal (not a warning) | BS-19 | refuse, `SKILL_GATES=off` to force | #215 |
| Integrity manifest at `<git-common-dir>/skt-integrity/` | BS-19 | location/format chosen by the agent | #215 |
| Milestone config file named `epic-workflow.toml` `[milestone]` | BS-14 | no prior convention existed | #218 |
| SIGKILL and timeout are both `errored`, told apart by `cause`, not a 5th status | BS-11 | four-value status set | #216 |
| `--resume-from-build` relative paths now resolve against the test-graph root, not the caller's cwd | BS-13 | behaviour change for relative paths | #220 |
| BS-01 edited the skill-feedback adapter in all three model trees; BS-08 edited `specs/current` adapters, not only tests | BS-01, BS-08 | model trees touched by ticket agents (small corrections) | #208, #221 |
| **Merge lane not held strictly** (BS-22, BS-10, BS-20, BS-12, BS-21 early) | epic agent | merged on arrival where keys were disjoint and deps merged | `merges.md` |
| Ticket agents could not run `home close-out` (auto-mode classifier) | environment | 19 worktree homes not closed out; every agent reports no skill edits in its home | BS-03-DF-02 |
| Graph validation used the **in-repo** runner, not `run-graphs.py` (which binds the installed test-graph since BS-09) | tickets + epic agent | in-repo runner for any test-graph change | #204, #216 |

## 3. Where the bugs probably are

- **`close ticket` now does more on every call** (desired carry, ledger marking, mutation refusal). Each piece is tested alone; the combination on a real multi-ticket epic close has not run. *Suspicion.* BS-16's specWorkflow + BS-18's manual loop are the first combined exercise.
- **specWorkflow `failure_cleanup_probe`** errors "live descendants" under host load (load avg 28–47 on 10 cores; it errors on the untouched base too). The probe gives a nested Gradle 20 s to drain. Consequence: `spec.reference.adapters_resolve` has **not run once** this epic. BS-07-DF-05.
- **`skt sync` pin path** was proven against a fake CLI only; the real `project resolve` on a drifted unit has not run (BS-05-DF-02).
- **`skt build` exit 4** parses the CLI's English ("it is built from …") — falls back to exit 1 if skill-manager rewords it (BS-20).
- **`snapshot_results` basename collisions** silently overwrite results in close snapshots (BS-21-DF-02).

## 4. What the epic agent applied, and what it still owes

Applied in `a783c57d` (tracked machinery in this repo): skt SKILL.md sync wording (BS-05-DF-01); `skt/__init__` re-exports (#212); git-epic-workflow SKILL.md lists `census.py`/`milestone.py` (BS-15-DF-03); plan-and-schedule rerun-reproduction pointer (BS-04-D1); skt `test_cli_floor` prunes harness caches (same defect as BS-08's fix). Plan YAML rewritten without anchors in `933bfcad` (BS-01-DF-01). Epic deferred ledger created; census PASS on 49 rows.

#### Model delta applied
None by the epic agent. Ticket-made model-tree edits (no `.tla`/`.cfg` changed anywhere): BS-01 skill-feedback adapter `--feedback` in `specs/{current,desired_program_model,program_model}/production_adapters.py`; BS-08 `specs/current/{production_adapters.py,adapter_case_runtime.py}`, `specs/current/tests/*`, and comment-only citation repairs in all three `spec_manifest.yaml`. The 19 no-op spec-ticket closes have **not** been run yet — owed before finalization.

#### Anchors placed
None. All 49 findings are tooling defects anchored to a unit (`unit:` field in the ledger), not to a `<Module>.<Action>`; no `UNMODELED/<bin>` reached MODELABLE.

#### Improvement-card row
| Epic | Tickets | Issues addressed | Red→green proven | Findings filed | Conflicts | Lane deviations |
|---|---|---|---|---|---|---|
| bug-sweep M1 | 19 | 37 (+#200) | 19/19 tickets show red-on-base → green-on-branch (local; BS-16 decides) | 49 | 0 | 5 early merges |

#### Skill changes applied or declined
| Unit | Hit | Disposition |
|---|---|---|
| skt (PATH) | `skt` on PATH is the root home's | declined here → finding BS-03-DF-01 (SessionStart/launch wrapper change; successor) |
| git-issue-workflow | ticket agents denied `home close-out` | declined → owner decision (below) |
| spec-double-2 `load_manifest` | plan YAML anchors | applied(933bfcad) — plan written without aliases; loader itself unchanged (BS-01-DF-01) |
| spec-double-2 refs | `--feedback`/`--tlc-report`/`workflow:` undocumented | declined → BS-01-DF-04 |
| spec-double-2 | consumption.md / agent_roles.md drift | declined → BS-02-DF-01/02 |
| test-graph run.py | describe-errored read as not_run | applied(d9c20ee4, BS-11) |
| skt SKILL.md | sync described as trunk pull | applied(a783c57d) |
| skill-manager CLI | no per-revision sync verb | declined → upstream, BS-05-DF-02 |
| skill-manager CLI | build exit 1 conflates blocked/failed | declined → upstream, BS-20-DF-01 |
| skt `__init__` | new names not re-exported | applied(a783c57d); version bump declined (release decision) |
| spec-double-2 `tla_spec_dev.py` | stale `scripts/run_tlc.sh` hint | declined → BS-07-DF-01 |
| test_graph probe | lingering daemon under load | declined → BS-07-DF-05 |
| spec-double-2 refs | desired carry undocumented | declined → BS-12-DF-03 |
| test-graph resume | cannot resume past an errored earlier node | declined → finding (BS-21 PR) |
| git-issue-workflow assignment template | accelerate block uses old resume form | declined → render `run.py --resume` in future assignments (successor) |

#### Model corrections owed by merged tickets
| Ticket | Correction | Owed |
|---|---|---|
| BS-08 | `specs/current` adapter + test edits (spec-unit 11 → 2) | promote to `specs/program_model` / `desired_program_model` at workflow close |
| BS-01 | adapter `--feedback` | none — applied in all three trees by the ticket |

## 5. Suggested next steps

**Goal trajectory (local signals only — the evaluation tickets decide):**
| Goal | Baseline | Local signal now | Target | Outlook |
|---|---|---|---|---|
| GOAL-BS-BUGS | 0/37 | every ticket recorded red-on-base → green-on-branch | 37/37 | on track; partial items named in findings (#171 sweep half, #134 delta half, #166 2nd symptom, #173 write-once) |
| GOAL-BS-SUITE | 9 failed | 1 failed / 1920 passed (BS-08, full run); spec-unit 11 → 2 | 0 | **will miss by 1** unless the owner decides `test_the_same_tag_control_holds` (deliberately red) |
| GOAL-BS-GRAPHS | 5/5 PASSED | cliWorkflow, effectProviderExamples, sktSurface, sktHooks PASSED on tip (in-repo runner); specWorkflow 7/8, probe ERRORED (load) | 5/5 | depends on a quiet host for the probe |
| GOAL-BS-EVALS | unmeasured | — | 0 regressions | BS-17, ~$66 for base + tip |
| GOAL-BS-MANUAL | unmeasured | — | owner accepts | BS-18 |

**Deferred findings (49, ledger `specs/results/bug-sweep/deferred-ledger.yaml`).** None blocks the evaluation tickets. Recommended default: **keep batched → successor epic**, except:
| ID | Severity | Summary | Recommendation |
|---|---|---|---|
| BS-01-DF-01 | major | plan YAML anchors break `load_manifest` | close: fixed in 933bfcad (plan side) |
| BS-08-DF-02 | escalate | `test_the_same_tag_control_holds` is deliberately red | **owner decides**: keep red, or `xfail(strict=True)` |
| BS-08-DF-01 | minor | Skt actions unbound → spec-unit red | keep batched (one of the 2 spec-unit reds) |
| BS-08-DF-03 | minor | close truncates ledger-refusal message → spec-unit red | keep batched (the other spec-unit red) |
| BS-07-DF-05 | — | cleanup probe not load-tolerant; `adapters_resolve` never runs | promote if BS-16 cannot get a quiet host |
| BS-20-DF-01/02/03, BS-05-DF-02 | medium | skill-manager CLI upstream | file upstream issues on skill-manager |

**Standing worktrees and headroom:** 19 ticket worktrees + the epic worktree; 92 GiB free (90% used). All stay until the final sweep.

**What gets more expensive if deferred:** the 19 no-op spec-ticket closes + BS-08's model-tree promotion (finalization); the 19 un-closed-out worktree homes.

**Recommendation (default if you say "go ahead"):** keep the deliberately-red test red and accept GOAL-BS-SUITE as "1 named exception"; batch all other findings to a successor epic; dispatch **BS-16** now on the integrated tip (synced home, quiet host for specWorkflow); then BS-17 (~$66 eval spend) after BS-16 reports.
