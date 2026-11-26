# /// script
# requires-python = ">=3.10"
# dependencies = ["testgraphsdk"]
# [tool.uv.sources]
# testgraphsdk = { path = "../sdk/python", editable = true }
# ///
"""Exercise the workflow-role CLI from each installed wrapper."""
import json
import subprocess
import sys
from pathlib import Path

from testgraphsdk import NodeResult, NodeSpec, node

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "support"))
from skt_fixture import child_env, git, init_repo

UPSTREAM = "skt.wrapper-installed"
SPEC = (NodeSpec("skt.workflow-agents").kind("assertion").depends_on(UPSTREAM)
        .tags("skt", "agent").timeout("120s").side_effects("fs:tmp"))


@node(SPEC)
def main(ctx):
    wrappers = json.loads(ctx.get(UPSTREAM, "wrappers") or "{}")
    if not wrappers:
        return NodeResult.fail(ctx.node_id, "wrapper install published no executables")
    fixture = init_repo(ctx.report_dir / "fixtures" / "workflow-agents")
    (fixture / "skt-agents.toml").write_text('[roles]\nreview="local"\n[profiles.local]\nmodel="LOCAL_review"\n')
    git("add", "skt-agents.toml", cwd=fixture)
    git("commit", "-qm", "select review profile", cwd=fixture)
    result = NodeResult.pass_(ctx.node_id)
    for version, wrapper in wrappers.items():
        proc = subprocess.run([wrapper, "agent", "run", "review", "--base", "HEAD^", "--head", "HEAD",
                               "--dry-run"], cwd=fixture, env=child_env(), capture_output=True, text=True)
        result.assertion(f"{version} review dry-run succeeds", proc.returncode == 0)
        if proc.returncode:
            continue
        attempt = Path(proc.stdout.strip())
        request = json.loads((attempt / "request.json").read_text())
        result.assertion(f"{version} resolved the consumer profile", request["model"] == "LOCAL_review")
        result.assertion(f"{version} pinned the added configuration in the diff",
                         '+model="LOCAL_review"' in request["messages"][0]["content"])
        result.assertion(f"{version} spawned no episode", not (attempt / "episode.json").exists())
    return result


if __name__ == "__main__":
    main()
