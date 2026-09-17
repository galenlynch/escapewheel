# Spec sweep

Mechanical checks over the frozen specification. Produces the evidence in
[R4](../../revisions/accepted/R4-schema-reconciliation.md). Run from the repository root.

```bash
python3 conformance/spec-sweep/sweep.py       # 09 vs 02 drift, requirement mismatches
python3 conformance/spec-sweep/compliance.py  # 02 against R3's rules
```

`sweep.py` writes `tables02.json`, the parsed column set, which `compliance.py` reads.
Re-run both after any revision touching Part 02 or Part 09.
