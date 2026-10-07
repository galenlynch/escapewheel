"""Packets amended to a second version."""

import json
import shutil
from datetime import timedelta
from pathlib import Path

from .intervals import CUE_EXTENSION
from .numbering import Numbering
from .record import Build, Expected, Packet
from .registry import EXTENSION, KIND, REGISTRY
from .replacements import replaced
from .session import START, content, trial
from .writing import edit_manifest, write_packet


def amend(
    out: Path,
    make,
    change,
    *,
    extensions: tuple = (),
    identity: dict | None = None,
    superseded_identity: dict | None = None,
    dropped: tuple = (),
) -> None:
    """Write `make()`, then `change`'s edit of it over it at the next patch version (Part 05 §15.1).

    Each version binds the extensions it uses, so an edit adding an extension's table binds it. A
    table whose bytes the edit changes is written at a new uri beside the held file; every other
    entry is kept, and the superseded manifest's exact bytes are retained under `manifests/`
    (Part 03 §9). A name the packet holds keeps its number and a new one is numbered after them, as
    Part 05 §4.3 has an amending build number. `superseded_identity` sets packet-level fields of
    the first version; `identity` overrides, and `dropped` removes, those of the amended one.
    """
    held = write_packet(out, make(), extensions=extensions).keys
    if superseded_identity:
        edit_manifest(out, lambda manifest: manifest.update(superseded_identity))
    edited = make()
    change(edited)
    unheld = Numbering(REGISTRY, EXTENSION, *extensions)
    unheld.preassign(edited)
    numbers = {}
    for kind, names in unheld.keys.items():
        kept = held.get(kind, {})
        added = sorted((name for name in names if name not in kept), key=names.get)
        start = max(kept.values(), default=-1) + 1
        numbers[kind] = {**kept, **{name: start + i for i, name in enumerate(added)}}
    scratch = out.with_name(out.name + ".next")
    write_packet(scratch, edited, extensions=extensions, numbers=numbers)

    superseded = json.loads((out / "packet.json").read_text())
    major, minor, patch = superseded["packet_version"].split(".")
    following = f"{major}.{minor}.{int(patch) + 1}"
    manifest = json.loads((scratch / "packet.json").read_text())
    # Each version binds the extensions it uses (Part 04 §8), and one bound by both is bound alike.
    shared = manifest["registries"].keys() & superseded["registries"].keys()
    assert all(manifest["registries"][name] == superseded["registries"][name] for name in shared), out.name
    for name in manifest["registries"].keys() - shared:
        path = manifest["registries"][name]["path"]
        (out / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(scratch / path, out / path)
    before = {e["resource_id"]: e for e in superseded["resources"]}
    resources = []
    for entry in manifest["resources"]:
        kept = before.get(entry["resource_id"])
        if kept is not None and (out / kept["uri"]).read_bytes() == (scratch / entry["uri"]).read_bytes():
            resources.append(kept)
            continue
        uri = entry["uri"] if kept is None else entry["uri"].replace(".parquet", f".{following}.parquet")
        (out / uri).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(scratch / entry["uri"], out / uri)
        resources.append({**entry, "uri": uri})
    shutil.rmtree(scratch)
    (out / "manifests").mkdir()
    retained = out / "manifests" / f"{superseded['packet_version']}.json"
    retained.write_bytes((out / "packet.json").read_bytes())
    amended = {
        **superseded,
        "packet_version": following,
        "registries": manifest["registries"],
        "resources": resources,
        **(identity or {}),
    }
    for member in dropped:
        del amended[member]
    (out / "packet.json").write_text(json.dumps(amended, indent=2) + "\n")


def processing_run(run_id, activity, scope_kind, scope, hours):
    return {
        "processing_run_id": run_id,
        "session_id": "s001",
        "activity_type": activity,
        "scope_kind": scope_kind,
        "scope": scope,
        "software_name": "escapewheel",
        "software_version": "0.1.0",
        "status": "succeeded",
        "started_at": START + timedelta(hours=hours),
        "ended_at": START + timedelta(hours=hours, minutes=10),
    }


def scoped():
    # An import's scope is its session, so two imports of one session share a scope.
    c = content()
    c["core.processing_runs"][0] |= {"scope_kind": "core.sessions", "scope": "s001"}
    return c


def reimported(c):
    c["core.processing_runs"].append(processing_run("run_import_002", "import", "core.sessions", "s001", 30))


def curated(preferred=None):
    def make():
        c = scoped()
        c["core.processing_runs"].append(
            processing_run("run_curation_001", "curation", "core.sorting_runs", "sort_ks4_001", 4)
        )
        if preferred is not None:
            add_curation(c)
            c["core.preferred_runs"] = [preference(preferred)]
        return c

    return make


def preference(run_id):
    return {
        "session_id": "s001",
        "activity_type": "curation",
        "scope_kind": "core.sorting_runs",
        "scope": "sort_ks4_001",
        "processing_run_id": run_id,
        "reason": "the later curation",
        "chosen_at": START + timedelta(hours=31),
    }


def add_curation(c):
    """A second curation of the sorting run: new units, their spikes, contacts, windows and labels."""
    c["core.curation_versions"].append(
        {**c["core.curation_versions"][0], "curation_id": "curation_002", "created_at": START + timedelta(hours=29)}
    )
    held = [u for u in c["core.units"] if u["curation_id"] == "curation_001"]
    by_unit = {}
    for unit in held:
        name = f"recurated.{unit['unit_id']}"  # sorts after the held units, as the build numbers them
        by_unit[unit["unit_id"]] = name
        c["core.units"].append({**unit, "unit_id": name, "curation_id": "curation_002"})
    for table in (
        "core.spike_events",
        "core.unit_electrodes",
        "core.unit_observation_intervals",
        "core.unit_quality_labels",
    ):
        c[table] += [{**r, "unit_id": by_unit[r["unit_id"]]} for r in c[table] if r["unit_id"] in by_unit]
    c["core.processing_runs"].append(
        processing_run("run_curation_002", "curation", "core.sorting_runs", "sort_ks4_001", 29)
    )


def with_curation(c):
    add_curation(c)
    c["core.preferred_runs"] = [preference("run_curation_002")]
    reimported(c)


def tones(c):
    # 120 tones of a kind sorting before the trials, numbered after every interval the packet holds.
    for i in range(120):
        name = f"s001/cue.tones/{i + 1}"
        c["core.intervals"].append(
            {
                "session_id": "s001",
                "interval_kind": "cue.tones",
                "interval_id": name,
                "local_interval_label": str(i + 1),
                "start_tick": 100 + 90 * i,
                "stop_tick": 140 + 90 * i,
                "clock_id": "behavior_s001",
            }
        )
        c.setdefault("cue.tones", []).append({"session_id": "s001", "tone_id": name})
    reimported(c)


def another_trial(c):
    c["core.intervals"].append(
        {
            **c["core.intervals"][1],
            "interval_id": trial(3),
            "local_interval_label": "3",
            "start_tick": 10500,
            "stop_tick": 11500,
        }
    )
    c[KIND].append({**c[KIND][1], "trial_id": trial(3)})
    reimported(c)


def moved_trial(c):
    c["core.intervals"][0]["stop_tick"] = 5500
    reimported(c)


def held_unit_observed_again(c):
    # Unit 2's dropout, observed after all: its windows are one group the packet holds.
    c["core.unit_observation_intervals"].append(
        {"session_id": "s001", "unit_id": 2, "start_tick": 125_000, "stop_tick": 145_000}
    )
    reimported(c)


def replacing(packet_id):
    # The first version replaces version 0.1.0 of its own packet_id, so it is at 1.0.0.
    return {"packet_version": "1.0.0", "replaces": [replaced(packet_id)]}


def repreferred(c):
    c["core.preferred_runs"] = [preference("run_curation_001")]
    reimported(c)


def amended(make, change, **options) -> Build:
    """A build of `amend`."""

    def build(out: Path) -> None:
        amend(out, make, change, **options)

    return build


def two_imports(out: Path) -> None:
    c = scoped()
    reimported(c)
    write_packet(out, c)


def preference_of_another_scope(out: Path) -> None:
    # A preference whose run curated the probe, not the sorting run the preference names.
    c = curated()()
    c["core.processing_runs"].append(processing_run("run_curation_002", "curation", "core.probes", "probe0", 29))
    c["core.preferred_runs"] = [preference("run_curation_002")]
    write_packet(out, c)


#: Part 05 §15.2's amendments: each adds groups a packet lacks, or breaks one rule of adding.
AMENDMENT_PACKETS = (
    Packet("amended_intervals", amended(scoped, tones, extensions=(CUE_EXTENSION,))),
    Packet("amended_curation", amended(curated(), with_curation)),
    Packet("amended_preference", amended(curated("run_curation_002"), repreferred)),
    Packet("amended_trial", amended(scoped, another_trial), Expected("error", "amendment.group_grown")),
    Packet("amended_trial_bounds", amended(scoped, moved_trial), Expected("error", "amendment.row_changed")),
    Packet(
        "amended_unit_window",
        amended(scoped, held_unit_observed_again),
        Expected("error", "amendment.group_grown"),
    ),
    Packet(
        "amended_packet_id",
        amended(scoped, reimported, identity={"packet_id": "another_packet"}),
        Expected("error", "amendment.identity_changed"),
    ),
    Packet(
        "amended_replacement",
        amended(scoped, reimported, superseded_identity=replacing("amended_replacement")),
    ),
    Packet(
        "amended_replacement_unlinked",
        amended(
            scoped,
            reimported,
            superseded_identity=replacing("amended_replacement_unlinked"),
            dropped=("replaces",),
        ),
        Expected("error", "amendment.identity_changed"),
    ),
    Packet(
        "amended_replacement_major",
        amended(
            scoped,
            reimported,
            superseded_identity=replacing("amended_replacement_major"),
            identity={"packet_version": "2.0.0"},
        ),
        Expected("error", "amendment.identity_changed"),
    ),
    Packet("two_imports", two_imports),
    Packet(
        "preference_of_another_scope",
        preference_of_another_scope,
        Expected("error", "core.preferred_runs.scope_matches_run"),
    ),
)
