import json
import pathlib
import re

D = pathlib.Path("revisions/baseline-v0.1")
t02 = (D / "02_core_logical_schemas.md").read_text()
t09 = (D / "09_metadata_minimalism_and_extensions.md").read_text()

# --- parse 02: table -> {col: (type, required)} ---
tables, cur = {}, None
for line in t02.splitlines():
    m = re.match(r"^## `(core\.[a-z_]+)`", line)
    if m:
        cur = m.group(1)
        tables[cur] = {}
        continue
    if line.startswith("## ") or line.startswith("# "):
        if not re.match(r"^### ", line):
            cur = cur if line.startswith("### ") else None
    m = re.match(r"^\|\s*`([a-z_0-9]+)`\s*\|\s*([^|]+?)\s*\|\s*([a-z]+)\s*\|", line)
    if m and cur:
        tables[cur][m.group(1)] = (m.group(2).strip(), m.group(3).strip())
# provenance subsections use ###
for m in re.finditer(r"^### `(core\.[a-z_]+)`\n(.*?)(?=\n#{2,3} |\Z)", t02, re.S | re.M):
    name, body = m.group(1), m.group(2)
    tables.setdefault(name, {})
    for lm in re.finditer(r"^\|\s*`([a-z_0-9]+)`\s*\|\s*([^|]+?)\s*\|\s*([a-z]+)\s*\|", body, re.M):
        tables[name][lm.group(1)] = (lm.group(2).strip(), lm.group(3).strip())

print(f"02 defines {len(tables)} tables, {sum(len(v) for v in tables.values())} columns\n")

# --- parse 09 section 4: `core.X` MUST/SHOULD/MAY include: ```text ... ``` ---
claims = []
for m in re.finditer(
    r"`(core\.[a-z_]+)`\s+(MUST|SHOULD|MAY)\s+include[^:]*:\s*\n+```text\n(.*?)```",
    t09,
    re.S,
):
    tbl, lvl, body = m.group(1), m.group(2), m.group(3)
    for f in [x.strip() for x in body.splitlines() if x.strip()]:
        claims.append((tbl, lvl, f))
print(f"09 §4 makes {len(claims)} field claims across {len({c[0] for c in claims})} tables\n")

print("=== DRIFT: field named in 09 but absent from 02 ===")
drift = False
for tbl, lvl, f in claims:
    if tbl in tables and f not in tables[tbl]:
        print(f"  {tbl:26s} {lvl:6s} {f}")
        drift = True
if not drift:
    print("  (none)")

print("\n=== REQUIREMENT MISMATCH: 09 says MUST, 02 says not required ===")
mm = False
for tbl, lvl, f in claims:
    if lvl == "MUST" and tbl in tables and f in tables[tbl]:
        req = tables[tbl][f][1]
        if req != "yes":
            print(f"  {tbl:26s} {f:24s} 02 required={req}")
            mm = True
if not mm:
    print("  (none)")
json.dump(
    {k: v for k, v in tables.items()},
    open(str(pathlib.Path(__file__).parent / "tables02.json"), "w"),
    indent=1,
)
