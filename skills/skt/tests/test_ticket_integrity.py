"""bug-sweep BS-19 (#201): resume and retirement recheck LIVE integrity.

The finite fixture the issue names: one linked worktree with its `.git`
pointer gone, one with a tracked file gone, one whose declared retained
evidence is partly missing and partly replaced, and one whose declared home
is gone. Each must be identified DISTINCTLY by `skt ticket list` (resume)
and refused by `skt ticket sweep --yes` and `skt ticket close` (deletion),
and an old "intact" receipt must not satisfy the current check.

The manifest is written here in its on-disk format rather than through
`ticket_integrity.declare`, so this file imports and fails by ASSERTION on
the epic base, where the recheck does not exist.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skt import publish as publish_mod  # noqa: E402
from skt import ticket as ticket_mod  # noqa: E402

from test_ticket_sweep import add_worktree, epic_repo, git, isolate  # noqa: E402,F401

KINDS = ("pointer_missing", "source_missing", "evidence_missing", "evidence_replaced",
         "home_missing")


def _common(root: Path) -> Path:
    out = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute",
                          "--git-common-dir"], capture_output=True, text=True, check=True)
    return Path(out.stdout.strip())


def _handle(wt: Path) -> str:
    return "wt-" + hashlib.sha256(str(wt.resolve()).encode()).hexdigest()[:12]


def write_manifest(root: Path, wt: Path, *, home: bool, evidence: list[str]) -> Path:
    """The declared retained-evidence manifest, in its on-disk format."""
    entries = []
    for rel in evidence:
        digest = hashlib.sha256((wt / rel).read_bytes()).hexdigest()
        handle = "ev-" + hashlib.sha256(rel.encode()).hexdigest()[:8]
        entries.append({"handle": handle, "path": rel, "sha256": digest})
    store = _common(root) / "skt-integrity"
    store.mkdir(parents=True, exist_ok=True)
    path = store / f"{_handle(wt)}.manifest.json"
    path.write_text(json.dumps({"schema": 1, "handle": _handle(wt), "worktree": str(wt.resolve()),
                                "home": home, "evidence": entries}))
    return path


def _held(wt: Path, *names: str) -> list[str]:
    """Ignored raw evidence files under `raw/` (the repo ignores `raw/`)."""
    (wt / "raw").mkdir(exist_ok=True)
    rels = []
    for name in names:
        (wt / "raw" / name).write_text(f"raw observation {name}\n")
        rels.append(f"raw/{name}")
    return rels


def fixture(tmp_path) -> dict:
    """The finite fixture: four damaged worktrees and one committed deletion."""
    repo = epic_repo(tmp_path)
    root = repo["root"]
    (root / ".gitignore").write_text(".skill-manager/\nraw/\n")
    (root / "src.txt").write_text("source\n")
    git("add", "-A", cwd=root)
    git("commit", "-q", "-m", "ignore raw evidence; add source", cwd=root)
    git("push", "-q", "origin", "main", cwd=root)
    git("branch", "-f", "epic/demo", "main", cwd=root)
    git("push", "-q", "-f", "origin", "epic/demo", cwd=root)

    trees = {}
    for t in ("T-P", "T-S", "T-E", "T-H", "T-C"):
        trees[t] = add_worktree(repo, t)
        write_manifest(root, trees[t], home=True, evidence=[])
    # pointer_missing
    (trees["T-P"] / ".git").unlink()
    # source_missing — the file is still tracked, just not on disk
    (trees["T-S"] / "src.txt").unlink()
    # evidence_missing + evidence_replaced
    rels = _held(trees["T-E"], "obs-1.bin", "obs-2.bin", "obs-3.bin")
    write_manifest(root, trees["T-E"], home=True, evidence=rels)
    (trees["T-E"] / "raw" / "obs-1.bin").unlink()
    (trees["T-E"] / "raw" / "obs-2.bin").write_text("a different file\n")
    # home_missing
    subprocess.run(["rm", "-rf", str(trees["T-H"] / ".skill-manager")], check=True)
    # an INTENTIONAL committed deletion — never a finding
    git("rm", "-q", "src.txt", cwd=trees["T-C"])
    git("commit", "-q", "-m", "delete src.txt on purpose", cwd=trees["T-C"])
    return {**repo, "trees": trees}


def _rows(root: Path, capsys) -> dict:
    capsys.readouterr()
    ticket_mod.run("list", None, start=root, as_json=True)
    payload = json.loads(capsys.readouterr().out)
    return {r["ticket"]: r for r in payload["worktrees"] if r["ticket"]}


def _kinds(row: dict) -> set[str]:
    integ = row["status"].get("integrity") or {}
    return {k for k, n in (integ.get("counts") or {}).items() if n}


# ------------------------------------------------------------------ resume


def test_list_identifies_each_failure_distinctly(tmp_path, capsys):
    fx = fixture(tmp_path)
    rows = _rows(fx["root"], capsys)

    assert _kinds(rows["T-P"]) == {"pointer_missing"}
    assert _kinds(rows["T-S"]) == {"source_missing"}
    assert _kinds(rows["T-E"]) == {"evidence_missing", "evidence_replaced"}
    assert _kinds(rows["T-H"]) == {"home_missing"}
    assert _kinds(rows["T-C"]) == set(), "a committed deletion is not missing source"
    for t in ("T-P", "T-S", "T-E", "T-H"):
        assert rows[t]["status"]["clean"] is False, t


def test_list_reports_handles_and_expected_vs_current_hashes(tmp_path, capsys):
    fx = fixture(tmp_path)
    rows = _rows(fx["root"], capsys)
    findings = {f["kind"]: f for f in rows["T-E"]["status"]["integrity"]["findings"]}
    replaced = findings["evidence_replaced"]
    assert replaced["handle"].startswith("ev-")
    assert replaced["expected"] and replaced["current"] and replaced["expected"] != replaced["current"]
    assert findings["evidence_missing"]["current"] is None
    source = rows["T-S"]["status"]["integrity"]["findings"][0]
    assert source["path"] == "src.txt" and source["expected"], "the index blob is the expected hash"
    assert not any("src.txt" in d for d in rows["T-S"]["status"]["dirty"]), \
        "missing source is reported once, as integrity, not as uncommitted work"


def test_list_text_names_each_kind_and_a_non_destructive_recovery(tmp_path, capsys):
    fx = fixture(tmp_path)
    capsys.readouterr()
    assert ticket_mod.run("list", None, start=fx["root"]) == 0
    out = capsys.readouterr().out
    for kind in KINDS:
        assert kind in out, kind
    assert "worktree repair" in out
    assert "checkout-index" in out
    for banned in ("reset", "clean -", "checkout -f", "--force"):
        commands = [l.split("#")[0] for l in out.splitlines() if "recover" in l]
        assert banned not in "\n".join(commands), banned


# ---------------------------------------------------------------- deletion


def test_sweep_refuses_every_damaged_worktree_and_keeps_the_pointer_metadata(tmp_path, capsys):
    fx = fixture(tmp_path)
    capsys.readouterr()
    rc = ticket_mod.run("sweep", None, start=fx["root"], yes=True, as_json=True)
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    steps = {s["ticket"]: s for s in payload["steps"]}
    for t in ("T-P", "T-S", "T-E", "T-H"):
        assert steps[t]["action"] == "skipped", (t, steps[t])
        assert fx["trees"][t].is_dir(), t
        assert steps[t]["missing_before_sweep"], "reported as prior loss, not as removed"
    assert payload["missing_before_sweep"] == 4
    # `git worktree prune` would delete T-P's admin entry — the repair source.
    listing = git("worktree", "list", "--porcelain", cwd=fx["root"]).stdout
    assert str(fx["trees"]["T-P"].resolve()) in listing or str(fx["trees"]["T-P"]) in listing
    assert payload["pruned"] is False


def test_sweep_refuses_to_delete_intact_retained_evidence(tmp_path, capsys):
    repo = epic_repo(tmp_path)
    root = repo["root"]
    (root / ".gitignore").write_text(".skill-manager/\nraw/\n")
    git("add", "-A", cwd=root)
    git("commit", "-q", "-m", "ignore raw", cwd=root)
    git("push", "-q", "origin", "main", cwd=root)
    git("branch", "-f", "epic/demo", "main", cwd=root)
    git("push", "-q", "-f", "origin", "epic/demo", cwd=root)
    wt = add_worktree(repo, "T-R")
    write_manifest(root, wt, home=True, evidence=_held(wt, "keep.bin"))

    assert ticket_mod.run("sweep", None, start=root, yes=True) == 0
    out = capsys.readouterr().out
    assert "retained evidence" in out
    assert (wt / "raw" / "keep.bin").is_file()


def test_skill_gates_off_forces_past_evidence_but_git_still_refuses_a_broken_tree(
    tmp_path, capsys, monkeypatch
):
    fx = fixture(tmp_path)
    monkeypatch.setenv("SKILL_GATES", "off")
    capsys.readouterr()
    ticket_mod.run("sweep", None, start=fx["root"], yes=True, as_json=True)
    steps = {s["ticket"]: s for s in json.loads(capsys.readouterr().out)["steps"]}
    assert steps["T-E"]["action"] == "removed"
    assert any("FORCED" in n for n in steps["T-E"]["notes"]), "the override is on the record"
    assert fx["trees"]["T-P"].is_dir(), "git refuses a worktree with no pointer; nothing forced it"


# --------------------------------------------------- receipts and recovery


def test_an_old_intact_receipt_cannot_satisfy_the_current_check(tmp_path):
    from skt import ticket_integrity as integ

    fx = fixture(tmp_path)
    wt = fx["trees"]["T-E"]
    receipts = integ.receipts_path(_common(fx["root"]), _handle(wt))
    receipts.parent.mkdir(parents=True, exist_ok=True)
    old = json.dumps({"at": "2026-01-01T00:00:00Z", "event": "check", "verdict": "intact"})
    receipts.write_text(old + "\n")

    result = integ.check(fx["root"], wt, record=True)
    assert not result.intact
    lines = receipts.read_text().splitlines()
    assert lines[0] == old, "history is kept, never overwritten"
    assert json.loads(lines[-1])["verdict"] == "findings"


def test_offered_recovery_restores_pointer_and_source_without_touching_other_files(tmp_path):
    from skt import ticket_integrity as integ

    fx = fixture(tmp_path)
    for t in ("T-P", "T-S"):
        wt = fx["trees"][t]
        (wt / "raw").mkdir(exist_ok=True)
        (wt / "raw" / "untouched.bin").write_text("ignored data\n")
        for fix in integ.check(fx["root"], wt).fixes():
            subprocess.run(fix.split("   #")[0], shell=True, cwd=fx["root"])
        assert integ.check(fx["root"], wt).intact, t
        assert (wt / "raw" / "untouched.bin").read_text() == "ignored data\n"


def test_declare_and_check_round_trip_through_the_cli(tmp_path):
    from skt import ticket_integrity as integ

    repo = epic_repo(tmp_path)
    wt = add_worktree(repo, "T-D")
    (wt / "ev.txt").write_text("evidence\n")
    script = Path(integ.__file__)
    assert subprocess.run([sys.executable, str(script), "declare", str(wt), "ev.txt"]).returncode == 0
    assert subprocess.run([sys.executable, str(script), "check", str(wt)]).returncode == 0
    (wt / "ev.txt").write_text("tampered\n")
    proc = subprocess.run([sys.executable, str(script), "check", str(wt)],
                          capture_output=True, text=True)
    assert proc.returncode == 3 and "evidence_replaced" in proc.stdout


def test_epic_new_records_a_home_baseline_so_a_lost_home_is_reported(tmp_path, monkeypatch, capsys):
    from test_epic_mode import epic_repo as giw_repo

    from skt import ticket_integrity as integ

    root = giw_repo(tmp_path)
    monkeypatch.chdir(root)
    wt = tmp_path / "wt-B"
    assert ticket_mod.epic_new("B", "HEAD", str(wt)) == 0
    assert (wt / ".skill-manager").is_dir()
    subprocess.run(["rm", "-rf", str(wt / ".skill-manager")], check=True)
    assert [f.kind for f in integ.check(root, wt).findings] == ["home_missing"]


# ------------------------------------------------------- close-change.sh


@pytest.fixture
def giw(tmp_path, monkeypatch):
    from test_epic_mode import epic_repo as giw_repo
    from test_ticket_lifecycle import gate_cli

    for var in ("GIT_ISSUE_WORKFLOW_SCRIPTS", "WT_BIN", "GIW_WT_BIN", "SKILL_GATES"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("WT_FETCH", "0")
    monkeypatch.setattr(publish_mod, "edited_units", lambda *_: [])
    root = giw_repo(tmp_path)
    (root / "src.txt").write_text("source\n")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "-m", "src"], check=True)
    monkeypatch.chdir(root)
    cli, _ = gate_cli(tmp_path)
    monkeypatch.setenv("SKILL_MANAGER_CLI", str(cli))
    return root


def test_close_refuses_a_worktree_missing_tracked_source(giw, tmp_path, capsys):
    wt = tmp_path / "wt-CS"
    assert ticket_mod.epic_new("CS", "HEAD", str(wt)) == 0
    (wt / "src.txt").unlink()
    capsys.readouterr()
    rc = ticket_mod.run("close", "CS", start=giw)
    out = capsys.readouterr().out
    assert rc != 0, out
    assert "integrity recheck" in out, out
    assert "checkout-index" in out, "the fix names the non-destructive recovery"
    assert wt.is_dir(), "a worktree that failed the recheck is not removed"


def test_close_names_a_missing_pointer_and_its_repair(giw, tmp_path, capfd):
    wt = tmp_path / "wt-CP"
    assert ticket_mod.epic_new("CP", "HEAD", str(wt)) == 0
    (wt / ".git").unlink()
    capfd.readouterr()
    rc = ticket_mod.run("close", "CP", start=giw)
    captured = capfd.readouterr()
    assert rc != 0
    assert wt.is_dir()
    assert "pointer_missing" in captured.out + captured.err
    assert "worktree repair" in captured.out + captured.err
