# BS-17: eval lane, base 68922587 vs tip 8655e008 (skill-manager 0.29.0)

Run staggered, one case at a time, on 2026-11-08. `tip.json` is one run per case;
`compare.json` is base vs tip, three runs each, for the eight unsettled cases.

| Result on tip (74 cases) | Count |
| --- | --- |
| Passed | 53 |
| Undecided: the fixture needs a real home | 6 |
| Failed | 15 |

Failed, explained without a comparison (7): w-misc-otlp-endpoint-native-runner
(skill not in this plugin); epic-mode-is-not-main (grader false negative);
w-epic-force-when-owner-decided, w-skt-check-record-disagrees-with-checkout,
w-skt-ticket-new-needs-a-project-home (over tool-call budget only);
w-giw-wt-refusal-quotes-subject (sandbox; same score with base skt);
w-sdc-complexity-ledger-is-advisory (case ships no fixture).

Base vs tip, three runs each:

| Case | Base | Tip |
| --- | --- | --- |
| w-sdc-ticket-binding-bare-adapter-module | .17 .17 .17 | .17 .17 .17 |
| w-sm-sync-skt-when-absent | .25 .25 .25 | 1 1 1 |
| w-sm-verify-is-not-currency | .33 .5 .5 | .5 .5 .5 |
| w-skt-migration-delete-project-block | 1 1 1 | 1 1 1 |
| catch-the-drift | .8 .8 .8 | .8 .2 .6, then .6 1 .8 |
| w-roles-propagation-is-checkable | 1 .5 .5 | .92 1 .58 |
| w-sdc-effect-conformance-observed-nothing | .78 1 .78 | .78 1 .78 |
| w-sdc-scorecard-tool-needs-a-newer-python | .44 1 .67 | 1 .78 .67 |

GOAL-BS-EVALS verdict: no case shows a clear regression. catch-the-drift is
inconclusive (mean .67 over six tip runs vs .80 over three base runs).

Caveats. Passes outside the git-issue-workflow group were recorded before the
`evals/bin/skt` shim; those eight git-issue-workflow cases were voided and rerun,
the rest carried forward. Only the eight cases above have a base measurement, so
the 53 passes are tip-only. Single runs are noisy (see evals/README). The six
undecided cases are unmeasured.
