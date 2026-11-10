# BS-20 model result: no-op

specs/current is unchanged. BS-20 changes how `skt build` classifies and reports
a run the CLI exits 1 for: every attempted artifact was produced, and each is
still stale only because of a stale ancestor that `build` has no producer for.
That is a `skt` front-end reporting change (`skills/skt/src/skt/artifacts.py`,
`build_cmd.py`); no Internal.tla or External.tla action, variable or invariant
describes `skt build`'s exit codes or the artifact-freshness ledger, so there is
no model delta. Per the epic's model-ownership rule no open/close ticket,
close_tickets.py or --accept-new was run; the epic agent owns the close.

Evidence in this directory:
- regression-red-on-base.txt      (10 failed: new tests vs origin/epic/bug-sweep sources)
- regression-green-on-branch.txt  (10 passed)
- repository-unit.txt             (local_signal and the targeted repository_unit subset)
- real_fixture.sh                 (finite one-unit fixture home, real skill-manager 0.28.2)
- real-fixture-base.txt           (base skt: exit 1 twice, everything stale, no remedy)
- real-fixture-branch.txt         (branch skt: exit 4 unresolved-ancestor twice, names
                                   unit-store:fixa and `skill-manager sync fixa`; after the
                                   sync, nothing stale, exit 0)
- real-fixture-branch-json/       (the two --json documents from the branch runs)
- sktHooks graph result           (see sktHooks.txt)
