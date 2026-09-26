# The epic, before it is evaluated

**Written 2026-09-26 at tip `37ada6f4`, by the epic agent, at the owner's
request, before SI-23 runs.**

SI-23 is measurement-only and it **freezes six goals**. Anything unexamined
going into it becomes a verdict. So this is the reading I would defend if
someone re-derived every number themselves — including the parts that make the
epic look worse than its ticket list does.

`EPIC-STATE.md` is the standing state. `evals/STATE.md` is the lane. This is the
argument.

---

## 1. Where we are

**29 tickets, 28 delivered, 23 waves.** Only SI-23 remains, and it is an
evaluation: no behavioural delta, measurement only.

| | |
| --- | --- |
| epic branch | `epic/self-improvement-substrate` at `37ada6f4` |
| delivery surface | `github.com/haydenrear/tla-spec-dev-plugin` |
| repository suite | 10 failed / 1742 passed / 6 skipped — names identical to baseline, all 10 |
| graphs | specWorkflow 74 · cliWorkflow 41 · effectProviderExamples 8 · sktSurface 318 · sktHooks 167 |
| corpus | 52 of 58 decidable at 1.00, mean 0.959 — **single sample per case** |
| ledger | 151 rows absorbed + 20 in four open inboxes, **all 20 attributed** |
| descriptions / bodies | 592 words (≤600) · 0 of 11 bodies over 1500 |
| case files | 75, all parse |

**What the epic actually built**, as distinct from what it planned: one plugin
containing eleven units where there were six repositories; a five-rung eval
ladder whose ordering is provable in git; a role-routed reference map with a
propagation channel for four agent types; and a set of instruments that now fail
loudly instead of quietly — which is most of what the last week produced.

---

## 2. The ten goals, read now

Four were frozen by **SI-08 (Evaluation A)** at wave 10. Six belong to SI-23.
I am not pre-empting its verdicts; I am recording what is measurable today so a
number that moves between now and then is visible as movement rather than
discovery.

### The four SI-08 froze — and two have moved

| goal | SI-08, wave 10 | measured today |
| --- | --- | --- |
| `GOAL-pinned-eval-toolchain` | **MET** | still MET — and see §5, the pin covers the *eval* toolchain and never covered the *bootstrap* CLI |
| `GOAL-one-unit` | **SPLIT** — project MET, root NOT MET | **both homes MET.** Zero standalone copies of any contained skill in `~/.skill-manager` or the project home; the plugin installed in both |
| `GOAL-findings-become-changes` | **NOT MET** — 19 of 121 (16%) | **71 of 151 (47%)** carry a parseable disposition. Still NOT MET against "every finding" |
| `GOAL-blockers-propose` | **NOT MET** — discrimination fails | unchanged; no round run since |

`GOAL-one-unit` moving is the epic's clearest structural win and it took three
separate actions to get there: SI-24 rebuilt the root home from a recorded
manifest, `EA-DF-05` cleared 46 duplicate `plugins/skt` directories, and
`EA-DF-06` swept the 74 project manifests that would have regenerated them.
**`EA-DF-05` without `EA-DF-06` would have been a sweep that undid itself.**

### The six SI-23 decides

| goal | decidable today | reading |
| --- | --- | --- |
| `GOAL-progressive-disclosure` | yes | **both clauses MET** — 592 ≤ 600, 0 of 11 bodies over 1500. See §6: the target is satisfiable by degrading the product |
| `GOAL-evals-earned` | yes | **MET on all five rungs**, checkable in git, not asserted |
| `GOAL-no-new-gates` | yes | **holds** — every checker this epic added carries zero non-zero exits |
| `GOAL-one-plugin` | **half** | containment MET; the bootstrap half **cannot be demonstrated** while the repo is private |
| `GOAL-evals-one-command` | yes | **one clause NOT MET** — 2 of 11 units have zero cases |
| `GOAL-epic-owns-the-model` | yes | clause 2 holds; **clause 1 has a four-wave gap that is mine** |

