import subprocess,sys
print("sys.executable:",sys.executable)
R="/Users/hayde/IdeaProjects/wt-372-evaluation-b"
def git(*a,check=True):
    p=subprocess.run(["git","-C",R,*a],capture_output=True,text=True)
    if check and p.returncode!=0: raise SystemExit(f"git {a} rc={p.returncode} {p.stderr}")
    return p
rungs=[("SI-19","8e362bbb","eefe3aa8"),("SI-20","70549f90","7daa8e18"),
       ("SI-21","bec1934b","c96de147"),("SI-22","679f76f1","3dc106fb"),
       ("SI-29","f8a3994e","b929e07c")]
assert len(rungs)==5, "NON-VACUITY: expected 5 rungs"
print(f"{'rung':7s} {'record':9s} {'first-case':10s} anc  record_has_case.yaml  case_commit_adds_cases")
ok=0
for t,rec,case in rungs:
    # both commits must exist
    for c in (rec,case):
        assert git("cat-file","-e",c+"^{commit}",check=False).returncode==0, f"NON-VACUITY: {c} not a commit"
    anc=git("merge-base","--is-ancestor",rec,case,check=False).returncode
    strict = anc==0 and git("rev-parse",rec).stdout.strip()!=git("rev-parse",case).stdout.strip()
    recfiles=git("show","--name-only","--pretty=format:",rec).stdout.split()
    reccase=[f for f in recfiles if f.endswith("case.yaml")]
    casefiles=git("show","--name-only","--pretty=format:",case).stdout.split()
    addcase=[f for f in casefiles if f.endswith("case.yaml")]
    assert recfiles, f"NON-VACUITY: record commit {rec} touched no files"
    assert casefiles, f"NON-VACUITY: case commit {case} touched no files"
    print(f"{t:7s} {rec:9s} {case:10s} rc={anc} strict={strict}  record_cases={len(reccase)}  case_commit_cases={len(addcase)}")
    if strict and not reccase and addcase: ok+=1
print(f"\nrungs satisfying [record strictly precedes cases, record contains 0 case.yaml, case commit adds >=1]: {ok} of 5")
