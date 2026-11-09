# BS-15 evidence (#148, #147 closure-census step)

| File | What it shows |
|---|---|
| red-on-base.txt | The new tests run on origin/epic/bug-sweep 1262f7e6: 4/4 close-ticket tests fail, 17/17 census tests fail (census.py absent). |
| green-on-branch.txt | The same tests on the branch: 4 + 17 pass. |
| green-after-merge.txt | After merging origin/epic/bug-sweep abfcbc3c: 5 close tests (adds the no-PyYAML case) + 212 git-epic-workflow tests pass. |
| repository-unit-tests.txt / -base.txt | Local signal `pytest tests -k 'deferred or census or ledger'`: the same 8 failed + 2 errors on base and branch (pre-existing, BS-08's); branch +4 passed. |
| spec-unit.txt | `pytest specs/current/tests`: 11 failed, identical to baseline/spec-unit-failures.txt. |
| census-on-bug-sweep-backlogs.txt | The census on this epic's real per-ticket backlogs: no ledger, so exit 2; on a scratch copy, init + absorb takes 32 rows and passes. |
| specworkflow.txt | specWorkflow graph verdict. |

Model result: no-op. specs/current is unchanged. BS-15 is tooling (a new
script plus a close-ticket side effect on a results file) and adds no model
action. No open/close ticket, close_tickets.py or --accept-new was run against
this repository's workflow; the close tests run in temp dirs.
