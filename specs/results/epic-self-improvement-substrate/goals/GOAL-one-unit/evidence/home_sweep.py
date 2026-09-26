import json,os,sys,glob
print("sys.executable:",sys.executable)
CONTAINED=["discovery","git-epic-workflow","git-integration-repo","git-issue","git-issue-workflow",
           "plugin-repository","skill-manager","skt","spec-double-2","test-graph","unit-authoring"]
OLD=["spec-double-compiler"]                      # pre-rename spelling
PROBE=CONTAINED+OLD
assert len(CONTAINED)==11, "NON-VACUITY: expected 11 contained units"
HOMES={
 "root":    os.path.expanduser("~/.skill-manager"),
 "project": "/Users/hayde/IdeaProjects/tla-spec-dev/.skill-manager",
 "worktree":"/Users/hayde/IdeaProjects/wt-372-evaluation-b/.skill-manager",
}
res={}
for name,h in HOMES.items():
    if not os.path.isdir(h):
        res[name]={"MISSING":h}; continue
    skills=sorted(os.path.basename(p) for p in glob.glob(h+"/skills/*") if os.path.isdir(p))
    plugins=sorted(os.path.basename(p) for p in glob.glob(h+"/plugins/*") if os.path.isdir(p))
    recs=sorted(os.path.basename(p) for p in glob.glob(h+"/installed/*.json"))
    # NON-VACUITY: a home with no install records at all is a mis-resolved path, not a clean home
    assert recs or skills or plugins, f"NON-VACUITY FAIL: {name} home {h} has no skills, plugins or install records -- path mis-resolved?"
    standalone_dirs=[s for s in skills if s in PROBE]
    standalone_recs=[r for r in recs if os.path.splitext(r)[0] in PROBE]
    # skt contained inside a plugin?
    contained_paths=sorted(glob.glob(h+"/plugins/*/skills/skt"))
    plugin_installed=[p for p in plugins if "tla-spec-dev" in p]
    res[name]={"home":h,"n_skill_dirs":len(skills),"n_plugin_dirs":len(plugins),"n_install_records":len(recs),
      "standalone_substrate_dirs":standalone_dirs,"standalone_substrate_records":standalone_recs,
      "skt_contained_in":contained_paths,"plugin_dirs_matching_tla_spec_dev":plugin_installed,
      "plugin_dirs":plugins}
print(json.dumps(res,indent=2))
print("\n=== SUMMARY: GOAL-one-unit clause 1 / GOAL-one-plugin clause 3 ===")
for n,d in res.items():
    if "MISSING" in d: print(f"{n:9s} HOME MISSING {d['MISSING']}"); continue
    sd=d["standalone_substrate_dirs"]; sr=d["standalone_substrate_records"]
    print(f"{n:9s} skill_dirs={d['n_skill_dirs']:3d} install_records={d['n_install_records']:3d} "
          f"standalone_dirs={len(sd)} {sd} standalone_records={len(sr)} {sr} "
          f"skt_contained={len(d['skt_contained_in'])} plugin={d['plugin_dirs_matching_tla_spec_dev']}")
