"""Explore a possible specification bundle and print its digests.

This is a non-authoritative design probe, not a release or publication tool. It inventories one
candidate bundle so its composition can be discussed without creating a tracked release snapshot.

    python prototype/release-bundle/probe.py

Nothing is copied or written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: What a consumer needs, and why each is in the bundle rather than assumed.
PARTS: dict[str, tuple[str, ...]] = {
    "specification": (
        "escapewheel_poc_docs_v0.2/Escapewheel_POC_v0.2_Implementation_Spec.md",
    ),
    "registry": ("registry/logical_schemas.json", "registry/tables.md"),
    "schemas": ("registry/registry.schema.json", "registry/manifest.schema.json"),
    "extensions": tuple(
        sorted(
            str(p.relative_to(ROOT))
            for p in (ROOT / "registry/extensions").glob("*.json")
        )
    ),
    "conformance": ("fixtures/build.py", "fixtures/corpus.py"),
    "provenance": ("revisions/applied.toml",),
}


def digest(path: Path) -> str:
    """SHA-256 of one file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def described() -> dict[str, object]:
    """The bundle: every part, its files, and what each hashes to."""
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    return {
        "standard": {
            "semantic": "escapewheel-semantic-v0.1",
            "logical": "escapewheel-logical-v0.1",
            "profile": "escapewheel-portable-v0.1",
            "registry_version": json.loads(
                (ROOT / "registry/logical_schemas.json").read_text()
            )["registry_version"],
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
    """Print the candidate bundle without writing repository state."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.parse_args()

    bundle = described()
    total = sum(len(files) for files in bundle["parts"].values())
    print(
        f"{total} files across {len(bundle['parts'])} parts, at {bundle['commit'][:12]}"
        f"{'' if bundle['clean'] else ' (WORKING TREE DIRTY)'}"
    )
    for part, files in bundle["parts"].items():
        print(f"  {part}")
        for name, value in files.items():
            print(f"    {value[:12]}  {name}")
    return 0 if bundle["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