**`GOAL-evals-earned`, stated as evidence rather than claim.** Five rungs, each
with its manual record committed before its first case, and no record commit
containing a `case.yaml`:

```
8e362bbb → eefe3aa8   SI-19      70549f90 → 7daa8e18   SI-20
bec1934b → c96de147   SI-21      679f76f1 → 3dc106fb   SI-22
f8a3994e → b929e07c   SI-29
```

`merge-base --is-ancestor` rc=0 on all five. This is the only goal in the epic
decided by a check that cannot be argued with.

**`GOAL-evals-one-command` fails a clause nobody has stated out loud.** The
target is *"at least one case per nested skill"*. Measured:

```
spec-double-2 20 · skt 17 · skill-manager 11 · git-issue-workflow 9
git-epic-workflow 7 · git-issue 3 · plugin-repository 2 · test-graph 2 · discovery 1
git-integration-repo 0        unit-authoring 0
```

75 case files, 72 under unit names, **2 of 11 units uncovered**. SI-23 should
report that clause NOT MET rather than reading the 75 as coverage.

**`GOAL-one-plugin` cannot be closed on its own sentence.** Containment is MET
and re-verified: no standalone `skt` in root, project or worktree home, `skt`
contained in all three, and the brew CLI pinned at every tier
(`cli="${SKILL_MANAGER_CLI:-/opt/homebrew/bin/skill-manager}"`). But
`tla-spec-dev-plugin` is **private**. SI-22 measured `rc=128`,
`could not read Username`, against `rc=0` under the operator's `HOME`, because
`credential.helper=osxkeychain` comes from the *system* gitconfig while the
keychain it reads is HOME-relative. **What was demonstrated is "fresh home,
operator's credential", not "a machine that has nothing."** Three units install,
not one. Both numbers are in the record, not the flattering one.

---

## 3. Decisions, and who made them

The epic changed shape six times. Every one of these was the owner's, and
several overrode rules the plan itself carried — which is worth recording
because a plan that was never overridden is usually a plan nobody was reading.

| when | decision | what it overrode |
| --- | --- | --- |
| kickoff | `debugging` stays standalone, outside the bundle | — |
| 2026-09-19 | the epic branch never merges to `tla-spec-dev`'s default branch | the ordinary epic close |
| 2026-09-20 | **cut over to the plugin repo at wave 10**, with eight tickets still planned | `planning_rules`, which forbade exactly that. Recorded as an override, not rewritten |
| 2026-09-20 | SI-18 dispatched as a separate agent in the skill-manager repository | the one-repo assumption |
| 2026-09-20 | root-home nuke-and-rebuild authorised (SI-24) | rule 8, ticket agents never touch the root home |
| 2026-09-24 | eval spend authorised | the lane had produced cases and zero measurements |
| 2026-09-26 | **skill-manager released from its epic branch to `main`** | "skill-manager PRs never target `main`" |
| 2026-09-26 | disclosure is **references only, no detection script** | my own recommended design |

**The two that mattered most were both refusals of my recommendation.**

The owner chose references-only disclosure over the marker file I recommended.
The marker would have worked and would have added a mechanism to a substrate
whose whole complaint is that it has too many. SI-29 then delivered routing with
no detection code at all, and it passes both clauses.

And at the release: I asked whether to cherry-pick one 79-line fix or merge the
whole epic branch, showing that the second ships 15 source files and removes
159,734 lines of vendored skills. The owner chose the larger one deliberately,
having been shown the blast radius. **That is the shape a decision record should
have** — the alternative was stated, the cost was measured, the choice was made
knowingly.

---

## 4. Attribution

**151 rows absorbed; 20 more in open inboxes, all attributed.** Of the absorbed
ledger:

```
127  tie to a modelled TLA+ action
 24  UNMODELED/<bin>
```

