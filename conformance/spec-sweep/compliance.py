import pathlib
import json, re, pathlib
T = json.load(open(str(pathlib.Path(__file__).parent/"tables02.json")))
t09 = pathlib.Path("nwb_lake_poc_docs/09_metadata_minimalism_and_extensions.md").read_text()

covered = sorted({m.group(1) for m in re.finditer(r"`(core\.[a-z_]+)`\s+(?:MUST|SHOULD|MAY)\s+include", t09)})
print("09 §4 field-list coverage:", ", ".join(c.replace("core.","") for c in covered))
print("02 tables NOT restated in 09 §4:", ", ".join(sorted(set(T) - set(covered))).replace("core.",""), "\n")

R3_COVERED = {"experimenter","tags","shape","dimension_names","dtype","transform_to_parent",
              "spike_ticks","payload","parameters","metadata"}
print("=== R3 §2.1 compliance: nested-typed columns in 02 ===")
miss = []
for tbl, cols in sorted(T.items()):
    for c,(ty,req) in cols.items():
        if any(k in ty for k in ("list<","struct","map","json_string")):
            flag = "" if c in R3_COVERED else "  <-- NOT IN R3 §2.2"
            if flag: miss.append((tbl,c,ty))
            print(f"  {tbl+'.'+c:44s} {ty:34s} req={req}{flag}")
print(f"\n  unlisted in R3 §2.2: {len(miss)}")

print("\n=== timestamp/date columns (R3 §2.1 wall-clock rule) ===")
for tbl, cols in sorted(T.items()):
    for c,(ty,req) in cols.items():
        if "timestamp" in ty or ty.strip()=="date" or "date" in ty:
            print(f"  {tbl+'.'+c:44s} {ty}")

print("\n=== *_index columns (R3 §6 classification) ===")
STRUCT={"channel_index","frame_index","axis_index"}; LABEL={"local_electrode_index","local_channel_index","local_unit_index"}
for tbl, cols in sorted(T.items()):
    for c in cols:
        if c.endswith("_index"):
            k = "structural" if c in STRUCT else "source label" if c in LABEL else "UNCLASSIFIED"
            print(f"  {tbl+'.'+c:44s} {k}")

print("\n=== tick columns (R3 §2.1 signed int64) ===")
bad=[]
for tbl, cols in sorted(T.items()):
    for c,(ty,req) in cols.items():
        if c.endswith("_tick") and ty.strip()!="int64": bad.append((tbl,c,ty))
print(f"  {sum(1 for t,cs in T.items() for c in cs if c.endswith('_tick'))} tick columns; non-int64: {bad or 'none'}")
