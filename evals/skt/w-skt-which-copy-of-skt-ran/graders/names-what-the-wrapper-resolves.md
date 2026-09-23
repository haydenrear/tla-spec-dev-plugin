---
type: regex
pattern: 'plugins/\S*skills/skt|home (it|this wrapper|the wrapper|the shim|this shim) lives in'
weight: 3
---

THE BEHAVIOUR. The generated wrapper carries no absolute home path — only the
interpreter and a HOME-RELATIVE entrypoint:

    py="/opt/homebrew/bin/python3.14"
    rel="plugins/tla-spec-dev/skills/skt/src/skt/cli.py"
    home="$(cd -- "$shim_dir/../.." && pwd -P)"
    entrypoint="$home/$rel"

So `<checkout>/.skill-manager/bin/cli/skt` runs
`<checkout>/.skill-manager/plugins/tla-spec-dev/skills/skt/src/skt/cli.py` —
the home's own contained copy of the plugin — and never
`<checkout>/skills/skt/`, which is a different tree that merely sits nearby.
That is the wrapper contract working as designed (`skill-scripts/install-skt.sh`
and skill-manager#262: a frozen `$SKILL_DIR` sent a home that HAD its own copy
off to run somebody else's), not a defect.

Either spelling passes: the entrypoint path, or the rule in words.

OBSERVED, NOT INFERRED. In the SI-20 worktree at `1cb00be7` on 2026-09-23:

    $ git -C <worktree>/.skill-manager/plugins/tla-spec-dev log --oneline -1
    1efa0b4b plan revision 6: …
    $ diff <worktree>/.skill-manager/plugins/tla-spec-dev/skills/skt/src/skt/status.py \
           <worktree>/skills/skt/src/skt/status.py
    → differs

Reads the FINAL RESPONSE only.