The unmodelled bins cluster where you would expect if the *instruments* were the
problem rather than the product: `eval-harness` (4), `eval-case` (3),
`test-graph-scaffold` (2), `test-fixture` (2). That matches what the last week
actually found — nineteen defects, seventeen of them in the measuring apparatus.

**In waves 19–22 the cluster moved**, and it is the signal SI-23 should read:

```
UNMODELED/install-pipeline        5     ← and no invariant was added
UNMODELED/record-keeping          3
UNMODELED/eval-harness            2
UNMODELED/bootstrap-preconditions 2
UNMODELED/progressive-disclosure  1     ← new bin
RunSpecUnitTests · RunEffectConformance   1 each
```

**Seven of those twenty arrived with no attribution, and the cause was mine.**
The work orders I wrote for SI-28 and SI-29 dropped the *"attribute before
close"* instruction that #370 and #371 both carried. The agents did not skip a
step; they were never given it. I attributed all seven at wave close and stamped
each with an `attribution_note` naming who did it and when, so the record does
not read as though the tickets had.

---

## 5. The self-improvement record — the epic's actual thesis

The claim is: *the plugin works because agents improve it, and use it to improve
their projects.* Here is the evidence, including the part that undercuts it.

### The funnel

```
151  findings filed
 71  carry a parseable skill_change   (47%, from SI-08's 16%)
 79  carry no skill_change field at all
 40  proposed(...)       ← waiting on the epic agent
 12  none · 9 declined · 1 malformed
 10  applied(...)        ← 7% of findings became a change
```

**Three facts follow and none of them is comfortable.**

**The bottleneck is the epic agent.** The funnel narrows hardest at
`proposed → applied`: 40 against 10. That step is mine. And until SI-29 gave it
a documented use, `specs/results/deferred/EPIC-AGENT.yaml` held **zero rows** —
the one role responsible for closing the loop had no record of ever having been
in it.

**The record of improvement barely survives its own PRs.** Of the ten `applied`
rows, only three name a commit (`4caab479`, `d09d8326`, `f212cbe3`). The rest
say "this PR" or name a path. A fourth *resolves* under `git cat-file` — but
only because this repository has a **remote** named `test-graph`, so a
resolvability check would score that row a pass while pointing at an unrelated
commit. That is why SI-29 documented a form constraining **shape**, not
resolvability, and added no validator.

**But the loop did reach the substrate, and it is checkable.** Every `applied`
row corresponds to something the substrate now checks and did not before: an
UNDECIDED verdict that reaches the screen (`EA-DF-08`), a node stem matched
inside a quoted path (`EA-DF-18`), 46 duplicate plugin directories cleared and
their source swept (`EA-DF-05`/`06`), a hook ordering that stopped discarding
its own report (`EA-DF-13`).

### The one piece of evidence that cuts both ways

`SI-21-DF-01` recorded that `python3` is a zsh alias on this machine, and that
six of SI-21's own measurements had silently run under an interpreter it did not
intend. Its stated remedy: *anything that measures by shelling out to `python3`
should print `sys.executable`.*

Two waves later, SI-29 **read that row**, then made the same mistake inverted —
measured in zsh, attributed the result to a bash script — and filed
`SI-29-DF-03` at high severity claiming my case-parse checker was inert. **I
repeated the claim to the owner before checking it.** It was false: `run.sh` is
a script, bash resolves `/usr/bin/python3`, which has PyYAML.

So: the substrate recorded the lesson, a later agent read the lesson, and the
lesson still did not prevent the recurrence — in the reader, and then in me.
**Filing is not consumption.** The row is kept corrected rather than deleted,
with the recurrence on it, because that is the only version of this that teaches
anything.

---

## 6. The finding SI-23 most needs, and it is about a goal

**SI-29's first pass scored better and was worse.**

