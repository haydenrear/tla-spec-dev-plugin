#!/usr/bin/env python3
"""Bind orchestration evidence, render qualified claims and admit attributed repairs."""
from __future__ import annotations

import argparse
import hashlib
from itertools import islice
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

MAX_DOCUMENT_BYTES = 1024 * 1024
MAX_FILES = 4096
MAX_SOURCE_BYTES = 64 * 1024 * 1024


class EvidenceError(ValueError):
    pass


def read_document(path: Path):
    if path.stat().st_size > MAX_DOCUMENT_BYTES:
        raise EvidenceError(f"document exceeds {MAX_DOCUMENT_BYTES} bytes: {path}")
    def nonfinite(value):
        raise EvidenceError(f"nonfinite JSON number is not an observation: {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=nonfinite)


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_document(path: Path, document, *, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(document, sort_keys=True, indent=2) + "\n").encode()
    if exclusive:
        with path.open("xb") as stream:
            os.chmod(path, 0o600)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def git(root: Path, *arguments):
    process = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, check=True)
    return process.stdout


def source_identity(root: Path):
    root = Path(git(root, "rev-parse", "--show-toplevel").decode().strip())
    head = git(root, "rev-parse", "HEAD").decode().strip()
    names = git(root, "diff", "--no-ext-diff", "--name-only", "-z", "HEAD").decode().split("\0")
    changed = fingerprint_paths(root, [name for name in names if name])
    return {"root": str(root), "commit": head, "workingTreeDigest": changed}


def fingerprint_paths(root: Path, names: list[str]):
    digest = hashlib.sha256()
    count = total = 0
    for name in sorted(names):
        path = Path(name)
        path = path if path.is_absolute() else root / path
        paths = [path]
        if path.is_dir():
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError:
                raise EvidenceError("directory identity inputs must belong to the source repository")
            listed = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", relative)
            paths = [root / value for value in listed.decode().split("\0") if value]
        for candidate in sorted(paths):
            count += 1
            if count > MAX_FILES:
                raise EvidenceError("identity input file count exceeds 4096")
            digest.update(str(candidate).encode())
            if candidate.is_file():
                total += candidate.stat().st_size
                if total > MAX_SOURCE_BYTES:
                    raise EvidenceError("identity source inputs exceed 64 MiB; declare compact corpus receipts")
                digest.update(file_digest(candidate).encode())
            else:
                digest.update(b"missing")
    return digest.hexdigest()


def binding_identity(root: Path, config_path: Path, runner: Path, graph_root: Path | None, config: dict):
    identity = config.get("identity", {})
    paths = identity.get("paths", [])
    tools = identity.get("tools", [])
    environment = identity.get("environment", [])
    for key, values in (("paths", paths), ("tools", tools), ("environment", environment)):
        if not isinstance(values, list) or len(values) > 256 or not all(isinstance(value, str) and value for value in values):
            raise EvidenceError(f"milestone.identity.{key} must be a bounded string list")
    tool_paths = [Path(sys.executable).resolve()]
    for name in tools:
        resolved = shutil.which(name)
        if resolved is None:
            raise EvidenceError(f"identity tool is unavailable: {name}")
        tool_paths.append(Path(resolved).resolve())
    if graph_root:
        paths = [*paths, *(str(graph_root / name) for name in
                          ("build.gradle.kts", "settings.gradle.kts", "sources", "support", "provider-bindings.json"))]
    runtime_environment = {name: os.environ.get(name) for name in environment}
    return {
        "schema": "epic.milestone.binding.v1",
        "source": source_identity(root),
        "runnerSource": source_identity(runner.parent) if runner.is_file() else None,
        "runnerSha256": file_digest(runner) if runner.is_file() else None,
        "configurationSha256": file_digest(config_path),
        "controller": {name: file_digest(Path(__file__).with_name(name))
                       for name in ("evidence.py", "milestone.py")},
        "inputsSha256": fingerprint_paths(root, paths),
        "tools": [{"path": str(path), "sha256": file_digest(path)} for path in tool_paths],
        "environmentSha256": hashlib.sha256(json.dumps(runtime_environment, sort_keys=True).encode()).hexdigest(),
        "architecture": {"system": platform.system(), "machine": platform.machine(),
                         "python": platform.python_version()},
    }


