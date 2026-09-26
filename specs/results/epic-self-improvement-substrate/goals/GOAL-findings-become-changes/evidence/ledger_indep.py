import sys,yaml,re,collections
print("sys.executable:",sys.executable)
p="/Users/hayde/IdeaProjects/wt-372-evaluation-b/specs/results/deferred_findings_final.yaml"
d=yaml.safe_load(open(p))
# find the row list
rows=None
if isinstance(d,list): rows=d
elif isinstance(d,dict):
    for k,v in d.items():
        if isinstance(v,list) and len(v)>50: rows=v; print("row key:",k); break
assert rows is not None, "NON-VACUITY FAIL: could not locate row list"
assert len(rows)>100, f"NON-VACUITY FAIL: only {len(rows)} rows, expected ~151"
print("rows in deferred_findings_final.yaml:",len(rows))
VERB=re.compile(r'^\s*(applied|declined|proposed|none)\b')
c=collections.Counter(); absent=0; malformed=0; parse=0
for r in rows:
    if not isinstance(r,dict): continue
    if "skill_change" not in r or r.get("skill_change") in (None,""):
        absent+=1; c["absent"]+=1; continue
    v=str(r["skill_change"])
    m=VERB.match(v)
    if m:
        # ledger treats two verbs in one value as malformed
        verbs=re.findall(r'\b(applied|declined|proposed|none)\s*\(',v)
        if len(verbs)>1: malformed+=1; c["malformed(multi-verb)"]+=1
        else: parse+=1; c[m.group(1)]+=1
    else:
        malformed+=1; c["malformed"]+=1
print("\nindependent count over deferred_findings_final.yaml ONLY:")
for k,v in sorted(c.items()): print(f"  {k:22s} {v}")
print(f"  parseable            {parse}")
print(f"  absent               {absent}")
print(f"  malformed            {malformed}")
print(f"\n  parseable/rows = {parse}/{len(rows)} = {100*parse/len(rows):.1f}%")
