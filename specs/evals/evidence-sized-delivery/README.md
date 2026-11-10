# ESD-06 uptake cases (GOAL-ESD-UPTAKE evidence root)

Five declarative cases under `cases/`, in exactly the format of `evals/<skill>/<case>/`
(`case.yaml` + `graders/*.md`). They are measurement data for #240, not part of the
shipped suite: they live outside `evals/` because the existing hooks dispatch on
`EVAL_CASE` and a new name under `evals/` would need new dispatch code
(see `specs/results/evidence-sized-delivery/ESD-06/declaration.md`).

Run (from either arm's checkout, the cases must be in that checkout's HEAD):

    evals/run.sh --case <name> --eval-dir specs/evals/evidence-sized-delivery/cases --json <out>

Results are filled in below after the runs.
