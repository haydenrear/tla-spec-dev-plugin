# Workflow subagents, epic 292

**Decision pending live verification.** Hold the current step size. The end-of-epic reviews exposed nine product findings, including two ways an owner could trust stale evidence. The final manual extension check found a tenth product defect involving environment variables. A behavioral graph exposed a defect in its own cleanup probe, and the eval harness suite found two defects in the validation instruments. The provider evaluations and three field decisions still have no observations. They are necessary to judge how many defects escaped the final boundary.

## What was evaluated

| Item | Revision or scope |
|---|---|
| Base | `790955899dfa53802a0b5875a82a9526709df91c` |
| Integrated implementation | #293 launcher `4e801c6`, #294 settings `7c276c5`, #295 regress `8b86642`, #296 review `d1745c5`, #289 owner decisions `437c68a` |
| Final behavioral and unit candidate | `2e9d02e50a1648c8a801510b317415c13bf2c466` |
| Eval harness confirmation | `c3a014551ee30e238e4efc28bab03a8b34b4d2c3`. The three response graders and their harness test were repaired here. |
| Installed consumer | Skill Manager `365abbf16c4fef4da9f0e84a1664fdc70198cbd5`, source archive `2e9d02e`, new home `/workspace/epic-consumer-accepted`. Installed `skt` package files were compared with the candidate. |
| Provider toolchain | meta-harness `42c73ed42a1fe2709f5df07af2a66855fa34b0ca`, real private servers, deterministic local ACP and OpenAI-compatible HTTP backends. Live ACP selection is `CLAUDE_haiku`; live HTTP selection awaits an authorized endpoint. |
| Eval controls | One setup smoke, then one observation each for weakened guard, clean review, missing evidence, large repair escalation, and caller instructions conflicting with a rule. A score-change claim requires the repository's six-sample comparison. |

The ticket work used local fixtures and the focused regress suite. The #289 handoff recorded 52 passing regress tests. Independent reviews, full suites, installed-consumer exercises, and full graph runs began after all five implementations were integrated.

## Independent review

Two independent Codex reviewers received the same base and initial integrated head. They followed different paths through the change and revisited their findings at `1536abc` and `315f1fe`. Their session identifiers are recorded below. The runtime did not expose a model-version string or meta-harness execution ID for these sessions.

| Reviewer | Scope and original evidence | Recheck at 315f1fe |
|---|---|---|
| `/root/cli_review` | Caller → configuration → route → request → cancellation and evidence. Reported SA-REVIEW-01 through 05. Recheck found direct SIGTERM and provider-discovery timeout still mishandled after the first repair. | A local client received cancellation on parent SIGTERM, its PID was reaped, and the owner exited 143. A discovery timeout returned 3 with a durable incomplete receipt. Caller-owned ACP regress still trusts the operator's route declaration. |
| `/root/regress_review` | Failed node → attribution → cumulative patch → acceptance and release. Reported SA-REVIEW-06 through 09. Recheck found that retry could acknowledge an altered digest after acceptance. | Unchanged evidence allowed a retry. Altered or deleted attribution was refused. An independent Linux fixture observed a detached grandchild while alive and reaped it after exit. |

The [attribution ledger](attribution.yaml) records the affected area, severity, discovery channel, effect, repair commit and regression evidence for each reconciled finding. The seal and timeout findings above are additional reproductions and repair laps within their original rows. The CLI reviewer also independently checked the two eval repairs at `c3a0145` and verified six role-environment assertions at `2e9d02e`, including punctuation and case collisions.

## Clause-level evidence

| Clause | Observation and boundary |
|---|---|
| Install and discover roles | A clean Skill Manager install resolved all three units and reported 17 CLI dependency entries installed. Homebrew-backed commands were skipped on Linux. The installed executable listed `regress` and `review`. The smoke used a venv-capable CPython and task-local Git URL mappings for the two private dependencies. |
| Add a role | A third fixture role registered its own input handler and result reader and ran through the CLI against a stub episode after a dry run. At `c3a0145` it erroneously inherited the review model variable. The final control covers independent names and aliases (SA-MANUAL-01). `test_plugin_can_register_another_role_with_its_own_result_reader` records the result. |
| Apply overrides and reject an incapable target | Resolver tests exercise defaults, role profiles and invocation settings. The installed graph dry-runs review on the Python 3.11 and 3.13 wrappers and inspects the selected model in its request. A private mislabelled model is rejected. Remote regress capability remains an operator declaration because the server model list omits transport. |
| Preserve legacy regress and owner authority | Nine fixture scenarios passed through the cleanly installed executable. They covered both entry points, shared history, graph-backed green and red, rejection of stale and nonexistent evidence, acceptance and retry, failed assertions, and cross-ID admission. The harness in this exercise writes fixture graph summaries. |
| Route review over ACP and HTTP | Both real meta-harness transports reviewed the same synthetic revisions `6cea82e717e017bef3fcbac561c1983e031c8110` → `208e6773ce035f53c2bccffcdc3bdc512fb64da2`. The scripted ACP execution `01a21528-da19-7440-9884-990232c75e97` and loopback HTTP execution `01a21528-e461-7930-bfd5-7f7b86628035` each returned exit 1 and the seeded `cart.py:1` finding from separate attempt directories. The clean and missing-evidence controls then returned 0 and 3, respectively, on each transport. Both backends supplied a fixed response. [Six transport receipts](transports.json) |
| Evaluate real subagent behavior | **UNDECIDED.** 82 eval definitions parsed, 50 regex graders compiled, and the eval home resolved four offline wheels. The eval harness suite passed 43 tests with two macOS-only skips in 5.11 seconds. The setup checker flagged absent Claude login files and the macOS Keychain link on this Linux host. The billed setup smoke, three review controls, and two regress cases await live credentials and provider approval. |
| Observe #289 in use | **0/3 field observations.** Each needs its regress ID, before/after owner refs, owner decision and ledger inspection. The disposable fixtures have separate evidence. |

