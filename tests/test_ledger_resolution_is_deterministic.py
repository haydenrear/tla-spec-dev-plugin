"""Which archived ledger you read must not depend on when you checked out.

`specs/desired_program_model/deferred_findings.yaml` is removed by a workflow
close, so both `scripts/disposition.py` and `examples/validation/scorecards/
score_tools.py` fall back to the archived copies under `specs/.history`. Both
ordered them by `(mtime, size, path)`.

Git does not preserve mtimes. So two checkouts of the SAME COMMIT resolved
different ledgers -- silently, because both answers are a real ledger:

    fresh extract of main : cut-the-apparatus-epic/closed-snapshot  (296 rows)
    working tree, same content: subtract-to-measure/ticket-005-SM-05 ( 88 rows)

Downstream, nine scorecard claims failed to resolve `filed_as = CL-03-DF-04`,
and five disposition tests asserted `88 > 200`. Those five were recorded as a
standing baseline waiting on #296 for an entire epic. They were waiting on a
`stat()` call.

`disposition.archived_ledgers`'s own docstring named the hazard -- "a
`git checkout` flattens mtimes, which is exactly when the tie-break is needed"
-- and sorted on mtime first anyway, so the size tie-break only applied to
files sharing a timestamp to the microsecond and in practice never ran.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import random
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts import disposition as D  # noqa: E402


def _score_tools():
    path = REPO_ROOT / "examples" / "validation" / "scorecards" / "score_tools.py"
    spec = importlib.util.spec_from_file_location("ledger_score_tools", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["ledger_score_tools"] = module
    spec.loader.exec_module(module)
    return module


def _shuffle_mtimes(paths, seed: int) -> None:
    rng = random.Random(seed)
    for path in paths:
        stamp = rng.uniform(1_600_000_000, 1_800_000_000)
        os.utime(path, (stamp, stamp))


def test_disposition_picks_the_same_ledger_whatever_the_mtimes(tmp_path) -> None:
    archives = D.archived_ledgers(REPO_ROOT)
    assert len(archives) >= 5, (
        f"only {len(archives)} archived ledgers found; this control would pass "
        "on a tree with nothing to disagree about"
    )

    # Copy, so the repository's own timestamps are never touched.
    # Staged under the shape the globs expect, or `archived_ledgers` finds
    # nothing and this control passes on an empty list -- the vacuity this
    # repository keeps catching in its own checks.
    staged = []
    for i, source in enumerate(archives):
        target = tmp_path / "specs" / ".history" / f"epic-{i}" / "closed-snapshot" / "deferred_findings.yaml"
        target.parent.mkdir(parents=True)
        target.write_bytes(source.read_bytes())
        staged.append(target)

    def best(paths):
        return max(paths, key=lambda p: sum(
            1 for line in p.read_text(encoding="utf-8").splitlines()
            if line.lstrip().startswith("- id:")
        ))

    fullest = best(staged)
    for seed in (1, 2, 3, 4, 5):
        _shuffle_mtimes(staged, seed)
        found = D.archived_ledgers(tmp_path)
        assert found, "the staged tree matched no archive glob, so nothing was compared"
        chosen = found[-1]
        assert chosen.read_bytes() == fullest.read_bytes(), (
            f"seed {seed}: the resolver picked a different ledger once the "
            "mtimes moved, so which findings this repository believes in "
            "depends on the order git happened to write files"
        )


def test_both_resolvers_agree_on_the_repositorys_ledger() -> None:
    """Two independent fallbacks, one answer.

    They are separate implementations of the same rule, and a reader who
    consults one and cites the other must not get a different set of findings.
    """
    # BS-08 (stale test, updated): this compared the ARCHIVE fallback of one
    # tool against `_ledger_path()` of the other, which returns the LIVE
    # ledger first. On `main` there is no live ledger so the two coincide; on
    # every open epic branch the live inbox exists and they cannot. The
    # property in this module's docstring is about the two FALLBACKS, so the
    # fallback is what is compared.
    from_disposition = D.archived_ledgers(REPO_ROOT)[-1]
    from_score_tools = _score_tools()._newest_archived_ledger()
    assert from_score_tools is not None
    assert from_disposition.read_bytes() == from_score_tools.read_bytes(), (
        f"disposition reads {from_disposition}\n"
        f"score_tools reads {from_score_tools}\n"
        "and they disagree about which findings exist"
    )
