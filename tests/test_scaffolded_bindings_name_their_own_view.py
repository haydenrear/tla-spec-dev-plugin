"""A ticket that edits its adapters must actually run them.

`open ticket` copies `case_adapters.toml` and `testgraph_bindings.yml` verbatim
into `specs/tickets/<id>/{current,desired}`. If those bindings name an adapter
module by a **view-qualified** dotted path — `specs.program_model.adapters:X` —
the name is resolved from the PROJECT ROOT and therefore means the accepted
baseline's adapters no matter which view was selected.

So a ticket that edits its own `adapters.py` **runs green without ever executing
it**: the corpus is the ticket's and the adapters are the baseline's. That is
the worst shape of green this project collects — not a missing test, but a
passing one that reports a validated change nothing ran.

Found by a real ticket agent, in `examples/agent_integration` round 001. It hit
the defect while implementing SL-1, filed it against the epic it was working as
`DEF-001` (severity major, with a reproduction and a blast radius), and its
suggested fix named this scaffold: *"consider the same in the tla-spec-dev
ticket scaffold so seeded bindings never point at another view."*

A bare `adapters:X` resolves against the SELECTED spec directory, which both
loaders put on the import path — `default_import_roots_for` adds the spec dir,
`enforce_external_channels` adds the bindings file's own directory. One
condition, asserted below because it is the half that would rot silently:
`default_import_roots_for` is skipped when `--import-root` is passed
explicitly, so a caller stating its own roots must include the spec directory.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

SKILL_ROOT = REPO_ROOT / "skills" / "spec-double-2"
#: Any dotted prefix naming a specific spec TREE. It is the `specs.<tree>.`
#: shape that is wrong, not the word `program_model`: `specs.current.adapters`
#: and `specs.desired_program_model.adapters` fail the same way, and a rule
#: written against one literal would miss the other two.
VIEW_QUALIFIED = re.compile(r"\bspecs\.[A-Za-z0-9_]+\.(adapters|internal_adapters|providers)\s*:")


def _onboard():
    path = SKILL_ROOT / "scripts" / "onboard_program_model.py"
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    try:
        spec = importlib.util.spec_from_file_location("onboard_program_model", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _binding_values(text: str) -> list[str]:
    """Only the VALUES of binding keys, never prose.

    The scaffold's own comments explain the hazard by quoting the wrong form,
    and a rule that scanned the whole file would flag the explanation of the
    defect as the defect. Keys are matched exactly, so a comment line — which
    begins with `#` — is never a value.
    """
    keys = ("adapter", "projector", "expected_projection", "assertion", "provider")
    values: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            continue
        if any(line.startswith(f"{key} =") or line.startswith(f"{key}:") for key in keys):
            values.append(line)
    return values


@pytest.mark.parametrize(
    "template",
    ["case_adapters_toml", "testgraph_bindings_yml"],
)
def test_the_scaffold_never_seeds_a_view_qualified_adapter_module(template: str) -> None:
    onboard = _onboard()
    text = getattr(onboard, template)()
    offenders = [line for line in _binding_values(text) if VIEW_QUALIFIED.search(line)]
    assert not offenders, (
        f"{template}() seeds bindings that name another view's adapter module:\n  "
        + "\n  ".join(offenders)
        + "\n`open ticket` copies these verbatim, so a ticket's own adapters.py is "
        "never imported and the ticket goes green without running the change it made."
    )


@pytest.mark.parametrize("template", ["case_adapters_toml", "testgraph_bindings_yml"])
def test_the_scaffold_still_binds_something(template: str) -> None:
    """Guard the guard: a template that stopped emitting bindings would pass above."""
    onboard = _onboard()
    text = getattr(onboard, template)()
    assert _binding_values(text), f"{template}() emits no binding values at all"


def _runner():
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    try:
        import run_generated_case_adapters  # type: ignore[import-not-found]

        return run_generated_case_adapters
    finally:
        sys.path.pop(0)


def test_the_selected_spec_directory_is_searched_FIRST_not_merely_present() -> None:
    """Membership was not enough, and asserting only membership hid a live hole.

    `ensure_import_roots` inserts each root at `sys.path[0]` in turn, so **the
    LAST root returned is the FIRST searched.** With `[cwd, spec_dir,
    project_root]` the resolved head was `[project_root, spec_dir, cwd]`, and a
    bare `adapters:X` -- the form `G-10` introduced so a view runs its OWN
    adapters -- imported `<project_root>/adapters` first.

    No example here has a top-level `adapters` package, so nothing was red. A
    project laid out ports-and-adapters, which is this repository's own
    doctrine, very plausibly does; there the bare name binds to the production
    package. **The same green that proves nothing, one directory over.** Found
    by review of `#317`, which is why this asserts ORDER.
    """
    runner = _runner()
    spec_dir = REPO_ROOT / "examples" / "distributed_history" / "specs" / "program_model"
    project_root = spec_dir.parents[1]
    roots = runner.default_import_roots_for(spec_dir)

    assert spec_dir in roots and project_root in roots, (
        "a root left the list; either bare bindings or view-qualified ones stop "
        f"resolving. roots={roots}"
    )
    # Simulate the reversal rather than describing it.
    path: list[str] = []
    for root in [REPO_ROOT, *roots]:
        resolved = str(root.resolve())
        if resolved not in path:
            path.insert(0, resolved)
    assert path[0] == str(spec_dir.resolve()), (
        "the selected spec directory is not the FIRST entry on the resolved "
        f"import path, so a bare `adapters:X` can bind elsewhere. head={path[:3]}"
    )


def test_a_bare_binding_resolves_to_the_TICKET_view_on_the_close_gate_path(tmp_path, monkeypatch) -> None:
    """The seam, not the string -- and on the path the close gate actually uses.

    The earlier pin asserted a property of `default_import_roots_for`, and
    `tla_spec_dev.py` passes `--import-root <target_dir>` explicitly on the
    ticket path, which SKIPS that function entirely. So the pin tested a
    function the defect's own code path never calls.

    This builds the two views `G-10` is about -- a baseline and a ticket copy,
    each with its own `adapters.py` -- and resolves through the mechanism the
    runner really uses, `ensure_import_roots` plus `importlib.import_module`.
    The bare name must yield the TICKET's module. The qualified name is shown
    yielding the baseline's, which is the defect, so this test carries its own
    demonstration of what it prevents.
    """
    import importlib

    runner = _runner()
    project = tmp_path / "proj"
    baseline = project / "specs" / "program_model"
    ticket = project / "specs" / "tickets" / "SL-1" / "current"
    for view, marker in ((baseline, "BASELINE"), (ticket, "TICKET")):
        view.mkdir(parents=True)
        (view / "adapters.py").write_text(f'WHICH_VIEW = "{marker}"\n', encoding="utf-8")
    (project / "specs" / "__init__.py").write_text("", encoding="utf-8")
    (project / "specs" / "program_model" / "__init__.py").write_text("", encoding="utf-8")

    saved_path, saved_modules = list(sys.path), dict(sys.modules)
    try:
        for name in [n for n in sys.modules if n == "adapters" or n.startswith("specs")]:
            del sys.modules[name]
        # Exactly what the close gate passes: the selected view, and nothing else.
        runner.ensure_import_roots([ticket])
        bare = importlib.import_module("adapters")
        assert bare.WHICH_VIEW == "TICKET", (
            "a bare `adapters:X` binding did not resolve to the selected view's "
            f"own adapters; it found {bare.WHICH_VIEW}. That is G-10: the ticket "
            "runs green over adapters it did not write."
        )

        # THE CONTRAST, so this test carries its own demonstration of what it
        # prevents rather than asserting only the good case. The qualified form
        # a pre-G-10 project still ships resolves from the project root, and
        # finds the BASELINE's adapters no matter which view was selected.
        sys.path.insert(0, str(project))
        qualified = importlib.import_module("specs.program_model.adapters")
        assert qualified.WHICH_VIEW == "BASELINE", (
            "the qualified form no longer reaches the baseline, so the defect "
            "this test contrasts against can no longer be demonstrated here"
        )
    finally:
        sys.path[:] = saved_path
        sys.modules.clear()
        sys.modules.update(saved_modules)


def test_opening_a_ticket_copies_the_project_binding_coordinates_verbatim(tmp_path, capsys) -> None:
    """DEF-507 (commit-diff-context-parent#388, owner decision 2026-10-04).

    `open ticket` used to strip `specs.program_model.adapters:X` to bare
    `adapters:X` in the ticket copy (G-10). `close ticket` then promoted the
    bare form into `specs/current`, and a project whose spec-unit requires the
    qualified form went red for the whole epic on one unnoticed close -- twice
    in commit-diff-context-parent. The project's coordinates are the project's:
    the ticket copy carries them byte for byte, qualified or bare.
    """
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from scripts.new_ticket_workflow import (  # type: ignore[import-not-found]
            copy_baseline_tree,
        )
    finally:
        sys.path.pop(0)

    src, dst = tmp_path / "program_model", tmp_path / "ticket_current"
    src.mkdir()
    qualified = (
        '[adapters.Reserve]\n'
        'adapter = "specs.program_model.adapters:ReserveInternalAdapter"\n'
        'kind = "shortlink-internal"\n'
    )
    bindings = (
        "bindings:\n"
        "  - adapter: specs.current.adapters:IndexPipelineModelAdapter\n"
        "  - adapter: adapters:BareAdapter\n"
    )
    (src / "case_adapters.toml").write_text(qualified, encoding="utf-8")
    (src / "testgraph_bindings.yml").write_text(bindings, encoding="utf-8")
    (src / "Internal.tla").write_text("---- MODULE Internal ----\n====\n", encoding="utf-8")

    copy_baseline_tree(src, dst, force=False, dry_run=False)

    assert (dst / "case_adapters.toml").read_text(encoding="utf-8") == qualified, (
        "the ticket copy rewrote the project's adapter coordinates; close ticket "
        "would promote the rewritten form over the project's own"
    )
    assert (dst / "testgraph_bindings.yml").read_text(encoding="utf-8") == bindings
    assert "un-rooted" not in capsys.readouterr().out
    assert (dst / "Internal.tla").read_text(encoding="utf-8").startswith("---- MODULE")