It reached **588** description words against a 600 target. It got there by
deleting activation vocabulary: three units lost their `use when` clause and
`skill-manager` had **none at all** — its description said what the skill *is*
and never when to invoke it — while `skt` lost five trigger phrases covering
sweep, retire and disk-reclaim.

A description is what the harness matches an intent against. **The goal as
written scores 588 as the cleaner pass.** Nothing in its target requires the
words to do anything.

The restoration landed at 612, over target, and was compressed to **592** —
eleven units with activation vocabulary, `skill-manager` better than baseline
with five quoted trigger phrases where it previously had zero. The goal did not
need relaxing. But it was satisfiable by degrading the substrate, and only a
measurement **neither the goal nor the ticket required** caught it.

`SI-29-DF-05` records the other half: **nothing makes 592 hold.** SI-09 cut
descriptions to 594 mid-epic and nesting grew them back to 1005. There are eight
words of headroom.

---

## 7. What I got wrong

Stated because SI-23 reads this file, and an evaluation fed only the successes
measures the wrong substrate.

1. **Three consecutive work orders carried an error the ticket agent found.** A
   suite baseline quoted for the wrong command; "warns and exits 0" for a check
   whose exit 10 is the *existing* notify convention, where a literal 0 would
   have built a warning that can never reach an agent; and a funnel figure off by
   one row, twice.
2. **I merged a case that had been unloadable for a full wave.** I verified that
   merge four ways and none of them touched whether a shipped case file parses.
3. **I closed #389 on three falsification arms that all ran the wrong
   interpreter** — verifying the step I performed instead of the outcome, which
   is the rule I put in every work order.
4. **I told the owner my own checker had shipped inert, before checking.**
5. **Two work orders dropped the attribution instruction**, so seven rows
   arrived unattributed.
6. **No model delta across four waves** while five findings piled into
   `install-pipeline`. Wave 17–18 established that rule and I wrote it down:
   *a finding becomes a change when the substrate checks something it did not
   check before.* I did not follow it.
7. **A 57 GB fixture and a disk at 532 MB free**, from a scratch home I placed
   inside the checkout.

The pattern across all seven is one thing: **I verified the step rather than the
outcome**, and the agents caught it four times out of four. That is the review
model working — and it is also the strongest argument that the epic's own
verification discipline is not yet a property of the substrate, only of the
people applying it.

---

## 8. What SI-23 must not do

1. **Do not report a mean without its spread.** `runs: 1` on the corpus; and
   `--runs 6` does **not** pin a score — 0.89→0.81 and 0.97→0.94 on unchanged
   cases at one commit.
2. **Do not read 52/58 as improvement.** Eleven instrument defects were fixed
   between that run and the one before it. The earlier number was wrong; the
   substrate did not move.
3. **Do not close `GOAL-one-plugin` on a fresh-machine claim** while the
   repository is private.
4. **Do not read 75 cases as per-skill coverage.** Two units have none.
5. **Do not score `GOAL-progressive-disclosure` without §6.**
6. **Do not treat `GOAL-epic-owns-the-model` as MET because the tickets
   behaved.** Clause 2 holds. Clause 1 has a four-wave hole and it is mine.
7. **A run that ends on the turn ceiling is UNDECIDED, not red** — the plan's
   own acceptance.

---

## 9. Open, and carried

| | |
| --- | --- |
| **#384** | adapter bindings — restated by SI-21; residual is a hand-edit hole, no check |
| **#385** | the SessionStart hook exits 0 silently when it cannot resolve an interpreter |
| **#387** | `skill-manager uninstall` and `skt status` resolve different homes |
| `SI-28-DF-01/02` | `install --dry-run` does not parse the manifest; no manifest field for a CLI floor — both skill-manager's |
| `SI-29-DF-05` | nothing makes 592 hold |
| — | **the scorecard still has no eval case**, open since wave 4 |
| — | **`install-pipeline` has five findings and no model** |
| — | 74 manifest edits uncommitted in other repositories |
