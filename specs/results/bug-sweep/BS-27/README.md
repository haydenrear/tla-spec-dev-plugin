# BS-27 evidence

`base-red/` and `branch-green/` hold the `--result-out` JSON of the two skill-manager
v0.29.0 nodes (`SkillManagerSkillDocsProjected`, `OnboardingDocsAndScriptsStatic`),
run unmodified by jbang through `run-nodes.sh`.

- Base: `git archive origin/epic/bug-sweep skills` at baf5facc.
- Branch: this worktree. Both were placed at `<home>/plugins/tla-spec-dev`, the
  installed shape: the node finds `wt` in a sibling skill only when the path is
  `<home>/plugins/<plugin>/skills/<skill>/scripts`. Run straight against the checkout
  it reports `missing=[wt]`; that is the harness layout, not the docs.

`wt-extractor-trace.txt` calls the node's own `SCRIPT_REF` and `claimsOwnScriptsDir`
on each `scripts/wt` occurrence (`TraceWt.java`).

These are single-node runs, not `doc-smoke` / `onboarding` graph runs; upstream
nodes were not executed.

`local-signal.txt`: `pytest tests -q -x --lf` stopped at its first failure, so it
does not say anything about the rest of the suite. The saved file is the second
run, where `--lf` re-ran only that failure (1 failed); the first run on this tree
reported 1 failed, 178 passed, on the same test, which the baseline README lists
as already failing at 350b9ab4.
