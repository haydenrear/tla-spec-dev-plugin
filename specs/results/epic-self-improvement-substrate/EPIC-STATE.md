# self-improvement-substrate — the whole epic

Written 2026-09-25. Epic `#333`, branch `epic/self-improvement-substrate`,
plugin `main` at `212b8387`. Delivery surface is
`github.com/haydenrear/tla-spec-dev-plugin`; the old `tla-spec-dev` remote was
retired and its PR closed on the owner's instruction.

`evals/STATE.md` is the eval lane in detail. This is the epic.

---

## Where it stands

**24 of 27 tickets done.** Three remain, and all three are the eval ladder's
top:

| ticket | wave | what it is |
| --- | --- | --- |
| **SI-21** | 19 | ladder 3/4 — the tla-spec-dev CLI's seven verbs and the plugin's own surface |
| **SI-22** | 20 | ladder 4/4 — skill-manager CLI per agent type, from a fresh home |
| **SI-23** | 21 | **Evaluation B** — decides six of the ten goals |

Nothing else is outstanding. Waves 0–18 are closed and reviewed.

---

## The ten goals

Four were decided by **SI-08 (Evaluation A)** at wave 10 and are frozen. Six are
**undecided** and belong to SI-23.

### Decided (SI-08, wave 10)

| goal | verdict |
| --- | --- |
| `GOAL-pinned-eval-toolchain` | **MET** — and the pin demonstrably changes which bytes run |
| `GOAL-one-unit` | **SPLIT** — met in the project home, not in the root home; graphs MET, eval cases UNDECIDED |
| `GOAL-findings-become-changes` | **NOT MET** — 19 of 121 findings carried a parseable `skill_change` |
| `GOAL-blockers-propose` | **NOT MET** — two of three conditions hold; **discrimination does not** |

**Two of those have moved since, and SI-23 owes the re-reading.**
`GOAL-findings-become-changes` is now **70 of 149 (47%)**, up from 19 of 121
(16%) — real movement, still short of "every finding". `GOAL-one-unit`'s root-home
half was the target of the skt sweep: 46 homes carried a duplicate `plugins/skt`
beside the carrier that contains it, and all 46 were cleared (EA-DF-05), with the
source of the duplication — 74 project manifests declaring what the carrier
ships — swept too (EA-DF-06).

### Undecided (SI-23 decides)

| goal | the claim |
| --- | --- |
| `GOAL-one-plugin` | one installed plugin; skt inside it, wt inside skt; only the Homebrew CLI separate |
| `GOAL-evals-earned` | no eval written for behaviour nobody watched work — manual record precedes every stage's cases |
| `GOAL-epic-owns-the-model` | at every wave close the epic agent applied the delta, placed anchors, wrote the card row |
| `GOAL-no-new-gates` | nothing this epic adds refuses; every new check warns and exits 0 |
| `GOAL-progressive-disclosure` | little loads at session start; the rest is behind a reference map |
| `GOAL-evals-one-command` | every eval in the plugin's `evals/`, one command, at least one case per nested skill |

**What can already be said about two of them**, as evidence rather than verdict:

- `GOAL-evals-earned` — the ordering claim is **checkable in git, not asserted**.
  For both shipped rungs the manual-record commit is a strict ancestor of the
  first eval-case commit (`8e362bbb→eefe3aa8`, `70549f90→7daa8e18`, `merge-base
  --is-ancestor` rc=0 both) and neither record commit contains a `case.yaml`.
- `GOAL-no-new-gates` — every check added this session warns and carries on.
  The one refusal in the lane (`run.sh` on a dirty or unpushed checkout) predates
  this work and is overridable.

---

## What the epic actually changed

**One plugin instead of seven units.** The substrate now installs as
`tla-spec-dev-plugin` and contains eleven units: `discovery`,
`git-epic-workflow`, `git-integration-repo`, `git-issue`, `git-issue-workflow`,
`plugin-repository`, `skill-manager`, `skt`, `spec-double-2`, `test-graph`,
`unit-authoring`. skt was demoted from its own plugin to a contained skill
(SI-16); wt moved into skt (SI-17).

**The model grew a skt surface.** Four findings that were being filed
`UNMODELED/` now have invariants, one to one — the largest model delta since
wave 4, and the thing the epic kept claiming and had not done:

