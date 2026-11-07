"""Every executable and every binding must find the toolchain under the plugin layout.

SI-02 nested five workflow skills plus test-graph into this repository as
CONTAINED SKILLS of the `tla-spec-dev` plugin. A contained skill's bytes land at
``<home>/plugins/<plugin>/skills/<skill>/`` — never at ``<home>/skills/<skill>/``,
which is where a standalone install used to put them and where most of this
repository's executables were written to look.

The reason this needs a test rather than a one-time sweep is that **every failure
in this class is silent**. A stale path does not raise: it resolves to nothing, a
loop finds no candidate, a `-d` test is false, and the caller takes its fallback
and reports success. SI-11 found three of them — `github-action.py` pinning
`TEST_GRAPH_SKILL_HOME` to the standalone rung, `provider-bindings.json` naming a
provider inside the gitignored home, and a `[[vendored]]` block whose declared
source could not exist — and not one of them had ever failed anything.

So the assertions here are about the SHAPE of resolution, not about whether a
particular run happened to work on the machine it ran on:

1. An executable that names the standalone rung for a skill this bundle contains
   must also name the plugin rung for that same skill. Two-rung resolution is the
   fix; a file carrying only rung one is the defect, whatever it resolves to
   today on a home that still has the retired standalone copy installed.
2. The Test Graph provider binding must bind to the test-graph skill installed
   in the Skill Manager home (``skill-root`` only), not the in-repo source.

Both read tracked files only. Neither needs a home, a network, or an install, and
neither refuses: they are pytest assertions, so a violation is a reported failure
with the offending path quoted — there is no `sys.exit`, no non-zero process exit
of our own, and nothing here can block a promotion (GOAL-no-new-gates).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"

# Directories inside an executable tree whose contents are deliberately wrong.
# Test fixtures plant malformed paths on purpose — `test_provider_bindings.py`
# carries a misspelled `../.skill-manger/skills/test-graph` precisely so the
# loader's rejection can be observed — and scanning them would make this test
# fail on data whose whole job is to be invalid.
EXCLUDED_DIR_NAMES = {"tests", "__pycache__", ".pytest_cache"}

EXECUTABLE_SUFFIXES = {".py", ".sh", ".bash"}


def _contained_skills() -> list[str]:
    """The skills this repository ships as contained skills of the plugin."""
    return sorted(
        path.name
        for path in SKILLS_DIR.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def _executables() -> list[Path]:
    """Tracked executables in the bundle's script trees, fixtures excluded."""
    out: list[Path] = []
    roots = [SKILLS_DIR.glob("*/scripts"), SKILLS_DIR.glob("*/skill-scripts")]
    roots.append(iter([ROOT / "skill-scripts"]))
    for group in roots:
        for scripts_dir in group:
            if not scripts_dir.is_dir():
                continue
            for path in scripts_dir.rglob("*"):
                if not path.is_file() or path.suffix not in EXECUTABLE_SUFFIXES:
                    continue
                if EXCLUDED_DIR_NAMES & set(path.relative_to(scripts_dir).parts):
                    continue
                out.append(path)
    return sorted(out)


# A rung is only a rung when it is anchored on a HOME. `/skills/<skill>` on its
# own is not enough, and getting that wrong is not hypothetical: the first draft
# of this test flagged
#
#     ENTRYPOINT="$SKILL_DIR/skills/spec-double-2/scripts/tla_spec_dev.py"
#
# in skill-scripts/install-tla-spec-dev.sh, which is CORRECT — on the plugin rung
# skill-manager sets SKILL_DIR to the plugin root, so that path is inside the
# bundle and never touches a home at all. Requiring a home anchor is what
# separates "resolving a unit out of a home" from "walking the bundle's own tree".
_HOME_ANCHOR = r"(?:SKILL_MANAGER_HOME|ACTIVE_HOME|\.skill-manager|<home>)"


