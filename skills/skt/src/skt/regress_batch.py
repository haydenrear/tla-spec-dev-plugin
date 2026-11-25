"""Owner review of the accumulated changes and attribution from a regression run."""
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

from .episode import AgentError


def git(repo, *args, data=None):
    proc = subprocess.run(["git", *args], cwd=repo, input=data, capture_output=True)
    if proc.returncode:
        raise AgentError(proc.stderr.decode(errors="replace").strip() or f"git {args[0]} failed")
    return proc.stdout


def patch(repo, base, head):
    return git(repo, "diff", "--binary", "--full-index", "--no-color", "--no-ext-diff",
               "--no-textconv", base, head, "--")


def verify_rows(rows, record, registered):
    """Only a node declaration at the tested revision can corroborate a ticket."""
    repo, base = record["worktree"], record["sha"]
    gaps = []
    for row in rows:
        problems = []
        fix = row.get("fix")
        citations = []
        if fix not in ("none", "escalated", None):
            if isinstance(fix, str) and re.fullmatch(r"[0-9a-fA-F]{4,64}", fix):
                citations.append(("fix", fix))
            else:
                problems.append("fix cites an unknown commit; supply its Git hash")
        introduced = row.get("introduced_by")
        if isinstance(introduced, str) and re.fullmatch(r"[a-fA-F0-9]{6,64}", introduced):
            citations.append(("introduced_by", introduced))
        for field in ("introduced_by", "observed", "pinned_by", "effect", "area"):
            for sha in re.findall(r"\bcommit\s+[`#]?([a-fA-F0-9]{4,64})\b", str(row.get(field) or ""), re.I):
                citations.append((field, sha))
        for field, sha in citations:
            try:
                git(repo, "rev-parse", "--verify", "--end-of-options", sha + "^{commit}")
            except AgentError:
                problems.append(f"{field} cites unknown commit {sha}")
        ticket, node = row.get("introduced_by"), row.get("node")
        touched = []
        if ticket:
            for path in registered.get(row.get("graph"), []):
                try:
                    path = (Path(record["test_graph_root"]).parent / path).resolve().relative_to(repo).as_posix()
                    source = git(repo, "show", f"{base}:{path}")
                    calls = (n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call))
                    if not any(getattr(n.func, "id", None) == "NodeSpec" and n.args
                               and isinstance(n.args[0], ast.Constant) and n.args[0].value == node for n in calls):
                        continue
                    history = git(repo, "log", "--format=%s", base, "--", path).decode().splitlines()
                    if any(subject.split() and subject.split()[0].rstrip(":") == ticket for subject in history):
                        touched.append(path)
                except (ValueError, SyntaxError, AgentError):
                    continue
            if not touched:
                problems.append(f"no verified {ticket} change to sources of {node}")
        row["verification"] = "unverified" if problems or not ticket else "verified"
        row["verification_notes"] = problems
        row["node_sources"] = touched
        gaps.extend(problems)
    return gaps


def candidate_rows(path):
    """Read the small YAML subset emitted by write_attribution_yaml (JSON scalars)."""
    rows = []
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        if line.startswith("- id: REGRESS-"):
            rows.append({})
        elif rows and line == "  channel: test-graph":
            continue
        elif rows and line.startswith("  "):
            key, separator, value = line.strip().partition(": ")
            if not separator or key in rows[-1]:
                raise AgentError(f"invalid attribution field in {path.name}")
            rows[-1][key] = json.loads(value)
        else:
            raise AgentError(f"unreadable candidate attribution in {path.name}")
    return rows


