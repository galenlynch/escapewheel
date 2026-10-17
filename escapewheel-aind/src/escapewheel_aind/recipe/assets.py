"""The data assets one session's recipe can read, and which of them it reads.

- :class:`Asset` -- one asset, public or not, and what it was derived from.
- :func:`from_docdb` and :func:`from_codeocean` -- an asset from either catalogue's record.
- :func:`mirrored` -- private assets given the location of a readable copy.
- :func:`choose` -- the sorted asset and the NWB a recipe reads, and the candidates passed over.

A recipe reads only assets in a public bucket, or a copy `mirrored` names: a packet names where
each source lives, and a private location is one its readers cannot open.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any, Literal

from ..errors import DraftFault, DraftRefused

#: Buckets a recipe may read from, each anonymously.
PUBLIC_BUCKETS = frozenset({"aind-open-data"})

#: `<raw>_<process>_<YYYY-MM-DD>_<HH-MM-SS>`, the name AIND gives a derived asset.
DERIVED = re.compile(r"^(?P<raw>.+?)_(?P<process>sorted|nwb)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{2}-\d{2}-\d{2})$")

Level = Literal["raw", "sorted", "nwb"]


@dataclass(frozen=True)
class Asset:
    """One data asset of a session.

    Attributes
    ----------
    name : str
        The asset's name, which both catalogues key on.
    level : {"raw", "sorted", "nwb"}
        What it holds.
    uri : str or None
        Its `s3://` prefix, or None where no public bucket holds it.
    made : str or None
        When its processing ran, as its name spells it (`2026-07-29_16-03-08`), which sorts as the
        time does; None for a raw asset.
    sorted_from : str or None
        For an NWB, the sorted asset it was built from, where a catalogue records it.
    """

    name: str
    level: Level
    uri: str | None
    made: str | None = None
    sorted_from: str | None = None

    @property
    def public(self) -> bool:
        """Whether a recipe may read it."""
        return self.uri is not None


def _public(uri: str | None) -> str | None:
    if uri is None or not uri.startswith("s3://"):
        return None
    bucket = uri.removeprefix("s3://").split("/", 1)[0]
    return uri.rstrip("/") if bucket in PUBLIC_BUCKETS else None


def classify(name: str, raw: str) -> tuple[Level, str | None] | None:
    """Return what `name` holds and when it was made, or None if it is not one of `raw`'s assets."""
    if name == raw:
        return "raw", None
    match = DERIVED.match(name)
    if match is None or match["raw"] != raw:
        return None
    made = f"{match['date']}_{match['time']}"
    return ("sorted" if match["process"] == "sorted" else "nwb"), made


def from_docdb(record: Mapping[str, Any], raw: str) -> Asset | None:
    """Read an asset from a DocDB v2 record, or return None if the record is not one of `raw`'s assets."""
    name = str(record.get("name", ""))
    sources = (record.get("data_description") or {}).get("source_data") or []
    found = classify(name, raw)
    if found is None and raw in sources and (match := DERIVED.match(name)):
        # A derived name can abbreviate its raw asset's; the record's source data still names it.
        found = classify(name, match["raw"])
    if found is None:
        return None
    level, made = found
    parents = [s for s in sources if (parent := classify(str(s), raw)) is not None and parent[0] == "sorted"]
    sorted_from = str(parents[0]) if level == "nwb" and parents else None
    return Asset(str(record["name"]), level, _public(record.get("location")), made, sorted_from)


def from_codeocean(asset: Any, raw: str) -> Asset | None:
    """Read an asset from a Code Ocean data asset, or return None if it is not one of `raw`'s assets.

    An asset stored inside Code Ocean has no `source_bucket` and is private; one attached from
    S3 names its bucket and prefix there.
    """
    found = classify(str(asset.name), raw)
    if found is None:
        return None
    level, made = found
    bucket = asset.source_bucket
    uri = f"s3://{bucket.bucket}/{bucket.prefix}" if bucket is not None and bucket.bucket else None
    parameters = {p.name: p.value for p in (asset.app_parameters or [])}
    sorted_from = parameters.get("sorted_asset") if level == "nwb" else None
    return Asset(str(asset.name), level, _public(uri), made, sorted_from)


