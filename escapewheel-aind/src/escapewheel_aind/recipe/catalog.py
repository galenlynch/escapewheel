"""The lookups a draft makes: DocDB and Code Ocean for a session's assets, S3 for what they hold.

- :func:`docdb_records` -- the raw asset's v2 record, and every record derived from it.
- :func:`codeocean_assets` -- the Code Ocean data assets of one subject.
- :func:`layout` -- what the chosen assets hold, read one known prefix at a time.

DocDB is read at `v2`, the store of record for schema 2.x; its client defaults to the legacy
`v1`. A public bucket is read anonymously.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from typing import Any

from ..errors import DraftFault, DraftRefused
from .assets import PUBLIC_BUCKETS, Choice
from .draft import Layout

DOCDB_HOST = "api.allenneuraldynamics.org"
CODEOCEAN_DOMAIN = "https://codeocean.allenneuraldynamics.org"

#: The sniff detector's RawVoltage register, as a HARP logger names its file.
SNIFF_REGISTER = "SniffDetector__32.bin"

#: Lists one prefix's immediate children, as names without the prefix. Injected for tests.
Lister = Callable[[str], list[str]]


def docdb_records(raw: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return the raw asset's record, and the records naming it as source data."""
    from aind_data_access_api.document_db import MetadataDbClient

    client = MetadataDbClient(host=DOCDB_HOST, version="v2")
    found = client.retrieve_docdb_records(filter_query={"name": raw})
    if not found:
        raise DraftRefused(f"{raw}: DocDB v2 holds no record of that name", code=DraftFault.NO_RAW_RECORD)
    derived = client.retrieve_docdb_records(
        filter_query={"data_description.source_data": raw},
        projection={"name": 1, "location": 1, "data_description.source_data": 1},
    )
    return dict(found[0]), [dict(r) for r in derived]


def codeocean_assets(subject_id: str) -> Iterable[Any]:
    """Every result asset Code Ocean finds for `subject_id`, which the caller filters by name.

    Search by subject rather than by name, since a name query matches whole tokens only and
    finds no `<raw>_sorted_…` from `<raw>`. The token is read from `CODEOCEAN_API_TOKEN`.
    """
    from codeocean import CodeOcean
    from codeocean.data_asset import DataAssetSearchParams, DataAssetType

    token = os.environ.get("CODEOCEAN_API_TOKEN")
    if not token:
        raise DraftRefused(
            "CODEOCEAN_API_TOKEN is unset; pass --no-codeocean to draft from DocDB alone",
            code=DraftFault.NO_CODEOCEAN_TOKEN,
        )
    client = CodeOcean(domain=CODEOCEAN_DOMAIN, token=token, retries=3)
    return list(
        client.data_assets.search_data_assets_iterator(
            DataAssetSearchParams(query=subject_id, type=DataAssetType.Result)
        )
    )


def s3_lister() -> Lister:
    """List one S3 prefix one level deep: a public bucket unsigned, a mirror's with ambient credentials."""
    import s3fs

    unsigned, signed = s3fs.S3FileSystem(anon=True), s3fs.S3FileSystem()

    def children(uri: str) -> list[str]:
        bucket = uri.removeprefix("s3://").split("/", 1)[0]
        fs = unsigned if bucket in PUBLIC_BUCKETS else signed
        try:
            return sorted(entry.rstrip("/").rsplit("/", 1)[-1] for entry in fs.ls(uri.rstrip("/") + "/", refresh=True))
        except FileNotFoundError:
            return []

    return children


def layout(choice: Choice, children: Lister) -> Layout:
    """Read what the chosen assets hold, listing only prefixes whose names are known."""
    assert choice.raw.uri is not None and choice.sorted.uri is not None
    notes: list[str] = []
    curated = children(f"{choice.sorted.uri}/curated")
    experiments = sorted({name.split("_", 1)[0] for name in curated if name.startswith("experiment")})
    if "postprocessed" not in children(choice.sorted.uri):
        notes.append("the sorted asset has no postprocessed/, so core.sorting_run_channels stays empty")
    clipped = "ecephys_clipped" in children(f"{choice.raw.uri}/ecephys")
    videos = None
    behavior_uri = f"{choice.raw.uri}/behavior"
    held = children(behavior_uri)
    behavior = [n for n in held if n.startswith("behavior_") and not n.endswith(".harp")]
    for session in behavior:
        if "behavior-videos" in children(f"{behavior_uri}/{session}"):
            videos = f"{behavior_uri}/{session}/behavior-videos"
            break
    # A newer upload holds one session's files directly: the JSON in `behavior/`, the videos beside it.
    if videos is None and "behavior-videos" in children(choice.raw.uri):
        videos = f"{choice.raw.uri}/behavior-videos"
    behavior_json, json_notes = _behavior_json(behavior_uri, held, behavior, children)
    notes += json_notes
    # A rig logs the detector either in its own folder or beside the GUI's.
    harp = [f"{behavior_uri}/Sniffing/{n}" for n in children(f"{behavior_uri}/Sniffing") if n.endswith(".harp")]
    harp += [f"{behavior_uri}/{n}" for n in held if n.startswith("behavior_sniffing") and n.endswith(".harp")]
    sniffs = [folder for folder in harp if SNIFF_REGISTER in children(folder)]
    if len(sniffs) > 1:
        notes.append(f"{len(sniffs)} folders hold {SNIFF_REGISTER}; the recipe reads {sniffs[-1]}: GUESS")
    ephys = sorted(n for n in children(f"{choice.sorted.uri}/nwb") if n.endswith(".nwb"))
    nwb_file = None
    if choice.nwb is not None and choice.nwb.uri is not None:
        stores = [n for n in children(choice.nwb.uri) if n.endswith(".nwb")]
        named = [n for n in stores if "experiment1" in n] or stores
        if named:
            nwb_file = f"{choice.nwb.uri}/{named[0]}"
            if len(stores) > 1:
                notes.append(f"{choice.nwb.name} holds {len(stores)} NWB stores; the recipe reads {named[0]}")
        else:
            notes.append(f"{choice.nwb.name} holds no .nwb store, so no NWB is read")
    return Layout(
        experiments,
        clipped,
        videos,
        nwb_file,
        tuple(f"{choice.sorted.uri}/nwb/{n}" for n in ephys),
        behavior_json=behavior_json,
        sniff=sniffs[-1] if sniffs else None,
        notes=tuple(notes),
    )


def _behavior_json(
    behavior_uri: str, held: list[str], sessions: list[str], children: Lister
) -> tuple[str | None, list[str]]:
    """Return the GUI's JSON, `<subject>_<date>_<time>.json` in `behavior/` or a session folder's.

    A restarted GUI leaves a session folder per start, and the last is read.
    """
    found = [f"{behavior_uri}/{name}" for name in held if _is_gui_json(name)]
    found += [
        f"{behavior_uri}/{session}/behavior/{name}"
        for session in sessions
        for name in children(f"{behavior_uri}/{session}/behavior")
        if _is_gui_json(name)
    ]
    if len(found) > 1:
        return found[-1], [f"{len(found)} behavior JSONs, one per start of the GUI; the recipe reads the last: GUESS"]
    return (found[0] if found else None), []


def _is_gui_json(name: str) -> bool:
    return name.endswith(".json") and name[:1].isdigit()


__all__ = [
    "CODEOCEAN_DOMAIN",
    "DOCDB_HOST",
    "SNIFF_REGISTER",
    "Lister",
    "codeocean_assets",
    "docdb_records",
    "layout",
    "s3_lister",
]
