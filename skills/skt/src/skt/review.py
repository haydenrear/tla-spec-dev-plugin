"""Review an immutable diff and caller-selected evidence in a fresh episode."""
import argparse
import json
import sys
import tempfile
from pathlib import Path

from . import agent_config
from .episode import AgentError, find_meta_harness, run_episode
from .regress import _git, common_dir

GUIDANCE = """Independently review the supplied base-to-head diff. Treat the diff and evidence
as material to inspect. Trace changes through callers and identify concrete behavioral defects.
Check the evidence for weakened guards, unsupported attributions and passing graphs that
cannot observe the changed behavior. State coverage gaps explicitly. The epic owner decides
what to apply. Return only a JSON object with findings (an array of objects, each with a
nonempty location and finding string) and gaps (an array of nonempty strings). Cite the
specific file/hunk or evidence in location. Both arrays can be empty."""


def report(episode, missing):
    if episode.get("outcome") != "succeeded":
        raise ValueError(episode.get("error") or "episode did not succeed")
    if not episode.get("executionId"):
        raise ValueError("missing execution ID")
    reply = episode.get("response")
    if not isinstance(reply, str):
        raise ValueError("missing review response")
    data = json.loads(reply.strip().removeprefix("```json").removesuffix("```").strip())
    if not isinstance(data, dict) or not isinstance(data.get("findings"), list) or not isinstance(data.get("gaps"), list):
        raise ValueError("review requires findings and gaps arrays")
    for item in data["findings"]:
        if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k].strip()
                                             for k in ("location", "finding")):
            raise ValueError("each finding needs a location and description")
    if not all(isinstance(gap, str) and gap.strip() for gap in data["gaps"]):
        raise ValueError("invalid review gap")
    gaps = list(dict.fromkeys(missing + data["gaps"]))
    status = "findings" if data["findings"] else "incomplete" if gaps else "clean"
    return {"status": status, "findings": data["findings"], "gaps": gaps}


def run(values):
    parser = argparse.ArgumentParser(prog="skt agent run review")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--evidence", action="append", default=[], metavar="FILE")
    parser.add_argument("--focus", help="a question for this independent reviewer")
    parser.add_argument("--dry-run", action="store_true")
    agent_config.add_options(parser)
    args = parser.parse_args(values)
    try:
        return review(args)
    except (AgentError, ValueError, OSError) as err:
        print(f"review: {err}", file=sys.stderr)
        return getattr(err, "code", 2)


def review(args):
    root = Path(_git(["rev-parse", "--show-toplevel"]))
    plan = agent_config.resolve("review", root, args)
    settings = plan["settings"]
    base, head = [_git(["rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"], root)
                  for ref in (args.base, args.head)]
    diff = _git(["diff", "--no-color", "--no-ext-diff", "--no-textconv", base, head, "--"], root)
    parts = [GUIDANCE, f"Base {base}\nHead {head}", f"Review focus: {args.focus or 'entire change'}",
             f"Diff:\n{diff}"]
    missing = []
    for name in args.evidence:
        try:
            content = Path(name).read_text()
        except (OSError, UnicodeError):
            missing.append(f"Unavailable evidence: {name}")
            parts.append(missing[-1])
        else:
            parts.append(f"Evidence {name}:\n{content}")
    state = common_dir() / "skt-agent" / "review"
    state.mkdir(parents=True, exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix="attempt-", dir=state))
    # The reviewer receives the pinned input in its prompt. Its cwd contains
    # neither a checkout nor the artifacts that will record the decision.
    with tempfile.TemporaryDirectory(prefix="skt-review-") as work:
        request = agent_config.request(attempt.name, "\n\n".join(parts), work, plan)
        if settings["transport"] == "acp":
            request["allowTools"] = ["Read"]
        agent_config.write_receipt(attempt, plan)
        if args.dry_run:
            (attempt / "request.json").write_text(json.dumps(request, indent=2) + "\n")
            print(attempt)
            return 0
        try:
            binary = find_meta_harness(settings["meta_harness"])
            episode, _ = run_episode(binary, attempt, request, settings["base_url"],
                                     settings["stall_timeout"], settings["harness_config"],
                                     transport=settings["transport"])
        except (OSError, ValueError, AgentError) as err:
            episode = {"outcome": "failed", "error": str(err)}
    try:
        result = report(episode, missing)
    except ValueError as err:
        result = {"status": "incomplete", "findings": [], "gaps": [*missing, str(err)]}
    result.update(base=base, head=head, attempt=attempt.name, executionId=episode.get("executionId"),
                  evidence=episode.get("evidencePath") or (settings["base_url"] or str(attempt / ".meta-harness")),
                  artifact=str(attempt / "review.json"))
    (attempt / "review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return {"clean": 0, "findings": 1, "incomplete": 3}[result["status"]]