def merged(assets: Iterable[Asset]) -> dict[str, Asset]:
    """One asset per name, keeping a public location and a recorded parent from whichever states one."""
    by_name: dict[str, Asset] = {}
    for asset in assets:
        held = by_name.get(asset.name)
        if held is None:
            by_name[asset.name] = asset
            continue
        by_name[asset.name] = Asset(
            asset.name,
            asset.level,
            held.uri or asset.uri,
            held.made or asset.made,
            held.sorted_from or asset.sorted_from,
        )
    return by_name


def mirrored(assets: Mapping[str, Asset], mirrors: Mapping[str, str]) -> tuple[dict[str, Asset], list[str]]:
    """Give each private asset named in `mirrors` its copy's location, and say so for each."""
    out = dict(assets)
    notes = []
    for name, uri in sorted(mirrors.items()):
        asset = assets.get(name)
        if asset is not None and not asset.public:
            out[name] = replace(asset, uri=uri.rstrip("/"))
            notes.append(f"{name} is private and read from a copy at {uri}")
    return out, notes


@dataclass(frozen=True)
class Choice:
    """The assets a recipe reads, and what a reader of it should know about the rest."""

    raw: Asset
    sorted: Asset
    nwb: Asset | None
    notes: tuple[str, ...]


def _newest(assets: list[Asset]) -> Asset:
    return max(assets, key=lambda a: (a.made or "", a.name))


def _pinned(assets: Mapping[str, Asset], name: str, level: Level) -> Asset:
    asset = assets.get(name)
    if asset is None or asset.level != level:
        raise DraftRefused(f"{name}: no {level} asset of this session has that name", code=DraftFault.PINNED_ASSET)
    if not asset.public:
        raise DraftRefused(
            f"{name}: stored in no public bucket, so a recipe cannot read it", code=DraftFault.PINNED_ASSET
        )
    return asset


def choose(
    assets: Mapping[str, Asset], raw: str, *, sorted_name: str | None = None, nwb_name: str | None = None
) -> Choice:
    """Choose the sorted asset and the NWB a recipe reads.

    The newest public sorted asset, unless `sorted_name` pins one. The NWB is the newest public
    one built from that sorting, unless `nwb_name` pins one; an NWB whose parent no catalogue
    records is taken only where it is the session's sole public NWB.

    Raises
    ------
    DraftRefused
        If the raw asset or every sorted asset is private or absent, or a pinned name is.
    """
    notes: list[str] = []
    raw_asset = assets.get(raw)
    if raw_asset is None or not raw_asset.public:
        raise DraftRefused(f"{raw}: the raw asset is in no public bucket", code=DraftFault.NO_PUBLIC_ASSET)
    for asset in sorted(assets.values(), key=lambda a: a.name):
        if not asset.public:
            notes.append(f"{asset.name} is stored in no public bucket, so it is not read")
    sorted_assets = [a for a in assets.values() if a.level == "sorted" and a.public]
    if sorted_name is not None:
        chosen = _pinned(assets, sorted_name, "sorted")
    elif sorted_assets:
        chosen = _newest(sorted_assets)
    else:
        raise DraftRefused(f"{raw}: no sorted asset is in a public bucket", code=DraftFault.NO_PUBLIC_ASSET)
    notes += [
        f"{a.name} is an older sorting, passed over" for a in sorted(sorted_assets, key=lambda a: a.name) if a != chosen
    ]

    nwbs = [a for a in assets.values() if a.level == "nwb" and a.public]
    nwb: Asset | None
    if nwb_name is not None:
        nwb = _pinned(assets, nwb_name, "nwb")
        if nwb.sorted_from not in (None, chosen.name):
            notes.append(f"{nwb.name} was built from {nwb.sorted_from}, not from {chosen.name}")
    elif built := [a for a in nwbs if a.sorted_from == chosen.name]:
        nwb = _newest(built)
    elif len(nwbs) == 1 and nwbs[0].sorted_from is None:
        nwb = nwbs[0]
        notes.append(f"{nwb.name} records no sorting it was built from; it is the session's only public NWB")
    else:
        nwb = None
    notes += [f"{a.name} is an NWB passed over" for a in sorted(nwbs, key=lambda a: a.name) if a != nwb]
    return Choice(raw_asset, chosen, nwb, tuple(notes))


__all__ = [
    "DERIVED",
    "PUBLIC_BUCKETS",
    "Asset",
    "Choice",
    "choose",
    "classify",
    "from_codeocean",
    "from_docdb",
    "merged",
    "mirrored",
]
