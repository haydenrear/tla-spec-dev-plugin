import glob,os,sys
print("sys.executable:",sys.executable)
CONTAINED=["discovery","git-epic-workflow","git-integration-repo","git-issue","git-issue-workflow",
           "plugin-repository","skill-manager","skt","spec-double-2","test-graph","unit-authoring"]
PROBE=CONTAINED+["spec-double-compiler"]
h=sys.argv[1]
skills=sorted(os.path.basename(p) for p in glob.glob(h+"/skills/*") if os.path.isdir(p))
recs=sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(h+"/installed/*.json"))
sd=[s for s in skills if s in PROBE]; sr=[r for r in recs if r in PROBE]
print(f"POSITIVE CONTROL home={h}")
print(f"  standalone_substrate_dirs    = {len(sd)} {sd}")
print(f"  standalone_substrate_records = {len(sr)} {sr}")
assert len(sd)==2 and len(sr)==2, f"DETECTOR DID NOT FIRE on a home with 2 planted standalone copies: {sd} {sr}"
print("  DETECTOR FIRES as expected -> the 0 readings in the real homes are measurements, not silent misses")