## Behavioral graphs

At the final candidate, the combined skt and eval harness test run passed 564 tests in 217.50 seconds. The skt suite contributed 521 passes and three skips (a fixture without a store checkout and two empty command parameterizations). The eval harness contributed 43 passes and two macOS sandbox skips.

All five registered graphs were in scope, including the two opt-in graphs. The [graph receipts](graphs.json) list the node verdicts, execution scopes and trace IDs. The local runs used the repository front door with freshly materialized bindings. In a second clean checkout, the installed `skt regress adopt` and `skt regress run` dispatched all five graphs through a private meta-harness server to a deterministic ACP worker. The worker invoked the attempt’s real `graph.sh` separately for each graph. The runner read the fresh summaries and returned **GREEN** after 436 seconds. All 21 nodes passed. The owner branch stayed at `2e9d02e`, with a clean working tree and zero attribution gaps. Execution ID `01a2152a-cb62-78a0-92f2-99ec8adf65d9`. [Installed regress receipt](regress.json)

Two earlier full `specWorkflow` attempts errored at the nested Gradle process boundary. Run `20261125-234439` had seven passes, one error and one skipped reference-adapter check. SA-GRAPH-01 records the repair. Full run `20261126-000640` then passed all nine nodes. A separate `effectProviderExamples` attempt, `20261125-235358`, failed because the launching shell omitted the installed `tlc2` directory from PATH. The failed generated-case step and the subsequent full retry are retained in the receipts.

| Full graph | Passing run | Nodes passed |
|---|---|---|
| specWorkflow | 20261126-000640 | 9/9 |
| cliWorkflow | 20261126-000155 | 2/2 |
| effectProviderExamples | 20261126-000229 | 1/1 |
| sktSurface | 20261126-000427 | 6/6 |
| sktHooks | 20261126-000552 | 3/3 |

All five confirmations in the table ran at `2e9d02e`. Each run completed its full plan.

After graph confirmation, an operator walkthrough in a fresh Git repository listed both roles through the installed executable, selected a project review profile, overrode its model for one dry run and repeated the original invocation. The three receipts reported `HTTP_review` from the profile, `HTTP_other` from the command line and `HTTP_review` from the profile. The working tree remained clean.

## Outstanding evidence

The separate live-model run needs approval for the repository graph brief, source, diff and evidence to reach Anthropic through Claude Code, and a runtime `CLAUDE_CODE_OAUTH_TOKEN`. The second live review needs an approved OpenAI-compatible endpoint and its credential variable. Keep credential values in runtime secret settings. After authorization, run the installed regress sweep, the two independent live target reviews and the eval smoke before the five preregistered cases. Record actual model IDs, costs, elapsed times and attempt IDs. The first three real consumer regress runs provide the field record for #289.

## Step size and cost

- **CATCH.** The planned final review caught nine distinct product issues. The final manual extension check found one further product defect that had escaped those reviews. The full graph caught one instrument issue and the eval harness suite caught two. No post-boundary escape rate is available while field verification remains open.
- **REACH.** The graph verdicts exercise the installed wrappers, pinned interpreters and lifecycle fixtures. Six additional consumer episodes exercise upstream transport, routed settings and receipt parsing across three fixtures.
- **BLIND.** Scripted providers cannot establish whether a model detects a weak assertion, invents a defect on a clean control, or accepts a plausible unsupported attribution. A successful local close cannot measure unreviewed commits in a consumer's real epic.
- **PRICE.** This step used two independent reviewers with two repair rechecks, successive suite confirmations and two errored full-graph attempts before the probe repair. The final local regress episode took 436 seconds and the final combined unit run took 217.50 seconds. Review time and internal token costs were unavailable. The recorded validation launched zero external model episodes. The previously reported agent-court run cost $1.13 over 28 minutes and found three instrument failures and one product defect. Its different scope and missing review-cost denominator prevent a like-for-like estimate.
- **HOLD, low confidence.** The review boundary found high-impact issues in routing, cancellation and owner decisions. Some survived the first repair. The third-role fallback also escaped the two specialist reviews and was caught in final manual validation. Revisit step size after recording the live evals, actual run/wait cost and all three field outcomes. Repeated escapes at a coupled boundary would support reducing the next batch.
