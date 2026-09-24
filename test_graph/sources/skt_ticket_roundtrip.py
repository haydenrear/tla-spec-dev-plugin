# /// script
# requires-python = ">=3.10"
# dependencies = ["testgraphsdk"]
#
# [tool.uv.sources]
# testgraphsdk = { path = "../sdk/python", editable = true }
# ///
"""skt.ticket-roundtrip — a worktree created and torn down for real.

`skt ticket new|info|close` is the lifecycle skt puts its name on. Since
SI-17 it SHIPS `wt` and the typed Python surface over it; what it still
imports across units is the lifecycle `wt` delegates to, which is
git-issue-workflow's `lib.sh` / `new-change.sh` / `close-change.sh`.
Two things follow, and only an end-to-end run reaches either:

  * the ROUND TRIP. `new` must produce a real linked worktree on a real
    branch, `info` must answer about that same worktree, and `close`
    must remove the directory while KEEPING the branch. Every one of
    those is a fact about a filesystem and a git object store.

  * the REFUSALS. When the git-issue-workflow lifecycle is unreachable,
    skt names the remedy that fits THIS home — and telling the four
    cases apart was itself a merged fix (`fix(ticket): tell
    not-installed from not-synced, and name a remedy that runs`, #25),
    landed because `sync` was being prescribed for a unit that was not
    installed, in five different homes. A remedy that cannot run is
    worse than no remedy: it costs the agent a failed command and a
    wrong mental model.

`INTEGRATION_SKIP_HOME=1` is exported for the round trip. That is
new-change.sh's own documented switch, and it draws the node's boundary
honestly in both directions: provisioning a per-worktree Skill Manager
home needs a `skill-manager` binary plus a source home to clone from,
which is a skill-manager claim and not an skt one, so it is left out
rather than faked.

WHAT THIS NODE THEREFORE DOES NOT COVER, stated so the gap is not
mistaken for coverage: `skt ticket close` also carries a GATE that
refuses while the worktree's home holds unpublished skill edits
(`publish.edited_units` + `wt close`). With no home there is nothing for
that gate to inspect, so it is neither exercised nor asserted here.
Covering it needs a `skill-manager` on PATH and a source home, which is
a CI dependency this graph deliberately does not take on.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from testgraphsdk import NodeResult, NodeSpec, node

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "support"))
from skt_fixture import (  # noqa: E402
    REPO_ROOT,
    build_home,
    child_env,
    git,
    init_repo,
    unit_record,
)

UPSTREAM = "skt.wrapper-installed"
GIW_REMOTE = "https://github.com/haydenrear/git-issue-workflow-skill.git"

SPEC = (
    NodeSpec("skt.ticket-roundtrip")
    .kind("assertion")
    .depends_on(UPSTREAM)
    .tags("skt", "ticket", "lifecycle")
    .timeout("900s")
    .side_effects("fs:tmp", "net:external")
    .output("giwSource", "string")
)


def _resolve_giw(workdir: Path) -> tuple[Path, str]:
    """The git-issue-workflow unit this node drives, and where it came from.

    An installed copy is preferred because it needs no network; the clone
    is the fallback a hosted runner takes. WHICH ONE was used is
    published, because "the round trip passed" means a different thing
    against a working copy than against the pushed main.
    """
    override = os.environ.get("SKT_TG_GIW")
    if override:
        return Path(override), f"SKT_TG_GIW={override}"
    for base in (os.environ.get("SKILL_MANAGER_HOME"), str(Path.home() / ".skill-manager")):
        if not base:
            continue
        # BOTH RUNGS, and the second one is why this node went red on
        # 2026-09-23. A unit installed STANDALONE lives at
        # `<home>/skills/<unit>`; a unit CONTAINED in a plugin lives at
        # `<home>/plugins/*/skills/<unit>`. git-issue-workflow is contained in
        # the tla-spec-dev plugin now and is absent from the standalone rung in
        # every home, so a single-rung search finds nothing, falls through, and
        # clones GIW_REMOTE — a DIFFERENT, archived repository. The node then
        # tests upstream main instead of the code under review, and the
        # dangerous outcome is not this red: it is the green it would report
        # when the clone succeeds. Filed as SI-25-DF-06 and left unrepaired
        # until it actually broke something.
        for candidate in [
            Path(base) / "skills" / "git-issue-workflow",
            *sorted((Path(base) / "plugins").glob("*/skills/git-issue-workflow")),
        ]:
            # SI-17: `wt` and `wt.py` are skt's now, so neither is evidence that
            # THIS unit is usable. What makes it usable is the lifecycle `wt`
            # delegates to, and lib.sh is the file every one of those scripts
            # sources first — so it is the honest probe.
            if (candidate / "scripts" / "lib.sh").is_file() and (
                candidate / "scripts" / "new-change.sh"
            ).is_file():
                return candidate, f"installed:{candidate}"
    target = workdir / "git-issue-workflow"
    if not target.exists():
        clone = subprocess.run(
            ["git", "clone", "--depth", "1", GIW_REMOTE, str(target)],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if clone.returncode != 0:
            raise RuntimeError(f"git clone {GIW_REMOTE} failed: {clone.stderr.strip()[:400]}")
    return target, f"clone:{GIW_REMOTE}"


def _skt(wrapper: str, args: list[str], *, cwd: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [wrapper, *args], cwd=str(cwd), capture_output=True, text=True, timeout=600, env=env
    )


def _remedy_scripts(blob: str) -> list[Path]:
    """Every absolute script path a refusal offers as its `fix:`.

    A remedy is scored on whether it RUNS, not on its wording, so the path has
    to come out of the text. Only absolute paths are taken: a relative one is
    ambiguous about which directory it is relative to, and that ambiguity is
    itself something a remedy should not have.
    """
    found: list[Path] = []
    for line in blob.splitlines():
        stripped = line.strip()
        if not stripped.startswith("fix:"):
            continue
        for token in re.findall(r"/[^\s]+", stripped):
            candidate = Path(token)
            if candidate.name.endswith(".sh") or candidate.name == "wt":
                if candidate not in found:
                    found.append(candidate)
    return found


def _arm(result, wrapper: str, version: str, repo: Path, wt_parent: Path,
         work: Path, label: str, env: dict) -> bool:
    """One placement classification, new -> info -> close, asserted throughout.

    Returns False when `ticket new` refused, so the caller can hand back the
    ACCUMULATED result rather than a bare fail(): NodeResult.fail builds a
    fresh object and every assertion gathered so far would be dropped.
    """
    ticket = f"TG-{label.upper()[:4]}"
    expected = wt_parent / f"{repo.name}-{ticket}"
    created = _skt(wrapper, ["ticket", "new", ticket], cwd=repo, env=env)
    result.assertion(f"{version}/{label}: ticket new exits zero", created.returncode == 0)
    if created.returncode != 0:
        result.log(f"{label} stdout: {created.stdout[-1200:]}")
        result.log(f"{label} stderr: {created.stderr[-1200:]}")
        return False
    contract = _contract(created.stdout)
    # LOG THE CONTRACT ON SUCCESS TOO. stdout was logged only on a non-zero
    # exit, so the case that actually happened -- exit 0 with the worktree
    # somewhere other than expected -- produced red assertions and NO record of
    # what the command printed, and the next reader had to reproduce it by hand
    # before they could start.
    result.log(f"{label}: ticket new contract: {contract}")
    result.log(f"{label}: expected worktree: {expected.resolve()}")
    result.log(f"{label}: worktree exists: {expected.is_dir()}")
    result.assertion(
        f"{label}: new prints the worktree and branch keys",
        contract.get("worktree") == str(expected.resolve())
        and contract.get("branch", "").startswith(f"feature/{ticket}"),
    )
    # THE CLASSIFICATION IS ASSERTED, NOT INFERRED FROM THE PATH. `new` prints
    # it in the branch key, and a fixture that silently changed classification
    # would otherwise make BOTH arms measure the same rule.
    result.assertion(
        f"{label}: new says which classification decided the location",
        f"{label} repo" in contract.get("branch", ""),
    )
    # THE ASSERTION THAT WAS MISSING (SI-20-DF-01). This node declares
    # `side_effects("fs:tmp")`. Nothing checked it, and for as long as the
    # fixture sat under `report_dir` -- inside an integration repo -- every run
    # created a real linked worktree in the OPERATOR'S checkout directory. A
    # path assertion against one expected location cannot catch that: it just
    # goes red, and red about `skt`.
    result.assertion(
        f"{label}: the worktree skt created is inside THIS NODE'S fixture tree",
        _inside(Path(contract.get("worktree", "/nowhere")), work),
    )
    # CHECKED WHILE IT IS STANDING, not after `close`. The same sweep at the
    # end of the node would pass on a leak that `close` then tidied away --
    # and tidying away is exactly what happened: the worktree WAS created in
    # the operator's directory and WAS removed again, so only a check taken
    # between `new` and `close` can see it.
    strays = sorted(str(c) for c in Path(REPO_ROOT).parent.glob(f"*-{ticket}"))
    if strays:
        result.log(f"{label}: STRAY beside the repository under test: {strays}")
    result.assertion(
        f"{label}: nothing was created beside the repository under test", not strays
    )
    result.assertion(
        f"{label}: new names its own close command",
        contract.get("close", "").startswith("skt ticket close"),
    )
    result.assertion(
        f"{label}: new warns that home-side skill edits are in no git diff",
        "no git diff" in created.stdout and "skt publish" in created.stdout,
    )
    result.assertion(f"{label}: the worktree directory exists", expected.is_dir())
    result.assertion(
        f"{label}: it is a LINKED worktree, not a copy", (expected / ".git").is_file()
    )
    listing = git("worktree", "list", "--porcelain", cwd=repo).stdout
    result.assertion(
        f"{label}: git knows about it",
        str(expected.resolve()) in listing.replace("/private", "")
        or str(expected.resolve()) in listing,
    )
    branches = git("branch", "--list", "--format=%(refname:short)", cwd=repo).stdout.split()
    result.assertion(f"{label}: the branch feature/{ticket} exists", f"feature/{ticket}" in branches)

    info = _skt(wrapper, ["ticket", "info", ticket], cwd=repo, env=env)
    info_keys = _contract(info.stdout)
    result.assertion(
        f"{label}: info answers about the same worktree",
        info.returncode == 0 and info_keys.get("worktree") == contract.get("worktree"),
    )
    result.assertion(
        f"{label}: info reports the worktree's base against its parent",
        "in sync with parent" in info.stdout,
    )

    closed = _skt(wrapper, ["ticket", "close", ticket], cwd=repo, env=env)
    result.assertion(f"{version}/{label}: ticket close exits zero", closed.returncode == 0)
    if closed.returncode != 0:
        result.log(f"{label} close stdout: {closed.stdout[-800:]}")
        result.log(f"{label} close stderr: {closed.stderr[-800:]}")
    result.assertion(f"{label}: close removes the worktree directory", not expected.exists())
    after = git("worktree", "list", "--porcelain", cwd=repo).stdout
    result.assertion(f"{label}: git no longer lists it", f"{repo.name}-{ticket}" not in after)
    branches_after = git("branch", "--list", "--format=%(refname:short)", cwd=repo).stdout.split()
    result.assertion(
        f"{label}: close KEEPS the branch \u2014 the work is not what is being torn down",
        f"feature/{ticket}" in branches_after,
    )
    result.assertion(f"{label}: close says the branch was kept", "kept" in closed.stdout)
    return True


def _inside(path: Path, ancestor: Path) -> bool:
    try:
        path.resolve().relative_to(ancestor.resolve())
        return True
    except (ValueError, OSError):
        return False


@node(SPEC)
def main(ctx):
    result = NodeResult.pass_(ctx.node_id)
    wrappers = json.loads(ctx.get(UPSTREAM, "wrappers") or "{}")
    if not wrappers:
        return NodeResult.fail(ctx.node_id, f"{UPSTREAM} published no wrappers")
    # One interpreter is enough here: the lifecycle is git and shell, and
    # the matrix claim is already carried by the nodes that read state.
    version, wrapper = sorted(wrappers.items())[0]

    # The clone is kept OUT of the wiped tree so a rerun does not re-fetch
    # it; everything else is rebuilt from scratch, because a `git worktree
    # add` for a branch a previous attempt already created fails, and a
    # node that only passes on a clean report directory is a node that
    # cannot be rerun. (Measured: the second run of this node in the same
    # reportDir failed for exactly that reason.)
    cache = ctx.report_dir / "fixtures" / "giw-source"
    cache.mkdir(parents=True, exist_ok=True)
    # THE FIXTURE TREE LEAVES THE REPORT DIRECTORY, and that is a repair, not a
    # tidy-up. `report_dir` is inside THIS repository; this repository carries
    # `integration.toml` at its root; and a ticket worktree goes beside the
    # OUTERMOST enclosing integration repo. So every `skt ticket new` driven
    # from a fixture under `report_dir` created a real linked worktree in the
    # OPERATOR'S checkout directory, beside their live work, while this node
    # declared `side_effects("fs:tmp")`. It was removed again only because
    # `close` resolves by search; a run interrupted between the two left it
    # standing. Measured by hand in SI-20 (the epic's `EA-DF-02`, filed as
    # `SI-20-DF-01`), and the containment assertion that was missing is below.
    work = Path(tempfile.mkdtemp(prefix="skt-ticket-roundtrip-"))
    result.log(f"fixture root, OUTSIDE the repository on purpose: {work}")
    try:
        giw, source = _resolve_giw(cache)
    except RuntimeError as exc:
        return NodeResult.fail(ctx.node_id, str(exc))
    result.log(f"git-issue-workflow from {source}")
    # THE SOURCE WAS LOGGED AND NEVER ASSERTED, which is why a single-rung
    # resolver could silently test a DIFFERENT repository for as long as it did
    # (SI-25-DF-06). A log is read by whoever already suspects something. Assert
    # it, so the fallback cannot pass quietly: when a local install exists, using
    # the upstream clone instead means the round trip is measuring upstream main
    # rather than the code under review, and "passed" would name the wrong code.
    allow_clone = os.environ.get("SKT_TG_ALLOW_CLONE") == "1"
    if not (source.startswith("installed:") or source.startswith("SKT_TG_GIW=") or allow_clone):
        result.log(
            f"RESOLVED {source} WHILE A LOCAL INSTALL WAS EXPECTED. A contained unit "
            f"lives at <home>/plugins/*/skills/<unit>, not only <home>/skills/<unit>. "
            f"Set SKT_TG_ALLOW_CLONE=1 on a hosted runner that genuinely has no home."
        )
    result.assertion(
        "git-issue-workflow resolved to a local install, not an upstream clone",
        source.startswith("installed:") or source.startswith("SKT_TG_GIW=") or allow_clone,
    )
    # metric() takes a number; the source string stays in the log above.
    result.metric("giwResolvedLocally", 1 if source.startswith(("installed:", "SKT_TG_GIW=")) else 0)
    # What this unit must supply AFTER SI-17: the lifecycle, not the door.
    # Asserting `scripts/wt` here would now be asserting something about skt
    # through a git-issue-workflow checkout, which is exactly the confusion
    # the move exists to remove.
    result.assertion(
        "git-issue-workflow supplies the shared lifecycle helpers",
        (giw / "scripts" / "lib.sh").is_file(),
    )
    result.assertion(
        "and the scripts `wt` delegates to",
        (giw / "scripts" / "new-change.sh").is_file()
        and (giw / "scripts" / "close-change.sh").is_file(),
    )

    # ------------------------------------------------------------ round trip
    #
    # TWO ARMS, ONE VARIABLE, because the placement rule IS an skt claim and a
    # single arm cannot tell a right answer from a lucky one.
    #
    # Where a ticket worktree lands is decided by exactly one thing: whether an
    # ANCESTOR of the repo carries `integration.toml`. The rule is
    # `skills/git-issue-workflow/scripts/lib.sh:341 (worktree_parent_dir)` --
    # beside the OUTERMOST enclosing integration repo, never inside one,
    # because a linked worktree's `.git` is a FILE and a parent `git add -A`
    # stages the whole directory as a gitlink (mode 160000), which
    # INTEGRATION.md rule 1 forbids and no .gitignore glob can separate from a
    # real constituent. This node used to drive ONE arm and hard-code the
    # standalone answer, so when its fixture came to sit inside an integration
    # repo it went red -- about `skt`, which was behaving correctly.
    home = build_home(work / "home", units=[unit_record("skt", version="0.3.1", kind="PLUGIN")])
    skills = home / "skills"
    skills.mkdir(parents=True, exist_ok=True)
    link = skills / "git-issue-workflow"
    if not link.exists():
        link.symlink_to(giw)
    env = child_env(SKILL_MANAGER_HOME=str(home), INTEGRATION_SKIP_HOME="1")

    arms = [
        # label, the repo, the directory the worktree MUST appear in, where to
        # plant integration.toml (None: none anywhere above the repo)
        ("standalone", work / "standalone" / "subject-repo", work / "standalone", None),
        ("constituent", work / "constituent" / "outer" / "inner" / "subject-repo",
         work / "constituent", work / "constituent" / "outer"),
    ]
    arms_driven = 0
    for label, repo_path, wt_parent, plant in arms:
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        if plant is not None:
            plant.mkdir(parents=True, exist_ok=True)
            (plant / "integration.toml").write_text('[integration]\nname = "fixture"\n')
        arms_driven += 1
        repo_arm = init_repo(repo_path)
        if not _arm(result, wrapper, version, repo_arm, wt_parent, work, label, env):
            return result
    result.metric("placementArms", arms_driven)
    # A GUARD ON THE GUARD. Two arms that both ran the standalone fixture would
    # assert the same thing twice and read as coverage; the metric is the only
    # thing a reader sees, so it is asserted rather than merely published.
    result.assertion("both placement classifications were driven", arms_driven == 2)

    # The refusal cases below need one repo and the bare env.
    repo = work / "standalone" / "subject-repo"

    # ------------------------------------------------------------- refusals
    #
    # WHAT THESE USED TO ASSERT, AND WHY THEY CANNOT ANY MORE.
    #
    # Four fixtures -- no home; installed but no importable surface; declared
    # but not installed; neither -- each asserted a DISTINCT remedy from
    # `skills/skt/src/skt/ticket.py:66 (_giw_remedy)`, the merged fix that told
    # not-installed from not-synced (#25). `skt ticket new` can no longer reach
    # that function: it is called from `ticket.py:122 (_import_wrapper)` only
    # when `import skt.wt` FAILS, and SI-17 moved `wt` into skt, so the import
    # always succeeds. The only other caller is `epic_new`, the `--path` route
    # this node does not take.
    #
    # Driven by hand in SI-20, three of the four fixtures produced the SAME
    # message -- "no Skill Manager home could be created for this worktree" --
    # and the fourth never reached the home check at all, because a bare
    # `mkdtemp()` is not a git repository, so skt refused one step earlier.
    # With the home step skipped (`INTEGRATION_SKIP_HOME=1`) all three
    # home-bearing fixtures SUCCEED in homes carrying no git-issue-workflow in
    # any form, because `wt` resolves the lifecycle from the plugin it ships in
    # rather than from `$SKILL_MANAGER_HOME`. The fault those four remedies
    # describe cannot occur once skt and git-issue-workflow are contained in
    # one plugin. Filed as `SI-20-DF-02` and `SI-20-DF-03`; transcripts in
    # `specs/results/epic-self-improvement-substrate/tickets/SI-20/transcripts/`,
    # `step-03-refusals-byhand.txt` and `step-04-refusals-skip-home.txt`.
    #
    # Asserting those phrases again would encode the DOCUMENTATION rather than
    # the behaviour, and an eval that does that passes forever and tells you
    # nothing. Asserting their ABSENCE would encode a defect as desired.
    #
    # ASSERTED INSTEAD: the property #25 was actually defending -- "a remedy
    # that cannot run is worse than no remedy: it costs the agent a failed
    # command and a wrong mental model" -- which NOTHING here checked before.
    # The refusal names a script, and THAT SCRIPT MUST EXIST AND BE
    # EXECUTABLE. A remedy naming the standalone rung of a unit that is now
    # contained is exactly the failure this repository has hit nine times
    # (SI-25-DF-06), and it is invisible to a phrase match.
    bare_env = child_env(PYTHONPATH="")
    orphan = Path(tempfile.mkdtemp(prefix="skt-ticket-nohome-"))
    cases = [
        (
            "not a git repository at all",
            child_env(PYTHONPATH="", SKT_ROOT_HOME=str(work / "does-not-exist")),
            orphan,
            ["not inside a git repository"],
        ),
        (
            # A home that is PERFECTLY FINE -- it is the one both arms above
            # round-tripped through -- and a repo that has no project home of
            # its own. Without `INTEGRATION_SKIP_HOME` that is where `new`
            # stops, and the remedy it prints is the one that has to run.
            "a git repository with no project home",
            {**bare_env, "SKILL_MANAGER_HOME": str(home)},
            repo,
            ["no Skill Manager home could be created"],
        ),
    ]

    for name, case_env, cwd, expected in cases:
        proc = _skt(wrapper, ["ticket", "new", "TG-REFUSED"], cwd=cwd, env=case_env)
        blob = proc.stdout + proc.stderr
        result.log(f"refusal [{name}] rc={proc.returncode}: {blob.strip()[:600]}")
        result.assertion(f"refusal [{name}]: exits non-zero", proc.returncode != 0)
        for needle in expected:
            result.assertion(f"refusal [{name}]: names {needle!r}", needle in blob)
        remedies = _remedy_scripts(blob)
        result.assertion(f"refusal [{name}]: prints a remedy", bool(remedies))
        for remedy in remedies:
            result.assertion(
                f"refusal [{name}]: the remedy it names EXISTS and runs -- {remedy.name}",
                remedy.is_file() and os.access(remedy, os.X_OK),
            )
        result.assertion(
            f"refusal [{name}]: creates no worktree",
            not (Path(cwd).parent / f"{Path(cwd).name}-TG-REFUSED").exists(),
        )

    shutil.rmtree(orphan, ignore_errors=True)
    result.metric("refusalCases", len(cases))

    # NOTHING OUTSIDE THE FIXTURE TREE, asserted before it is swept away. The
    # sweep below would hide a leak: a worktree created beside the repository
    # under test is not in `work`, so removing `work` removes no evidence of
    # it. This is the declared `side_effects("fs:tmp")` turned into a check.
    strays = sorted(
        str(c) for c in Path(REPO_ROOT).parent.glob("subject-repo-TG-*")
    )
    if strays:
        result.log(f"STRAY WORKTREES beside the repository under test: {strays}")
    result.assertion(
        "no ticket worktree was created outside the fixture tree", not strays
    )
    shutil.rmtree(work, ignore_errors=True)
    return result.publish("giwSource", source)


def _contract(text: str) -> dict[str, str]:
    keys = {}
    for line in text.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0] in ("worktree", "branch", "close", "launch", "propagate"):
            keys[parts[0]] = parts[1].strip()
    return keys


if __name__ == "__main__":
    main()
