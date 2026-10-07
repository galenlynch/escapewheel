"""The lookups a draft makes: DocDB and Code Ocean for a session's assets, S3 for what they hold.

- :func:`docdb_records` -- the raw asset's v2 record, and every record derived from it.
- :func:`codeocean_assets` -- the Code Ocean data assets of one subject.
- :func:`layout` -- what the chosen assets hold, read one known prefix at a time.

DocDB is read at `v2`, the store of record for schema 2.x; its client defaults to the legacy
`v1`. S3 is read anonymously, since only public buckets are read at all.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from typing import Any

from ..errors import DraftFault, DraftRefused
from .assets import Choice
from .draft import Layout

DOCDB_HOST = "api.allenneuraldynamics.org"
CODEOCEAN_DOMAIN = "https://codeocean.allenneuraldynamics.org"

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
    """List one S3 prefix, unsigned, one level deep."""
    import s3fs

    fs = s3fs.S3FileSystem(anon=True)

    def children(uri: str) -> list[str]:
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
    behavior = [n for n in children(f"{choice.raw.uri}/behavior") if n.startswith("behavior_")]
    for session in behavior:
        if "behavior-videos" in children(f"{choice.raw.uri}/behavior/{session}"):
            videos = f"{choice.raw.uri}/behavior/{session}/behavior-videos"
            break
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
        experiments, clipped, videos, nwb_file, tuple(f"{choice.sorted.uri}/nwb/{n}" for n in ephys), tuple(notes)
    )


__all__ = ["CODEOCEAN_DOMAIN", "DOCDB_HOST", "Lister", "codeocean_assets", "docdb_records", "layout", "s3_lister"]