```
SktNamesNoEpicItCannotResolve        skt status names a long-closed epic
SktClaimsNoMembershipItDidNotJoin    ticket worktree told its ticket isn't in the plan
SktVerdictCoversEverySurfaceItNames  check exits 0 "all current" having skipped a surface
SktPlansNoRemovalWithoutContainment  sweep skips containment with two epics
```

**Five test graphs pass together**, 20 nodes and 608/608 assertions, for the
first time this epic. `sktSurface` was ERRORED at 4/5 nodes the same morning.

**The repository suite holds** at 10 failed / 1853 passed / 6 skipped, compared
by NAME against the recorded baseline — identical sets, zero diff.

**The eval corpus exists and runs**: 64 cases, one command, 58 decidable.

---

## Decisions on the record

**The epic agent owns all TLA work.** Ticket agents report; the model delta is
the epic agent's. Honoured — no merged ticket left a `desired` edit to reconcile.

**The epic branch never merges to a default branch.** `planning_rules.no_default_branch_merge`.
`tla-spec-dev` was retired entirely at the owner's instruction; delivery is
`tla-spec-dev-plugin`, and `main` there is advanced deliberately, with say-so.

**Advisory, not blocking.** `GOAL-no-new-gates` is load-bearing in the eval lane:
every check added warns and exits 0, and the design notes say plainly that an
instrument which blocks the work is a gate wearing a lab coat.

**Fix instruments before running more evals** (owner, this session). A conflict
key keeps two *concurrent* writers off a surface; deferring to an undispatched
ticket is bookkeeping, not safety.

**Remove the need for a network rather than open it** (this session). Asked to
allow a JDK download, the machine already had twelve JDKs. The sandbox keeps no
network at all.

**Measure at n=6 before claiming a change.** One case moved ±0.8 between
identical invocations; four changes were made to it reading noise as signal
before anyone took a real sample.

---

## The two findings worth carrying to the next epic

**1. The sandbox boundary.** Anything that must reach the eval agent arrives
through the **view** or through a **file in the agent's home** — nothing else.
Four addressing schemes failed against it before the fifth and sixth worked:
an exported environment variable (the agent's sandbox does not inherit the
runner's), `$HOME` in a hook (that is the operator's), a symlink over a
directory the harness pre-creates, and a second environment variable not visible
to hooks. This produced three separate "the tool could not start, and the run
scored anyway" defects in one day — jbang wanting a JDK, the orientation hook
wanting a python, every `uv run --script` wanting a registry.

**2. Three-rung unit resolution.** `<home>/skills/<unit>`,
`<home>/plugins/<unit>`, `<home>/plugins/*/skills/<unit>`. Repaired five times
this epic — in `plugin-repo-lib.sh`, in the checkers, in skill-manager's
imports, in 74 manifests, and in 46 homes. **A defect repaired five times is one
missing abstraction, not five bugs.** `unit_dir` exists in one shell library and
nothing requires its use.

---

## What is left, concretely

1. **SI-21, SI-22, SI-23.** Manual record before cases, as both shipped rungs
   did and as git can be made to prove.
2. **Re-run the corpus whole** at one commit. The 45/58 figure predates ten
   fixes, and re-running only failures biases the result — measured: 3 of 11
   returned 1.00 with nothing fixed for them, and one fell 0.86→0.43.
3. **`runs: 1` across all 64 cases.** SI-23 must raise it for what it reads or
   state the limit in its verdicts.
4. **Toolchain drift.** Every score is against pinned
   `skill-manager 0.28.1+g7941f4e1dd9e`, which every run reports as moved from
   the branch tip. Advance the pin deliberately or say so.
5. **Product-side, filed not fixed:** the orientation hook exits 0 silently when
   it cannot resolve an interpreter — on a stock macOS PATH every session
   silently loses the substrate's only discoverability mechanism, which is what
   `GOAL-progressive-disclosure` runs through.
6. **74 manifest edits** remain uncommitted in 74 other repositories.
7. **Restart Claude/Codex** — the MCP gateway printed `ACTION_REQUIRED`.

---

## The honest headline

The substrate scores well; its instruments did not, and that was the work. Of
the low scores investigated to the end this session, **every one was an
instrument defect** — nine found, nine fixed, each producing a plausible number
rather than an error. The remaining reproducible failures are a short list with
causes identified, and the best candidates for genuine capability gaps are
`w-sdc-ticket-binding-bare-adapter-module` and `compose-a-behavioural-graph`,
which fail markers a *successful action* would have written.
