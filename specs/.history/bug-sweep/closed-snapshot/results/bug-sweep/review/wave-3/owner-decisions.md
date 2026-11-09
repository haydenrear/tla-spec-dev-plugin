# Owner decisions at the wave-3 milestone review (2026-11-07)

1. **Go ahead** with the recommended defaults:
   - `tests/test_architecture_tags.py::test_the_same_tag_control_holds` stays **deliberately red** (BS-08-DF-02, RM-06-DF-01). GOAL-BS-SUITE is reported as 0 failures plus this one named exception, never by editing the target.
   - All other deferred findings stay batched for a successor epic.
2. **Home close-out allowed.** The epic agent ran `skill-manager home close-out --home <wt>/.skill-manager --into <repo>/.skill-manager` (a read-only gate) for all 19 ticket worktree homes. All 19 returned rc=0, "holds nothing that removing it would destroy". The per-worktree output is in `home-close-out/`. This settles BS-03-DF-02 and BS-05-DF-03 for this epic. The classifier block on ticket agents is still a machinery finding.
3. **Evaluation on hold.** BS-16, BS-17 and BS-18 wait for the incoming skill-manager bug epic to land and for the homes to be upgraded to that skill-manager version. The evals then run on the new version, against the same base 68922587.
