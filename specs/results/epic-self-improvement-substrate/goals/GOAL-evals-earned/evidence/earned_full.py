import subprocess,sys,collections
print("sys.executable:",sys.executable)
R="/Users/hayde/IdeaProjects/wt-372-evaluation-b"
def git(*a):
    p=subprocess.run(["git","-C",R,*a],capture_output=True,text=True)
    return p.stdout
TIP="8b6d97e8"
cases=[l for l in git("ls-tree","-r","--name-only",TIP).splitlines() if l.endswith("/case.yaml") and l.startswith("evals/")]
assert len(cases)==75, f"NON-VACUITY/POPULATION FAIL: expected 75 case.yaml at tip, got {len(cases)}"
# first-add commit + date for each case
recs=[l for l in git("ls-tree","-r","--name-only",TIP).splitlines() if l.endswith("manual-verification.md")]
assert len(recs)==5, f"NON-VACUITY FAIL: expected 5 manual-verification.md, got {len(recs)}"
rec_commits={}
for r in recs:
    c=git("log","--diff-filter=A","--format=%H %cI",TIP,"--",r).strip().split("\n")[-1]
    rec_commits[r]=c.split()
print("manual-verification records, first-add commit:")
for r,(h,d) in sorted(rec_commits.items(),key=lambda x:x[1][1]):
    print(f"  {d}  {h[:8]}  {r}")
earliest=min(d for h,d in rec_commits.values())
print(f"\nEARLIEST manual-verification record anywhere: {earliest}")
out=[]
for c in sorted(cases):
    l=git("log","--diff-filter=A","--format=%H %cI",TIP,"--",c).strip().split("\n")
    l=[x for x in l if x]
    if not l:
        out.append((c,None,None)); continue
    h,d=l[-1].split()
    out.append((c,h,d))
assert all(x[1] for x in out), "NON-VACUITY FAIL: a case has no add commit"
# a case is 'earned' if SOME manual-verification record commit is a strict ancestor of its add commit
earned=[];unearned=[]
for c,h,d in out:
    ok=False
    for r,(rh,rd) in rec_commits.items():
        if rh!=h and subprocess.run(["git","-C",R,"merge-base","--is-ancestor",rh,h]).returncode==0:
            ok=True;break
    (earned if ok else unearned).append((c,h,d))
print(f"\ncases whose add-commit is strictly preceded by SOME manual-verification record: {len(earned)} of {len(out)}")
print(f"cases with NO preceding manual record:                                          {len(unearned)}")
byunit=collections.Counter(c.split("/")[1] for c,h,d in unearned)
print("\nunearned cases by top-level eval dir:")
for u,n in byunit.most_common(): print(f"  {u:22s} {n}")
print("\nearliest/latest add date among unearned:", min(d for c,h,d in unearned), max(d for c,h,d in unearned))
