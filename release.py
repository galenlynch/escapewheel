"""Assemble what a release of this specification consists of, and record its digests.

The specification is not one document. A consumer implementing it needs the prose, the registry
the prose delegates to, the two meta-schemas that say what a registry and a manifest look like,
the extension registries, and the conformance corpus that settles what a validator must find.
Shipping the prose alone ships a document whose normative content is elsewhere.

    python release.py            # print the bundle and its digests
    python release.py --write    # also write RELEASE.json

Nothing is copied. The bundle is a manifest of paths and SHA-256 digests, so a consumer can
verify that the artifacts they hold are the ones the release names, and the repository stays the
single copy of each.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "RELEASE.json"

#: What a consumer needs, and why each is in the bundle rather than assumed.
PARTS: dict[str, tuple[str, ...]] = {
    "specification": ("nwb_lake_poc_docs_v0.2/NWB_Lake_POC_v0.2_Implementation_Spec.md",),
    "registry": ("registry/logical_schemas.json", "registry/tables.md"),
    "schemas": ("registry/registry.schema.json", "registry/manifest.schema.json"),
    "extensions": tuple(sorted(str(p.relative_to(ROOT)) for p in (ROOT / "registry/extensions").glob("*.json"))),
    "conformance": ("fixtures/build.py", "fixtures/corpus.py"),
    "provenance": ("nwb_lake_poc_docs_v0.2/applied.toml",),
}


def digest(path: Path) -> str:
    """SHA-256 of one file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def described() -> dict[str, object]:
    """The bundle: every part, its files, and what each hashes to."""
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=False).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True, check=False).stdout.strip()
    return {
        "standard": {
            "semantic": "nwb-lake-semantic-v0.1",
            "logical": "nwb-lake-logical-v0.1",
            "profile": "nwb-lake-portable-v0.1",
            "registry_version": json.loads((ROOT / "registry/logical_schemas.json").read_text())["registry_version"],
        },
        "commit": revision,
        # A release assembled from a dirty tree names files that are not what the commit holds.
        "clean": not dirty,
        "parts": {
            part: {name: digest(ROOT / name) for name in names}
            for part, names in PARTS.items()
        },
    }


def main() -> int:
    """Print the bundle, and write it where asked."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--write", action="store_true", help="write RELEASE.json")
    args = parser.parse_args()

    bundle = described()
    total = sum(len(files) for files in bundle["parts"].values())
    print(f"{total} files across {len(bundle['parts'])} parts, at {bundle['commit'][:12]}"
          f"{'' if bundle['clean'] else ' (WORKING TREE DIRTY)'}")
    for part, files in bundle["parts"].items():
        print(f"  {part}")
        for name, value in files.items():
            print(f"    {value[:12]}  {name}")
    if args.write:
        OUT.write_text(json.dumps(bundle, indent=2) + "\n")
        print(f"\nwrote {OUT.name}")
    return 0 if bundle["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
