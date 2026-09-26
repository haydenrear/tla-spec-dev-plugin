#!/usr/bin/env python3
"""Pinned word-count instrument for GOAL-progressive-disclosure.

bodies:       awk 'BEGIN{fm=0} /^---$/{fm++; next} fm>=2'  <=> drop frontmatter, wc -w
descriptions: the YAML-parsed `description` scalar, .split()
Runs over a git REF via `git show`, so it can measure any commit.
"""
import subprocess, sys, json, io
import yaml

print("sys.executable:", sys.executable, file=sys.stderr)

REPO = sys.argv[1]
REF  = sys.argv[2]

def git(*a):
    return subprocess.run(["git","-C",REPO,*a],capture_output=True,text=True,check=True).stdout

# population: every skills/<u>/SKILL.md at that ref
files = [l for l in git("ls-tree","-r","--name-only",REF).splitlines()
         if l.startswith("skills/") and l.endswith("/SKILL.md") and l.count("/")==2]
assert files, f"NON-VACUITY FAIL: no skills/*/SKILL.md found at {REF}"

def body_words(text):
    # exact awk semantics: count '---' lines, emit lines once fm>=2, skipping the --- lines
    fm=0; out=[]
    for line in text.split("\n"):
        if line.rstrip("\r")=="---":
            fm+=1; continue
        if fm>=2: out.append(line)
    return len("\n".join(out).split())

rows={}
for f in sorted(files):
    unit=f.split("/")[1]
    text=git("show",f"{REF}:{f}")
    b=body_words(text)
    # frontmatter = between first and second ---
    parts=text.split("\n")
    fm_lines=[];fm=0
    for line in parts:
        if line.rstrip("\r")=="---":
            fm+=1
            if fm>=2: break
            continue
        if fm==1: fm_lines.append(line)
    assert fm>=2, f"NON-VACUITY FAIL: {f} at {REF} has no closing frontmatter delimiter"
    meta=yaml.safe_load("\n".join(fm_lines)) or {}
    desc=meta.get("description")
    assert desc, f"NON-VACUITY FAIL: {f} at {REF} has no description scalar"
    rows[unit]={"desc":len(str(desc).split()),"body":b}

assert len(rows)==len(files), "NON-VACUITY FAIL: row/file count mismatch"
tot_d=sum(r["desc"] for r in rows.values()); tot_b=sum(r["body"] for r in rows.values())
over=[u for u,r in rows.items() if r["body"]>1500]
print(json.dumps({"ref":REF,"resolved":git("rev-parse","--short",REF).strip(),
                  "units":len(rows),"rows":rows,"desc_total":tot_d,"body_total":tot_b,
                  "bodies_over_1500":over,"n_over":len(over)},indent=2))
