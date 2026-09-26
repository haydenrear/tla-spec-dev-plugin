import sys,glob,yaml,os,re
print("sys.executable:",sys.executable)
fs=sorted(glob.glob("/Users/hayde/IdeaProjects/wt-372-evaluation-b/specs/results/deferred/*.yaml"))
assert fs, "NON-VACUITY FAIL: no partition files"
VERB=re.compile(r'^\s*(applied|declined|proposed|none)\b')
tot=0; sc=0; parse=0
print(f"{'file':26s} {'rows':>5s} {'has skill_change':>16s} {'parseable':>10s}")
for f in fs:
    d=yaml.safe_load(open(f))
    assert isinstance(d,dict) and "findings" in d, f"NON-VACUITY FAIL: {f} has no 'findings' key (keys={list(d) if isinstance(d,dict) else type(d)})"
    rows=d["findings"] or []
    n=len(rows)
    h=sum(1 for r in rows if isinstance(r,dict) and r.get("skill_change"))
    p=sum(1 for r in rows if isinstance(r,dict) and r.get("skill_change") and VERB.match(str(r["skill_change"])))
    tot+=n; sc+=h; parse+=p
    print(f"{os.path.basename(f):26s} {n:5d} {h:16d} {p:10d}")
print(f"{'TOTAL':26s} {tot:5d} {sc:16d} {parse:10d}")
assert tot>=41, f"NON-VACUITY FAIL: only {tot} partition rows"
# cross-check: ledger's 4-file population + partitions
print(f"\nledger 4-file population        : 193")
print(f"per-ticket partition rows       : {tot}  (read by the ledger: NO -- BACKLOGS has 2 files only)")
print(f"true population if partitions counted once: {193+tot}")
