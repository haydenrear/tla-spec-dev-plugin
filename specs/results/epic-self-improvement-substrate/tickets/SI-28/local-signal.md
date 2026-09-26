SI-28 — cli-floor falsification, BOTH arms
Worktree : /Users/hayde/IdeaProjects/wt-390-bootstrap-cli-floor (branch feature/390-bootstrap-cli-floor, base 3cffe686)
Date     : 2026-09-26
Operator's real brew install: skill-manager 0.28.2

HOW THE 'OLDER CLI' ARM IS EXERCISED WITHOUT DOWNGRADING BREW
-------------------------------------------------------------
skt check asks the HOME'S PIN (<home>/bin/cli/skill-manager, skt.publish._cli),
not PATH — _installed_cli_identity's docstring says why: the question is
'which skill-manager does THIS HOME run'. So two scratch homes with two pins
vary exactly the fact under test, through the same function a real old
install would go through. Nothing on the operator's machine was changed.

floor declared in /Users/hayde/IdeaProjects/wt-390-bootstrap-cli-floor/bootstrap-floor.toml: 0.28.2

================ ARM 1: FIRES against an older CLI (0.28.1) ============
$ SKILL_MANAGER_HOME=/private/tmp/claude-501/-Users-hayde-IdeaProjects-tla-spec-dev/7839c261-ef83-40a5-bbde-456292085410/scratchpad/falsify/old/.skill-manager python3.12 skills/skt/src/skt/cli.py check
skt check: 2 notification(s), tier project
  skill-manager 0.28.1 is installed here, and this plugin requires 0.28.2 or newer (bootstrap-floor.toml) — 0.28.1 and earlier fail this plugin's install with MarkdownImportValidator violations on skills/*/fixtures/** (skill-manager PR #397, released in 0.28.2)
    upgrade with: brew update && brew upgrade skill-manager
    nothing was refused — this is a warning; the floor is declared in /Users/hayde/IdeaProjects/wt-390-bootstrap-cli-floor/bootstrap-floor.toml
  skill-manager 0.28.1 is installed here, and 0.28.2 is available — this session's commands run the older one
    upgrade with: skill-manager upgrade --self
    then re-check this home: skt check
  build: skt 0.8.2; skill-manager 0.28.1 @ artifact deadbeef built 2026-09-17T00:00:00Z (skill-manager.jar)
EXIT=10

================ ARM 2: SILENT against a current CLI (0.28.2) ==========
$ SKILL_MANAGER_HOME=/private/tmp/claude-501/-Users-hayde-IdeaProjects-tla-spec-dev/7839c261-ef83-40a5-bbde-456292085410/scratchpad/falsify/new/.skill-manager python3.12 skills/skt/src/skt/cli.py check
skt check: all current (0 change-managed unit(s), tier project)
  build: skt 0.8.2; skill-manager 0.28.2 @ artifact deadbeef built 2026-09-17T00:00:00Z (skill-manager.jar)
EXIT=0

================ ARM 3: the operator's REAL installed CLI =============
$ skill-manager --version
skill-manager 0.28.2
$ SKILL_MANAGER_HOME=/Users/hayde/IdeaProjects/wt-390-bootstrap-cli-floor/.skill-manager python3.12 skills/skt/src/skt/cli.py check
skt check: 1 notification(s), tier worktree
  new version available for tla-spec-dev — pull with: skt sync tla-spec-dev
  build: skt 0.8.2; skill-manager 0.28.2 @ artifact 03c0143ec45e built 2026-09-26T01:18:51Z (skill-manager.jar)
EXIT=10

================ ARM 4: it WARNS, it refuses nothing ===================
The floor rides skt's existing notification list, so skt check exits 10 —
skt's NOTIFY code, the same one 'new version available' has always used,
and the only route by which the SessionStart hook prints anything at all
(hooks/skt-session-start.sh: 'if [ "$rc" -eq 10 ]'). The hook itself
exits 0 and the session continues. No install, session or command is
refused anywhere; nothing else in the repository reads this exit code.

$ SKILL_MANAGER_HOME=<old home> bash hooks/skt-session-start.sh; echo $?
next       skt check — new-version and sync notifications

skt check: 2 notification(s), tier project
  skill-manager 0.28.1 is installed here, and this plugin requires 0.28.2 or newer (bootstrap-floor.toml) — 0.28.1 and earlier fail this plugin's install with MarkdownImportValidator violations on skills/*/fixtures/** (skill-manager PR #397, released in 0.28.2)
  skill-manager 0.28.1 is installed here, and 0.28.2 is available — this session's commands run the older one
    upgrade with: skill-manager upgrade --self
    then re-check this home: skt check
  build: skt 0.8.2; skill-manager 0.28.1 @ artifact deadbeef built 2026-09-17T00:00:00Z (skill-manager.jar)
HOOK_EXIT=0
