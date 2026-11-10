"""Resume and retirement integrity for ticket worktrees (BS-19, #201).

A multi-day epic resumed onto worktrees that had lost tracked source
files, their linked-worktree `.git` pointer, and held raw evidence. Git's
objects survived. The receipts written days earlier (clean, home closed
out, evidence held) no longer described the live filesystem, and nothing
re-measured it before validation or teardown began.

This module re-measures. It is the ONE implementation behind
`skt ticket list` (resume), `skt ticket sweep` (retirement) and
git-issue-workflow's `close-change.sh`, and it answers from the live
filesystem every time:

  worktree_missing   the directory itself is gone
  pointer_missing    `<wt>/.git` is gone — git cannot even find the repo
                     from inside it, and `git worktree prune` would delete
                     the admin entry (index, HEAD) that could restore it
  pointer_mismatch   `<wt>/.git` names some other admin directory
  source_missing     a tracked file is in the index but not on disk. A
                     deletion that was committed, or staged with `git rm`,
                     is NOT in the index and is never reported here
  home_missing       the manifest recorded a Skill Manager home; it is gone
  evidence_missing   a declared retained-evidence file is gone
  evidence_replaced  a declared retained-evidence file's bytes changed

Every finding carries an opaque handle and expected/current hashes,
never file contents.

Where the record lives
----------------------

In the repository's COMMON git directory, `<common>/skt-integrity/`, keyed
by an opaque handle of the worktree path. Not in the worktree, which is
the thing that went missing, and not under `<common>/worktrees/<name>/`,
which `git worktree prune` deletes.

  <handle>.manifest.json   what was declared: the home, and each retained
                           evidence file with its sha256
  <handle>.receipts.jsonl  APPEND-ONLY history of every recorded check and
                           every superseded manifest. Kept as history; it
                           is never read to decide a current verdict, so an
                           old "intact" cannot satisfy today's check.

Recovery is offered, never performed, and never by reset, clean, checkout
-f or --force: a missing pointer by `git worktree repair`, missing tracked
source by `git checkout-index` without `-f` (it writes only paths that are
absent). Missing or replaced raw evidence has no recovery and is reported
as unavailable.

Runnable standalone (stdlib only), so close-change.sh can call it:

    python3 ticket_integrity.py declare <worktree> [<evidence-path>...]
    python3 ticket_integrity.py check   <worktree> [--record] [--json]

`check` exits 0 when intact and 3 when it found something.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

SCHEMA = 1
STORE = "skt-integrity"
HOME_DIR = ".skill-manager"
EXIT_FINDINGS = 3
#: How many findings of one kind are itemised; the rest are counted.
MAX_ITEMS = 6
READ_TIMEOUT = 10.0

#: The kinds, in the order a reader should act on them.
KINDS = (
    "worktree_missing",
    "pointer_missing",
    "pointer_mismatch",
    "source_missing",
    "home_missing",
    "evidence_missing",
    "evidence_replaced",
)


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=str(cwd) if cwd else None,
            capture_output=True, text=True, timeout=READ_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolved(path: str | Path) -> Path:
    try:
        return Path(path).expanduser().resolve()
    except (OSError, RuntimeError):
        return Path(os.path.abspath(path))


def _short(digest: str | None) -> str | None:
    return digest[:12] if digest else digest


def handle(worktree: str | Path) -> str:
    """Opaque, stable name for a worktree path."""
    return "wt-" + hashlib.sha256(str(_resolved(worktree)).encode()).hexdigest()[:12]


def _item_handle(prefix: str, rel: str) -> str:
    return f"{prefix}-" + hashlib.sha256(rel.encode()).hexdigest()[:8]


def sha256_file(path: Path) -> str | None:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def common_dir(root: str | Path) -> Path | None:
    proc = _git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=Path(root))
    if proc is None or proc.returncode != 0 or not proc.stdout.strip():
        return None
    return Path(proc.stdout.strip())


def admin_dir(common: Path, worktree: str | Path) -> Path | None:
    """`<common>/worktrees/<name>` whose `gitdir` names `<worktree>/.git`.

    Read from the admin side, so it still answers when the worktree's own
    `.git` pointer is gone.
    """
    want = _resolved(worktree)
    base = common / "worktrees"
    try:
        entries = sorted(base.iterdir())
    except OSError:
        return None
    for entry in entries:
        try:
            gitdir = (entry / "gitdir").read_text().strip()
        except OSError:
            continue
        if gitdir and _resolved(Path(gitdir).parent) == want:
            return entry
    return None


def _store(common: Path) -> Path:
    return common / STORE


def manifest_path(common: Path, wt_handle: str) -> Path:
    return _store(common) / f"{wt_handle}.manifest.json"


def receipts_path(common: Path, wt_handle: str) -> Path:
    return _store(common) / f"{wt_handle}.receipts.jsonl"


def load_manifest(common: Path, wt_handle: str) -> dict | None:
    try:
        data = json.loads(manifest_path(common, wt_handle).read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _append_receipt(common: Path, wt_handle: str, record: dict) -> None:
    path = receipts_path(common, wt_handle)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def _expand(worktree: Path, paths: list[str]) -> list[str]:
    """Declared paths, relative to the worktree, directories expanded."""
    out: list[str] = []
    for raw in paths:
        p = Path(raw)
        full = p if p.is_absolute() else worktree / p
        if full.is_dir():
            out += sorted(
                os.path.relpath(f, worktree) for f in full.rglob("*") if f.is_file()
            )
        else:
            out.append(os.path.relpath(full, worktree))
    return out


def declare(root: str | Path, worktree: str | Path, evidence: list[str] = ()) -> dict:
    """Record (or extend) the worktree's retained-evidence manifest.

    The home is recorded as present when it is present now. Evidence is
    hashed now. A manifest that already exists is kept: its entries are
    merged, and the version it replaces goes into the receipts as history.
    """
    wt = _resolved(worktree)
    common = common_dir(root)
    if common is None:
        raise RuntimeError(f"{root} is not inside a git repository")
    wt_handle = handle(wt)
    previous = load_manifest(common, wt_handle)
    entries = {e["path"]: e for e in (previous or {}).get("evidence", []) if isinstance(e, dict)}
    for rel in _expand(wt, list(evidence)):
        digest = sha256_file(wt / rel)
        if digest is None:
            raise FileNotFoundError(f"cannot declare {rel}: not a readable file under {wt}")
        entries[rel] = {"handle": _item_handle("ev", rel), "path": rel, "sha256": digest}
    branch = _git("symbolic-ref", "--quiet", "--short", "HEAD", cwd=wt)
    manifest = {
        "schema": SCHEMA,
        "handle": wt_handle,
        "worktree": str(wt),
        "branch": branch.stdout.strip() if branch is not None and branch.returncode == 0 else None,
        "declared_at": _now(),
        "home": bool((previous or {}).get("home")) or (wt / HOME_DIR).is_dir(),
        "evidence": [entries[k] for k in sorted(entries)],
    }
    if previous is not None:
        _append_receipt(common, wt_handle, {"at": _now(), "event": "manifest_superseded",
                                            "manifest": previous})
    path = manifest_path(common, wt_handle)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)
    return manifest


@dataclass(frozen=True)
class Finding:
    kind: str
    handle: str
    path: str
    expected: str | None = None
    current: str | None = None
    fix: str = ""

    def line(self) -> str:
        hashes = ""
        if self.expected is not None or self.current is not None:
            hashes = f" expected {_short(self.expected) or '-'} current {_short(self.current) or 'absent'}"
        return f"{self.kind} {self.handle} {self.path}{hashes}"


@dataclass(frozen=True)
class Integrity:
    handle: str
    worktree: str
    findings: tuple[Finding, ...] = ()
    #: Declared evidence that is intact NOW — removing the worktree deletes it.
    retained: tuple[str, ...] = ()
    manifest: bool = False
    unmeasured: tuple[str, ...] = ()
    #: Counts per kind, including findings beyond MAX_ITEMS.
    counts: dict = field(default_factory=dict)

    @property
    def intact(self) -> bool:
        return not self.findings and not self.unmeasured

    @property
    def pointer_missing(self) -> bool:
        return any(f.kind == "pointer_missing" for f in self.findings)

    def kinds(self) -> list[str]:
        return [k for k in KINDS if self.counts.get(k)]

    def summary_lines(self) -> list[str]:
        """One line per finding (bounded per kind), then the fixes once each."""
        out: list[str] = []
        for kind in KINDS:
            items = [f for f in self.findings if f.kind == kind]
            for f in items:
                out.append(f"integrity: {f.line()}")
            extra = self.counts.get(kind, 0) - len(items)
            if extra > 0:
                out.append(f"integrity: {kind} +{extra} more")
        for probe in self.unmeasured:
            out.append(f"integrity: could not determine {probe} — refusing to guess")
        return out

    def fixes(self) -> list[str]:
        seen: list[str] = []
        for f in self.findings:
            if f.fix and f.fix not in seen:
                seen.append(f.fix)
        return seen

    def to_json(self) -> dict:
        return {
            "handle": self.handle,
            "worktree": self.worktree,
            "intact": self.intact,
            "manifest": self.manifest,
            "counts": dict(self.counts),
            "findings": [asdict(f) for f in self.findings],
            "retained": list(self.retained),
            "unmeasured": list(self.unmeasured),
            "fixes": self.fixes(),
        }


def check(root: str | Path, worktree: str | Path, *, record: bool = False) -> Integrity:
    """Measure the worktree NOW. Never consults an earlier receipt."""
    wt = _resolved(worktree)
    wt_handle = handle(wt)
    common = common_dir(root)
    if common is None:
        return Integrity(wt_handle, str(wt), unmeasured=("the repository's git directory",))
    manifest = load_manifest(common, wt_handle)
    findings: list[Finding] = []
    counts: dict[str, int] = {}
    unmeasured: list[str] = []
    retained: list[str] = []

    def add(f: Finding) -> None:
        counts[f.kind] = counts.get(f.kind, 0) + 1
        if counts[f.kind] <= MAX_ITEMS:
            findings.append(f)

    admin = admin_dir(common, wt)
    root_s = str(_resolved(root))
    if not wt.is_dir():
        add(Finding("worktree_missing", wt_handle, str(wt), fix=(
            "the directory is gone; its committed work is on its branch. Nothing here can "
            "restore uncommitted or ignored files")))
    else:
        dotgit = wt / ".git"
        if not dotgit.exists():
            add(Finding("pointer_missing", wt_handle, ".git",
                        expected=f"gitdir: {admin}" if admin else None,
                        fix=f"git -C {root_s} worktree repair {wt}   # rewrites only the .git pointer"))
        elif dotgit.is_file():
            try:
                named = dotgit.read_text().strip()
            except OSError:
                named = ""
            target = named[len("gitdir:"):].strip() if named.startswith("gitdir:") else ""
            if admin is not None and (not target or _resolved(target) != _resolved(admin)):
                add(Finding("pointer_mismatch", wt_handle, ".git",
                            expected=f"gitdir: {admin}", current=named[:200] or None,
                            fix=f"git -C {root_s} worktree repair {wt}"))
        if admin is None and not dotgit.is_dir():
            unmeasured.append("the worktree's admin entry under the common git directory")
        if admin is not None:
            gd = ["--git-dir", str(admin), "--work-tree", str(wt)]
            proc = _git(*gd, "ls-files", "--deleted", "-z", cwd=wt)
            staged = _git(*gd, "ls-files", "-s", "-z", cwd=wt)
            if proc is None or proc.returncode != 0:
                unmeasured.append("which tracked files are missing")
            else:
                blobs: dict[str, str] = {}
                if staged is not None and staged.returncode == 0:
                    for rec in staged.stdout.split("\0"):
                        meta, _, path = rec.partition("\t")
                        parts = meta.split()
                        if path and len(parts) >= 2:
                            blobs[path] = parts[1]
                missing = sorted({p for p in proc.stdout.split("\0") if p})
                fix = ""
                if missing:
                    shown = " ".join(missing[:MAX_ITEMS]) + (" …" if len(missing) > MAX_ITEMS else "")
                    fix = (f"git --git-dir={admin} --work-tree={wt} checkout-index -- {shown}"
                           "   # writes only absent paths; no -f, no reset, no clean")
                for path in missing:
                    add(Finding("source_missing", _item_handle("src", path), path,
                                expected=blobs.get(path), current=None, fix=fix))
        if manifest is not None:
            if manifest.get("home") and not (wt / HOME_DIR).is_dir():
                add(Finding("home_missing", _item_handle("home", HOME_DIR), HOME_DIR, fix=(
                    "unavailable: a re-bootstrapped home would be a NEW, empty copy; any "
                    "unpublished edit in the old one is not recoverable from here")))
            for entry in manifest.get("evidence") or []:
                if not isinstance(entry, dict) or not entry.get("path"):
                    continue
                rel = str(entry["path"])
                eh = str(entry.get("handle") or _item_handle("ev", rel))
                expected = entry.get("sha256")
                current = sha256_file(wt / rel) if (wt / rel).is_file() else None
                if current is None:
                    add(Finding("evidence_missing", eh, rel, expected=expected,
                                fix="unavailable: missing raw evidence has no recovery here"))
                elif current != expected:
                    add(Finding("evidence_replaced", eh, rel, expected=expected, current=current,
                                fix="unavailable: the declared bytes are gone; the replacement is "
                                    "not the held evidence"))
                else:
                    retained.append(eh)
    result = Integrity(
        handle=wt_handle, worktree=str(wt), findings=tuple(findings),
        retained=tuple(retained), manifest=manifest is not None,
        unmeasured=tuple(unmeasured), counts=counts,
    )
    if record:
        record_receipt(root, result)
    return result


def record_receipt(root: str | Path, result: Integrity) -> None:
    """Append one check to the worktree's receipts. History only."""
    common = common_dir(root)
    if common is None:
        return
    try:
        _append_receipt(common, result.handle, {
            "at": _now(), "event": "check",
            "verdict": "intact" if result.intact else "findings",
            "counts": dict(result.counts),
            "findings": [{"kind": f.kind, "handle": f.handle, "expected": f.expected,
                          "current": f.current} for f in result.findings],
        })
    except OSError:
        pass  # history is best-effort; the live verdict is what decides


def _main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="ticket_integrity")
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("declare", help="record the home and retained evidence of a worktree")
    d.add_argument("worktree")
    d.add_argument("evidence", nargs="*")
    d.add_argument("--root", help="any checkout of the repository (default: the worktree)")
    c = sub.add_parser("check", help="re-measure a worktree; exit 3 on any finding")
    c.add_argument("worktree")
    c.add_argument("--root", help="any checkout of the repository (default: the worktree)")
    c.add_argument("--record", action="store_true", help="append this check to the receipts")
    c.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root or args.worktree
    if args.cmd == "declare":
        try:
            m = declare(root, args.worktree, args.evidence)
        except (RuntimeError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"declared {m['handle']}: home={'yes' if m['home'] else 'no'}, "
              f"{len(m['evidence'])} retained evidence file(s)")
        return 0
    result = check(root, args.worktree, record=args.record)
    if args.json:
        print(json.dumps(result.to_json(), indent=2))
    else:
        if result.intact:
            print(f"intact {result.handle} ({len(result.retained)} retained evidence file(s) held)")
        for line in result.summary_lines():
            print(line)
        for fix in result.fixes():
            print(f"fix: {fix}")
    return 0 if result.intact else EXIT_FINDINGS


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