def _rung_patterns(skill: str) -> tuple[re.Pattern[str], re.Pattern[str]]:
    """Standalone and plugin rung spellings for one contained skill.

    Both are matched from a home anchor, with anything non-whitespace allowed in
    between so the many legitimate spellings all count: a closing quote
    (``"$ACTIVE_HOME"/plugins/*/skills/x``), a glob segment, or a literal plugin
    name (``.skill-manager/plugins/tla-spec-dev/skills/x``). The standalone
    pattern deliberately also matches a plugin rung — the assertion is only ever
    "if a standalone rung is present, a plugin rung must be too", so over-matching
    there costs nothing and under-matching the PLUGIN rung would raise a false
    alarm, which is the expensive direction.
    """
    name = re.escape(skill)
    standalone = re.compile(rf"{_HOME_ANCHOR}\S*?/skills/{name}(?![-\w])")
    plugin = re.compile(rf"{_HOME_ANCHOR}\S*?/plugins/[^/\s]*/skills/{name}(?![-\w])")
    return standalone, plugin


@pytest.mark.parametrize("skill", _contained_skills())
def test_no_executable_carries_a_standalone_only_rung(skill: str) -> None:
    """A file naming ``<home>/skills/<skill>`` must also name the plugin rung.

    This is the regression guard SI-11 exists to leave behind. It fails when an
    executable GAINS a standalone-only rung — the exact edit that produced
    `github-action.py:320`, which sat there through a 413-executable audit
    because nothing it broke was loud.
    """
    standalone, plugin = _rung_patterns(skill)
    offenders: list[str] = []

    for path in _executables():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not standalone.search(text):
            continue
        if plugin.search(text):
            continue
        hits = [
            f"    {path.relative_to(ROOT)}:{n}: {line.strip()}"
            for n, line in enumerate(text.splitlines(), 1)
            if standalone.search(line)
        ]
        offenders.append(
            f"  {path.relative_to(ROOT)} names /skills/{skill} with no "
            f"plugins/*/skills/{skill} rung:\n" + "\n".join(hits)
        )

    assert not offenders, (
        f"{len(offenders)} executable(s) resolve the contained skill {skill!r} at "
        "the standalone rung only.\n"
        "A contained skill's bytes are at <home>/plugins/<plugin>/skills/"
        f"{skill}/, so this resolves to nothing in any home that installed the\n"
        "bundle as a plugin — and resolves to a RETIRED standalone copy in a home\n"
        "that predates the migration, which is why it can look fine locally.\n"
        "Add the plugin rung beside the standalone one. Two idioms that do not\n"
        "work, both measured in wave 2: brace expansion does not happen inside\n"
        'double quotes ("$HOME"/{skills,plugins/*/skills}/x matches nothing), and\n'
        "`ls -d ... | head -1` sorts, putting plugins/ first and inverting the\n"
        "intended standalone-first precedence. Use an explicit loop with `break`,\n"
        "the form skills/git-issue-workflow/scripts/agent-home.sh already uses.\n\n"
        + "\n".join(offenders)
    )


def test_test_graph_provider_binding_uses_the_installed_skill() -> None:
    """``provider-bindings.json`` must bind to the INSTALLED test-graph skill.

    The graphs run against the test-graph skill contained in the tla-spec-dev
    plugin installed in this checkout's Skill Manager home, not the in-repo
    ``skills/test-graph`` source (owner decision, 2026-11-04). So the manifest
    declares only the ``skill-root`` candidate: no ``workspace-relative`` path
    back into the working tree, which would win first and silently re-vendor
    the SDK. The runner front door (``test_graph/run-graphs.py``) supplies the
    other half, by invoking the home's copy of the skill scripts.
    """
    manifest_path = ROOT / "test_graph" / "provider-bindings.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    kinds = [candidate.get("kind") for candidate in manifest["provider_candidates"]]
    assert kinds == ["skill-root"], (
        "provider-bindings.json must declare exactly one candidate, `skill-root`, "
        f"so the SDK comes from the installed skill; got {manifest['provider_candidates']!r}"
    )


def test_run_graphs_front_door_never_resolves_the_in_repo_runner() -> None:
    """``run-graphs.py`` must look for the runner inside a home, never in ``skills/``.

    With only a ``skill-root`` candidate, the runner that executes decides the
    provider; a fallback to ``skills/test-graph/scripts/run.py`` would bind the
    graphs back to the working-tree copy with a green exit.
    """
    source = (ROOT / "test_graph" / "run-graphs.py").read_text(encoding="utf-8")
    body = source[source.index("def skill_runner"):source.index("def prepare_bindings")]
    assert 'REPO_ROOT / "skills"' not in body, body
    assert '"plugins"' in body and '"tla-spec-dev"' in body, body
