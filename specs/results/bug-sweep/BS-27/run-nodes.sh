#!/bin/bash
# usage: run-nodes.sh <worktree> <outdir>
WT=$1; OUT=$2; mkdir -p "$OUT"
SM=/Users/hayde/IdeaProjects/skill-manager/test_graph/sources
cd "$OUT"
export OTEL_SDK_DISABLED=true
SKILL_MANAGER_SKILL_DIR=$WT/skills/skill-manager SKILL_MANAGER_HOME=/nonexistent \
 jbang $SM/smoke/doc/SkillManagerSkillDocsProjected.java --nodeId=skill-manager.skill.docs.projected --runId=bs27 --reportDir=$OUT/doc --result-out=$OUT/doc-smoke.result.json > $OUT/doc-smoke.stdout 2>&1
echo "doc exit $?"
TICKET_LIFECYCLE_SCRIPTS=$WT/skills/git-issue-workflow/scripts SKILL_MANAGER_HOME=/nonexistent \
 jbang $SM/onboarding/OnboardingDocsAndScriptsStatic.java --nodeId=onboarding.docs.and.scripts.static --runId=bs27 --reportDir=$OUT/onb --result-out=$OUT/onboarding.result.json > $OUT/onboarding.stdout 2>&1
echo "onboarding exit $?"