def atomic_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def decide(record, owner, accept, reject):
    state = Path(record["state"])
    attempts = [state / f"attempt-{item['attempt']}" for item in record["attempts"]]
    if not attempts:
        if accept or reject:
            raise AgentError("there is no completed attempt to review")
        return False
    latest = attempts[-1]
    result = json.loads((latest / "result.json").read_text())
    changes = latest / "fixes.patch"
    files = [p / "attribution.yaml" for p in attempts if (p / "attribution.yaml").is_file()]
    if changes.exists():
        files.append(changes)
    if not files:
        if accept or reject:
            raise AgentError("there is no candidate batch")
        return False
    digest = hashlib.sha256()
    digest.update(f"{record['id']}:{record['sha']}:{latest.name}".encode())
    for path in files:
        digest.update(str(path.relative_to(state)).encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    token = digest.hexdigest()
    receipt = state / "owner-decision.json"
    prior = json.loads(receipt.read_text()) if receipt.exists() else {}
    choice = "accepted" if accept else "rejected" if reject else None
    if choice and (accept or reject) != token:
        raise AgentError("candidate changed; inspect the current batch and use its digest")
    if prior.get("status") in ("accepted", "rejected"):
        if choice and prior["status"] != choice:
            raise AgentError("the owner already decided this batch")
        print(f"{prior['status']} {token} (decision already recorded)")
        return True
    if not choice:
        print("Inspect the complete diff for removed or relaxed assertions, guards and identity checks.")
        for path in files:
            print(path)
        print(f"skt regress close {record['id']} --accept {token}  # or --reject {token}")
        return True
    if prior and (prior.get("digest") != token or choice == "rejected"):
        raise AgentError("an acceptance is in progress; complete it from its owner checkout")
    commit = prior.get("commit")
    base = record["sha"]
    if accept:
        fix_heads = set()
        for attempt in attempts:
            info = json.loads((attempt / "result.json").read_text())
            if info["mode"] == "fix" and not info["fixes"]["uncommitted"]:
                fix_heads.add(info.get("candidate_head"))
            attribution = attempt / "attribution.yaml"
            if attribution.is_file():
                rows = candidate_rows(attribution)
                claimed = [row.get("verification") for row in rows]
                problems = verify_rows(rows, record, info.get("graph_sources", {}))
                if any("unknown commit" in problem for problem in problems):
                    raise AgentError("candidate attribution cites an unknown commit; reject this batch")
                if claimed != [row["verification"] for row in rows]:
                    raise AgentError("candidate attribution verification changed; obtain a fresh batch")
        owner = Path(git(owner, "rev-parse", "--show-toplevel").decode().strip())
        current = git(owner, "rev-parse", "HEAD").decode().strip()
        branch = git(owner, "symbolic-ref", "--short", "HEAD").decode().strip()
        if owner == Path(record["worktree"]) and changes.is_file():
            raise AgentError("accept from the owner's checkout")
        if prior and (str(owner) != prior.get("owner") or branch != prior.get("branch")):
            raise AgentError("retry from the original owner checkout and branch")
        if current != base and current != commit:
            raise AgentError("stale base; rerun against the owner's current HEAD")
        if changes.is_file() and current == base:
            candidate = result.get("candidate_head")
            if not candidate or candidate not in fix_heads or result["fixes"]["uncommitted"]:
                raise AgentError("acceptance needs a clean committed fix-mode candidate")
            if git(owner, "status", "--porcelain", "--untracked-files=no").strip():
                raise AgentError("owner has uncommitted changes")
            if patch(owner, base, candidate) != changes.read_bytes():
                raise AgentError("candidate tree differs from the inspected patch")
            tree = git(owner, "rev-parse", candidate + "^{tree}").decode().strip()
            if not commit:
                commit = git(owner, "commit-tree", tree, "-p", base, "-m",
                             f"Accept reviewed regress batch {record['id']} ({token[:12]})").decode().strip()
                atomic_json(receipt, dict(status="applying", digest=token, commit=commit,
                                          owner=str(owner), branch=branch))
            git(owner, "merge", "--ff-only", commit)
    atomic_json(receipt, dict(status=choice, digest=token, commit=commit))
    print(f"{choice} {token}; evidence kept in {state}")
    return True


def protect_adopted_refs(record, attempt, env):
    """Apply a reference-transaction guard to git in this checkout for the episode."""
    import os
    import sys

    repo = record["worktree"]
    git_dir = git(repo, "rev-parse", "--absolute-git-dir").decode().strip()
    original = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "hooks").decode().strip())
    hooks = attempt / "report-only-hooks"
    hooks.mkdir(exist_ok=True)
    for hook in original.glob("*"):
        if hook.is_file() and hook.name != "reference-transaction":
            link = hooks / hook.name
            if not link.exists():
                link.symlink_to(hook)
    guard = hooks / "reference-transaction"
    guard.write_text(f"#!{sys.executable}\n" + """import os, subprocess, sys
data = sys.stdin.buffer.read()
if sys.argv[1] == "prepared" and any(line.split()[-1].startswith(b"refs/heads/") or
                                     line.split()[-1] == b"HEAD" for line in data.splitlines()):
    sys.exit("skt regress: report-only episode cannot update the adopted branch")
""" + f"original = {str(original / 'reference-transaction')!r}\n" + """
if os.access(original, os.X_OK):
    sys.exit(subprocess.run([original, *sys.argv[1:]], input=data).returncode)
""")
    guard.chmod(0o700)
    config = attempt / "report-only.gitconfig"
    git(repo, "config", "--file", str(config), "core.hooksPath", str(hooks))
    # Preserve inherited entries by appending without copying their values
    # into the durable request. Other repositories used by a graph still get
    # their own hooks and can create fixture commits.
    count = int(env.get("GIT_CONFIG_COUNT", os.environ.get("GIT_CONFIG_COUNT", "0")))
    env.update({"GIT_CONFIG_COUNT": str(count + 1), f"GIT_CONFIG_KEY_{count}": f"includeIf.gitdir:{git_dir}.path",
                f"GIT_CONFIG_VALUE_{count}": str(config)})
