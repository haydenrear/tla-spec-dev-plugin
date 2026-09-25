# /// script
# requires-python = ">=3.10"
# dependencies = ["testgraphsdk"]
#
# [tool.uv.sources]
# testgraphsdk = { path = "../sdk/python", editable = true }
# ///
"""`G-12`: the reference adapters must import where an adopter will run them.

`scaffold_spec.py` substitutes `SKILL_ROOT_BOOTSTRAP` into every `adapters.py`
it writes, because without it `from spec_double_compiler.runtime import ...`
resolves under no interpreter absent a hand-set `PYTHONPATH`.
`examples/distributed_history/specs/program_model/adapters.py` -- the file the
docs call the concrete reference implementation -- carried none of it, and an
agent copying adapter shape from it got a module that could not be imported.

**This node exists because the unit test for it was green for the wrong
reason.** It cleared `PYTHONPATH` and passed, and would have kept passing with
the bootstrap deleted, because this checkout sits under the operator's home
directory and the resolver's ancestor walk found `~/.skill-manager` whatever the
environment said. A property of the machine, asserted as a property of the
repository. The blind review of `#318` found it.

So the assertion is made where the environment cannot supply the answer: the
repository is copied into the node's own report directory, every variable the
resolver consults is stripped, `HOME` is pointed at an empty directory, and the
import is run from a neutral working directory in a subprocess.

Two directions, because either alone is satisfiable by an accident:

  * it must IMPORT with no Skill Manager home reachable at all -- the adopter's
    situation, and CI's;
  * it must import THE CHECKOUT, not an installed skill. `sys.path.insert(0,
    home)` used to outrank the repository under test, so the reference example
    inside this skill's own repo exercised a different build than the one being
    validated. That is the hazard the bootstrap's own docstring warns about,
    produced by the bootstrap.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from testgraphsdk import NodeResult, NodeSpec, node, procs

SPEC = (
    NodeSpec("spec.reference.adapters_resolve")
    .kind("assertion")
    .tags("spec-workflow", "reference")
    .timeout("300s")
)

#: Everything the resolver consults, removed so the checkout is the only answer.
STRIPPED = ("SPEC_DOUBLE_COMPILER_HOME", "SKILL_MANAGER_HOME", "PYTHONPATH")

RELATIVE_ADAPTERS = "examples/distributed_history/specs/program_model/adapters.py"


def _probe(target: Path) -> str:
    return (
        "import sys, importlib.util as u;"
        f"sys.path.insert(0, {str(target.parents[2])!r});"
        f"spec = u.spec_from_file_location('ref_adapters', {str(target)!r});"
        "m = u.module_from_spec(spec); spec.loader.exec_module(m);"
        "import spec_double_compiler as sdc;"
        "print('RESOLVED', sdc.__file__)"
    )


@node(SPEC)
def main(ctx):
    repo = Path(__file__).resolve().parents[2]
    result = NodeResult.pass_(SPEC.id)

    # OUTSIDE THE REPOSITORY, and removed afterwards.
    #
    # The first version copied the checkout into `ctx.report_dir`, which lives
    # under `test_graph/build/`. Two repository-scanning tests then found the
    # duplicate and reported the scorecard stated in eleven places it should not
    # be -- `test_card_has_one_home` and `test_prediction_seal`, both green
    # before this node existed. **A validation that leaves a second copy of the
    # repository inside the repository breaks every check that reads the tree**,
    # which is `E-13`'s lesson and `H-03`'s, arriving a third time.
    scratch = Path(tempfile.mkdtemp(prefix="reference-adapters-resolve-"))
    checkout = scratch / "checkout"
    # `.toolchain` and `.history` added to the ignore list on 2026-09-25.
    # `symlinks=True` was ALREADY here and is what kept this copier safe: the
    # sibling node skt_wrapper_installed.py lacked it, dereferenced a scratch
    # eval home's links into the operator's home, and wrote a 57 GB fixture that
    # took a 926 GB disk to 532 MB free. This one only ever copied the
    # .toolchain BULK -- a pinned checkout and caches, never plugin content and
    # no business in a fixture -- which is worth not copying on its own.
    shutil.copytree(
        repo, checkout,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".skill-manager", "build", ".gradle",
            "evidence", "node_modules", ".venv", ".toolchain", ".history",
        ),
        symlinks=True,
    )
    target = checkout / RELATIVE_ADAPTERS
    result.assertion("the copied checkout holds the reference adapters", target.is_file())
    if not target.is_file():
        shutil.rmtree(scratch, ignore_errors=True)
        return result

    env = {k: v for k, v in os.environ.items() if k not in STRIPPED}
    empty_home = ctx.report_dir / "empty-home"
    empty_home.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(empty_home)

    detached = procs.run(
        ctx, "import-with-no-home", ["python3", "-c", _probe(target)],
        cwd=str(ctx.report_dir), env=env,
    )
    result.process(detached).assertion(
        "the reference adapters import with no Skill Manager home reachable",
        detached.exit_code == 0,
    )
    output = ""
    if detached.log_path:
        output = (ctx.report_dir / detached.log_path).read_text(encoding="utf-8")
    result.assertion(
        "and they import from the checkout under test, not an installed skill",
        str(checkout) in output,
    )

    # The second direction, against the REAL checkout rather than the copy: an
    # installed skill is reachable here, and must still lose.
    in_repo = procs.run(
        ctx, "import-prefers-the-checkout",
        ["python3", "-c", _probe(repo / RELATIVE_ADAPTERS)],
        cwd=str(ctx.report_dir),
        env={k: v for k, v in os.environ.items() if k != "SKILL_MANAGER_HOME"},
    )
    result.process(in_repo).assertion(
        "importing from this repository resolves spec_double_compiler at all",
        in_repo.exit_code == 0,
    )
    repo_output = ""
    if in_repo.log_path:
        repo_output = (ctx.report_dir / in_repo.log_path).read_text(encoding="utf-8")
    result.assertion(
        "the checkout outranks any installed spec-double-compiler",
        str(repo) in repo_output and ".skill-manager" not in repo_output,
    )
    shutil.rmtree(scratch, ignore_errors=True)
    return result


if __name__ == "__main__":
    main()