def evidence_reference(value, root: Path):
    if not isinstance(value, dict) or not isinstance(value.get("path"), str):
        raise EvidenceError("evidence requires a path and sha256")
    path = Path(value["path"])
    path = path if path.is_absolute() else root / path
    observed = file_digest(path)
    if value.get("sha256") != observed:
        raise EvidenceError(f"evidence digest mismatch: {path}")
    return {"path": str(path), "sha256": observed}


def observed_value(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list)):
        values = value.values() if isinstance(value, dict) else value
        return any(observed_value(item) for item in values)
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def render_claims(path: Path):
    document = read_document(path)
    claims = document.get("claims") if isinstance(document, dict) else None
    if not isinstance(claims, list) or not claims or len(claims) > 256:
        raise EvidenceError("claims must contain 1 through 256 observations")
    rows = []
    seen = set()
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get("id"), str) or not claim["id"].strip():
            raise EvidenceError("claim id is required")
        if claim["id"] in seen:
            raise EvidenceError("claim ids must be unique")
        seen.add(claim["id"])
        verdict = claim.get("verdict")
        if verdict not in {"met", "missed", "unmeasured"}:
            raise EvidenceError("claim verdict must be met, missed or unmeasured")
        row = dict(claim)
        if verdict == "unmeasured":
            if not isinstance(claim.get("reason"), str) or not claim["reason"].strip():
                raise EvidenceError("unmeasured claim requires a reason")
        else:
            for field in ("measured", "baseline", "target"):
                if not observed_value(claim.get(field)):
                    raise EvidenceError(f"{field} observation is required; use an explicit unmeasured claim")
            references = claim.get("evidence")
            if not isinstance(references, list) or not references or len(references) > 256:
                raise EvidenceError("measured claim requires evidence")
            row["evidence"] = [evidence_reference(value, path.parent) for value in references]
        rows.append(row)
    return {"schema": "epic.claims.v1", "source": {"path": str(path), "sha256": file_digest(path)}, "claims": rows}


def admit_repair(path: Path):
    report = read_document(path)
    if not isinstance(report, dict) or report.get("category") != "product":
        raise EvidenceError("product-fix admission requires a product attribution")
    for name in ("anchor", "owner"):
        if not isinstance(report.get(name), str) or not report[name].strip():
            raise EvidenceError(f"product-fix admission requires an attribution {name}")
    reproducer = report.get("reproducer")
    if not isinstance(reproducer, list) or not reproducer or not all(isinstance(v, str) and v for v in reproducer):
        raise EvidenceError("product-fix admission requires a reproducer argument list")
    red = evidence_reference(report.get("red"), path.parent)
    observation = read_document(Path(red["path"]))
    if not isinstance(observation, dict) or observation.get("status") not in {"failed", "errored"}:
        raise EvidenceError("product-fix admission requires terminal red evidence")
    return {"schema": "epic.repair-admission.v1", "admitted": True, "red": red,
            "anchor": report["anchor"], "owner": report["owner"], "reproducer": reproducer}


def cleanup_plan(build: Path, retained: list[Path]):
    if build.is_symlink():
        raise EvidenceError("cleanup build root must be a real directory")
    roots = [*(build / name for name in ("validation-reports", "validation-sweeps",
                                          "milestone-runs", "milestone-last.json", "milestone.lock")),
             *retained]
    roots = [path.resolve() for path in roots]
    children = list(islice(build.iterdir(), MAX_FILES + 1)) if build.exists() else []
    if len(children) > MAX_FILES:
        raise EvidenceError("cleanup build root exceeds 4096 immediate children")
    removed, preserved = [], []
    for child in sorted(children):
        canonical = child.resolve()
        protected = any(canonical == root or canonical.is_relative_to(root) or root.is_relative_to(canonical)
                        for root in roots)
        (preserved if protected else removed).append(str(child.absolute()))
    return {"schema": "epic.cleanup-plan.v1", "build": str(build.absolute()),
            "remove": removed, "preserve": preserved}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("claims", "admit-repair", "plan-clean"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--retain", type=Path, action="append", default=[])
    args = parser.parse_args()
    try:
        if args.command == "claims":
            result = render_claims(args.path)
        elif args.command == "admit-repair":
            result = admit_repair(args.path)
        else:
            result = cleanup_plan(args.path, args.retain)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(json.dumps({"refused": True, "reason": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
