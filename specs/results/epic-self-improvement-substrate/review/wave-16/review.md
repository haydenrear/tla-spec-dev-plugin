# Wave 16 review — epic/self-improvement-substrate

Range: `373cd74d` → `fe7f531b`. Two tickets: **SI-27** (#382) and **SI-18**
(#367). SI-27 landed here; SI-18 landed in the **skill-manager** repository as
PR #397, merged to its `epic/self-improvement-substrate` at `7941f4e1`, per the
owner decision of 2026-09-20 that dispatched it as a separate agent in a
separate session.

Wave 16 is not a gate. **Wave 17 is SI-19, the first rung of the eval ladder.**

---

## Block 1 — Model delta applied

**None owed.** Neither ticket changed a TLA+ action, state or invariant.

SI-18 carried the epic's only TLA-adjacent acceptance item, and it resolves to a
recorded non-change: the `@command` binding at
`GitHistoryInternal.tla:251` (skill-manager's spec tree, not this repository's)
**stays as it is, deliberately**. It reads `@command wt close / skt ticket
close`, and `skt ticket close` is still a real command — `skt/cli.py:90` lists
`close` among the ticket verbs, `:225` carries its usage. SI-18 retired the
**vendored copy** of skt, not the command, so repointing the binding would have
made it wrong. The acceptance asked for "repointed or removed deliberately", and
"unchanged" only counts as a decision if it is written down, so it is written
down here and in the ticket's `delivery_note`.

The companion assertion also holds: **no TLA identifier ever named skt.** The
three surviving mentions in skill-manager's live spec trees
(`GitHistoryInternal.tla:216`, `:251`, `HomeIntegrityInternal.tla:596`) are
prose and comments.

## Block 2 — Anchors placed

**None placed.** Every finding in this wave is a harness, checker or record
defect, attributed `UNMODELED/`.

## Block 3 — Improvement-card row

**No round run, and no score is claimed.** Wave 16 ran no scored eval. The eval
ladder that produces the next scored round is wave 17 onward; SI-23 decides the
goals. What wave 16 did produce is the toolchain the ladder will run against:
the pin now resolves to merged SI-18, verified by the CLI's own self-report
rather than ours — `skill-manager 0.28.1+g7941f4e1dd9e`.

## Block 4 — Skill changes applied or declined

| proposal | disposition |
| --- | --- |
| `check_citations.py`: prune non-source trees during descent, index once per root | **applied** (`d09d8326`) |
| `test_card_has_one_home.py`: extend the name prune to build output | **applied** (`d09d8326`) |
| `test_prediction_seal.py`: prune agent homes and build output on its `test_graph` walk | **applied** (`d09d8326`) |
| skill-manager's leak oracle: stop watching `.claude/skills/synced/`, or hash content instead of mtime | **declined here** — the oracle is another repository's code, and the merge did not need the instrument weakened to pass. Filed as SI-18-DF-01 |
| `git-issue-workflow`: pair `remote get-url origin` with `--push` before any ancestry check | **proposed**, unchanged from SI-27-DF-05 |

## Block 5 — Model corrections owed by merged tickets

**None owed.** No merged ticket in this wave left a `desired` edit for the epic
agent to reconcile.

---

## What this wave actually established

**SI-27 made the findings record answerable.** It was two ledgers that
disagreed: 87 rows in `deferred_findings_final.yaml` and 28 more in per-ticket
files that nothing read — which is how the epic agent came to cite `SI-16-DF-02`
and `-DF-03` as the eval blockers while a query for both returned NOT FOUND. The
28 were absorbed; the per-ticket files are inbox stubs now, and a row lives in
exactly one place. The ledger closed the wave at **122 rows, 0 pending**.

**The typed attribution record exists for the first time.** `bug_attribution.md`
defines four kinds and only CATCH had ever been written; all 115 rows were
CATCHes. `specs/results/deferred/attribution/attribution.yaml` now carries
**7 REACH / 9 BLIND / 3 PRICE**, every row with a `skill_change`.

## The recurrence that this wave caught, and why it is the finding

Running the test graphs and then the suite turned five checks red on a tree
whose only difference was generated output. `test_graph` materialises whole
plugin trees as fixtures, so `case_modules.py` had 22 copies; the citation
resolver called a uniquely-named source file ambiguous, the card tripwire
reported the card "stated outside its one home" at a fixture **of the card**,
and the prediction-seal check found 72 consumers of a checker nothing consumes,
one of which was a copy of its own test file.

**This was the third fix of one class.** RD-01-DF-02 pruned agent homes from the
card tripwire; HP-01-DF-01 pruned them from the citation resolver; each fixed
the instance in front of it and neither enumerated the population of walkers.
Section 5 of `bug_attribution.md` had already named the failure —
*"a REACH whose unenforced list was never acted on is a list, not a reach"* —
and there was no reach row for walkers at all, so there was not even a list to
ignore. There is one now (SI-27-DF-06), and its `unenforced_on` names four
surfaces that remain uncovered, including the one that matters most: **the cost
half is enforced in exactly one walker**, so any other can still go quadratic
without ever failing. It would only take longer.

The cost half is the part worth remembering. The first fix was **correct and
useless**: filtering `rglob`'s output still descends every excluded tree, and
`resolve_cited` re-walked per citation, so the shipped checker exceeded a 300s
timeout and reported *nothing at all*. A checker too slow to finish is worse
than one that answers wrongly, and it had been degrading silently for as long as
agents have run test graphs. Pruning during descent and indexing once: 300s → 4.1s,
and the whole suite 2185s → 1259s.

## Three things I got wrong in this wave

1. **I called the five reds "regressions introduced by the SI-27 merge."** They
   were not. They postdated the baseline because my own test-graph runs wrote the
   fixtures. The baseline comparison was sound; the inference from it was not.
2. **I reported a clean suite from a run that never executed.** A bare `pytest`
   without the scope or `pyyaml` that `README.md:168` requires returned
   `401 errors` and `0 FAILED`, and `0 FAILED` is not a green.
3. **An unquoted heredoc executed the backticks inside a ledger row** and ate the
   text, silently. Redone quoted, with substitution done in Python.

## Verified, not accepted

Nothing in this wave was taken on a report alone.

- **The suite** was gated against the pollution deliberately left in place, not a
  cleaned tree: `10 failed, 1843 passed`, compared BY NAME against the ten known
  failures — no new name, no disappeared name, and the five gone (1838 → 1843).
- **The graphs** were run locally because CI never runs them on a PR: that job is
  gated to `schedule`/`workflow_dispatch`, so `skipping` there was by design, and
  reading it as coverage would have been the mistake. 26 of 26 executed, 24 passed.
- **The two red graphs** were proven environmental rather than assumed. Both
  failed the same node over one file neither repository references:
  `.claude/skills/synced/<uuid>/manifest.json`, identical size 6501 bytes, mtime
  only. The decisive control was not a re-run but a `stat`: the file moves its own
  mtime over a 45-second window with no graph running, and the value it moved to
  (`1790191140`) is exactly what the next `ticket-lifecycle` run reported as a
  leak. The oracle's own self-tests — planted unit, planted symlink, in-place
  rewrite, repointed skill link — all passed, so the instrument is sound.
- **The push** was confirmed by re-fetching, not by trusting the push output,
  which is the SI-27-DF-05 lesson.

## Where the bugs probably are

- **The walkers nobody has exercised.** `evals/lib/checks/testgraph_scaffold.py`
  and `evals/lib/grant.py` walk the checkout with no prune. They did not fail
  here, and that is evidence about this tree's contents, not about the walkers.
- **`remote.origin.url` being rewritten by something unidentified.** Seen twice
  (SI-04-DF-04, SI-27-DF-05); no shipped script containing `remote set-url` aimed
  at the parent has been found. It cannot lose a commit — push still reaches
  GitHub — but it makes every epic-mode ancestry check lie, in the direction that
  reads as good news.
- **Frozen goal measurements.** The plan validator still reports that SI-08
  (promotion order 120) measured `GOAL-findings-become-changes` before SI-27
  (165) contributed to it. That is not repairable by reordering finished tickets;
  it is precisely what SI-23 is for, and SI-23's objective already says to show
  both readings side by side.

## Housekeeping done in this wave, stated so it is not mistaken for silence

- Plan revision **8 → 9**. Thirteen `blocks` / `promotion_predecessor` edges were
  repaired to satisfy the validator's "blocks is the exact reverse of depends_on"
  rule; SI-19's `promotion_predecessor` was wrong (`SI-18`, should be `SI-27`) and
  that field is copied verbatim into an assignment, which is how this class of
  error reaches an agent. Validator warnings: 14 → 6.
- `tla-spec-dev` was removed as a git remote; `origin` now points at
  `tla-spec-dev-plugin`. PR #383 on tla-spec-dev was closed unmerged.
- The wide eval lane (566 tracked files, 63 MB) was untracked in skill-manager.
  The `.gitignore` line alone had been inert, because git keeps tracking what it
  already tracks.

## Reviews 11–15 do not exist, and I am not reconstructing them

Waves **11, 12, 13, 14 and 15** (SI-16, SI-17, SI-24, SI-25, SI-26) have no
`review.md`. The plan validator names only wave-16 because it reports the latest
closed wave, so the honest count is six, not one. I am writing wave 16 because it
gates wave 17 and I hold first-hand evidence for it. I am not back-filling the
other five: this project has already recorded that a record reconstructed later
by a reader is a weaker artifact than one written by the party who did the work,
and five reconstructions would read as coverage the epic does not have. Flagged
for the owner as a decision, not quietly closed.

## Suggested next steps

1. **SI-19** — eval ladder 1/4. Ready: its dependencies (SI-13, SI-14) are done
   and merged. Its assignment must be re-rendered before dispatch; the one on
   #368 is stale in five fields.
2. Run the ladder **strictly one rung at a time**. The plan already enforces this
   (SI-19 → SI-20 → SI-21 → SI-22 → SI-23), and the reason is the owner's: a
   failing eval leads to a change, and a change invalidates the rungs already run.
3. Decide the **wave 11–15 review** question above.
