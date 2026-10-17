"""The recipe drafter: which assets it reads, how it reads their times, and what it renders."""

import tomllib
from dataclasses import replace
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from escapewheel_aind.errors import DraftRefused
from escapewheel_aind.recipe import assets, catalog, draft, facts

RAW = "ecephys_786867_2025-09-25_12-43-56"
OPEN = "s3://aind-open-data"
ZONE = ZoneInfo("America/Los_Angeles")


def _record(name, location, source_data=None):
    return {"name": name, "location": location, "data_description": {"source_data": source_data}}


def _co(name, bucket=None, prefix=None, **parameters):
    source = SimpleNamespace(bucket=bucket, prefix=prefix) if bucket else None
    listed = [SimpleNamespace(name=k, value=v) for k, v in parameters.items()]
    return SimpleNamespace(name=name, source_bucket=source, app_parameters=listed)


def _catalogue(*more):
    found = [
        assets.from_docdb(_record(RAW, f"{OPEN}/{RAW}"), RAW),
        assets.from_docdb(
            _record(f"{RAW}_sorted_2025-12-24_08-46-14", f"{OPEN}/{RAW}_sorted_2025-12-24_08-46-14"), RAW
        ),
        assets.from_docdb(
            _record(f"{RAW}_sorted_2026-07-29_16-03-08", f"{OPEN}/{RAW}_sorted_2026-07-29_16-03-08"), RAW
        ),
        # Stored inside Code Ocean, and newer than either public sorting.
        assets.from_docdb(_record(f"{RAW}_sorted_2026-09-01_00-00-00", "s3://codeocean-s3datasetsbucket-x/abc"), RAW),
        *more,
    ]
    return assets.merged(a for a in found if a is not None)


def test_a_name_is_classified_against_its_raw_asset():
    assert assets.classify(RAW, RAW) == ("raw", None)
    assert assets.classify(f"{RAW}_nwb_2026-08-18_13-28-44", RAW) == ("nwb", "2026-08-18_13-28-44")
    assert assets.classify("ecephys_786867_2025-09-26_12-48-15_sorted_2026-04-24_09-25-26", RAW) is None
    assert assets.classify(f"{RAW}_ccg_2026-04-25-23-39-00", RAW) is None


def test_the_newest_public_sorting_is_read_and_a_private_one_is_reported():
    choice = assets.choose(_catalogue(), RAW)
    assert choice.sorted.name == f"{RAW}_sorted_2026-07-29_16-03-08"
    assert f"{RAW}_sorted_2026-09-01_00-00-00 is stored in no public bucket, so it is not read" in choice.notes
    assert f"{RAW}_sorted_2025-12-24_08-46-14 is an older sorting, passed over" in choice.notes
    assert choice.nwb is None


def test_a_name_abbreviating_its_raw_asset_is_read_by_its_source_data():
    short = f"{RAW[:-9]}_sorted_2026-04-23_14-11-00"
    asset = assets.from_docdb(_record(short, f"{OPEN}/{short}", [RAW]), RAW)
    assert (asset.level, asset.made) == ("sorted", "2026-04-23_14-11-00")
    assert assets.from_docdb(_record(short, f"{OPEN}/{short}"), RAW) is None


def test_a_private_asset_is_refused_when_pinned():
    with pytest.raises(DraftRefused, match="no public bucket"):
        assets.choose(_catalogue(), RAW, sorted_name=f"{RAW}_sorted_2026-09-01_00-00-00")


def test_an_nwb_is_read_only_where_it_was_built_from_the_chosen_sorting():
    sorting = f"{RAW}_sorted_2026-07-29_16-03-08"
    older = f"{RAW}_sorted_2025-12-24_08-46-14"
    built = assets.from_codeocean(
        _co(f"{RAW}_nwb_2026-08-18_13-28-44", "aind-open-data", f"{RAW}_nwb_2026-08-18_13-28-44", sorted_asset=sorting),
        RAW,
    )
    newer_of_older = assets.from_codeocean(
        _co(f"{RAW}_nwb_2026-09-02_00-00-00", "aind-open-data", f"{RAW}_nwb_2026-09-02_00-00-00", sorted_asset=older),
        RAW,
    )
    private = assets.from_codeocean(_co(f"{RAW}_nwb_2026-09-03_00-00-00", sorted_asset=sorting), RAW)
    choice = assets.choose(_catalogue(built, newer_of_older, private), RAW)
    assert choice.nwb == built
    assert f"{RAW}_nwb_2026-09-03_00-00-00 is stored in no public bucket, so it is not read" in choice.notes


def test_a_location_in_docdb_and_a_parent_in_code_ocean_merge():
    name = f"{RAW}_nwb_2026-08-18_13-28-44"
    docdb = assets.from_docdb(_record(name, f"{OPEN}/{name}"), RAW)
    co = assets.from_codeocean(_co(name, sorted_asset="x"), RAW)
    assert assets.merged([docdb, co])[name] == assets.Asset(name, "nwb", f"{OPEN}/{name}", docdb.made, "x")


def test_a_utc_stamp_no_stream_corroborates_is_read_as_wall_clock():
    record = {
        "acquisition": {
            "acquisition_start_time": "2025-09-25 12:43:56+00:00",
            "acquisition_end_time": "2025-09-25 21:09:44.929974+00:00",
            "subject_id": "786867",
            "data_streams": [
                {
                    "stream_start_time": "2025-09-25 12:44:11.035095-07:00",
                    "stream_end_time": "2025-09-25 14:09:44.929974-07:00",
                }
            ],
        }
    }
    session, notes = facts.session_facts(record, RAW, ZONE)
    assert session["session_start_time"] == "2025-09-25T19:43:56Z"
    # The end is the video stream's, which states its offset, so its UTC stamp is right.
    assert session["session_end_time"] == "2025-09-25T21:09:44.929974Z"
    assert len(notes) == 1 and notes[0].startswith("acquisition_start_time")


def test_subject_facts_map_onto_core_s_vocabulary():
    details = {"date_of_birth": "2024-11-26", "sex": "Male", "genotype": "wt/wt", "species": {"name": "Mus musculus"}}
    subject, _ = facts.subject_facts({"subject": {"subject_id": "786867", "subject_details": details}})
    assert subject == {
        "subject_id": "786867",
        "species": "Mus musculus",
        "sex": "male",
        "genotype": "wt/wt",
        "date_of_birth": "2024-11-26",
    }
    unknown, notes = facts.subject_facts({"subject": {"subject_details": {"sex": "Unknown"}}})
    assert "sex" not in unknown and any(n.startswith("sex:") for n in notes)


def _listing(tree):
    return lambda uri: tree.get(uri.rstrip("/"), [])


def _render(choice, layout, **kwargs):
    return draft.render(
        choice,
        layout,
        session={"session_id": RAW},
        subject={"subject_id": "786867"},
        notes=[],
        packet_id=RAW,
        out=RAW,
        registry="core.json",
        extensions={"aind_unit_qc": "aind_unit_qc.json", "dynamic_foraging": "dynamic_foraging.json"},
        **kwargs,
    )


def test_layout_reads_known_prefixes_and_falls_back_to_the_sorted_asset_s_nwb():
    choice = assets.choose(_catalogue(), RAW)
    sorting = choice.sorted.uri
    tree = {
        f"{sorting}/curated": ["experiment1_Record Node 109#Neuropix-PXI-100.46101_recording1"],
        sorting: ["curated", "nwb", "postprocessed"],
        f"{sorting}/nwb": [f"{RAW}_experiment1_recording1.nwb", f"{RAW}_experiment2_recording1.nwb"],
        f"{OPEN}/{RAW}/ecephys": ["ecephys_clipped", "ecephys_compressed"],
        f"{OPEN}/{RAW}/behavior": ["Sniffing", "behavior_786867_2025-09-25_12-44-05"],
        f"{OPEN}/{RAW}/behavior/behavior_786867_2025-09-25_12-44-05": ["behavior-videos"],
    }
    layout = catalog.layout(choice, _listing(tree))
    text, missing = _render(choice, layout)
    recipe = tomllib.loads(text)
    kinds = {s["kind"]: s for s in recipe["source"]}
    assert set(kinds) == {"session", "sync", "sorter", "waveforms", "aind_unit_qc", "openephys", "aind_nwb", "lfp"}
    assert kinds["aind_nwb"]["root"] == f"{sorting}/nwb/{RAW}_experiment1_recording1.nwb"
    # The ephys-only NWB holds no trials, so no interval kind names the task and its registry is not bound.
    assert "interval_kind" not in kinds["aind_nwb"]
    assert recipe["packet"]["extensions"] == ["aind_unit_qc.json"]
    assert missing == []
    assert "video: ffprobe reads a local file" in text
    assert "dynamic_foraging: the raw asset holds no behavior JSON" in text


def test_the_behavior_json_wins_the_trials_and_the_sniff_register_is_found():
    choice = assets.choose(_catalogue(), RAW)
    behavior = f"{OPEN}/{RAW}/behavior"
    first, restart = "behavior_791094_2025-10-08_16-49-31", "behavior_791094_2025-10-08_16-52-04"
    tree = {
        behavior: [first, restart, "Sniffing"],
        f"{behavior}/{first}/behavior": ["791094_2025-10-08_16-49-31.json"],
        f"{behavior}/{restart}/behavior": ["791094_2025-10-08_16-52-04.json", "parameters.json"],
        f"{behavior}/Sniffing": ["T16-48.harp", "T16-50.harp"],
        f"{behavior}/Sniffing/T16-48.harp": ["SniffDetector__1.bin", "device.yml"],
        f"{behavior}/Sniffing/T16-50.harp": ["SniffDetector__32.bin", "device.yml"],
    }
    layout = catalog.layout(choice, _listing(tree))
    assert layout.behavior_json == f"{behavior}/{restart}/behavior/791094_2025-10-08_16-52-04.json"
    assert any("one per start of the GUI" in note for note in layout.notes)
    layout = replace(layout, nwb_file=f"{OPEN}/{RAW}_nwb/{RAW}_experiment1_recording1.nwb")
    recipe = tomllib.loads(_render(choice, layout)[0])
    kinds = {s["kind"]: s for s in recipe["source"]}
    assert kinds["dynamic_foraging"]["root"] == layout.behavior_json
    assert kinds["harp"]["root"] == f"{behavior}/Sniffing/T16-50.harp"
    assert kinds["harp"]["signals"] == ["RawVoltage"]
    # The NWB still names the task's kind, since its trials table is read, but the JSON's rows win.
    assert kinds["aind_nwb"]["interval_kind"] == "dynamic_foraging.trials"
    assert "core.intervals" not in kinds["aind_nwb"]["owns"]
    assert recipe["preference"]["core.intervals"]["source"] == "dynamic_foraging"
    assert recipe["packet"]["extensions"] == ["aind_unit_qc.json", "dynamic_foraging.json"]


def test_a_flat_upload_holds_its_json_and_videos_directly():
    choice = assets.choose(_catalogue(), RAW)
    raw = f"{OPEN}/{RAW}"
    tree = {
        raw: ["behavior", "behavior-videos", "ecephys"],
        f"{raw}/behavior": ["raw.harp", "791093_2025-08-28_15-21-26.json", "behavior_session_model_x.json"],
    }
    layout = catalog.layout(choice, _listing(tree))
    assert layout.behavior_json == f"{raw}/behavior/791093_2025-08-28_15-21-26.json"
    assert layout.videos == f"{raw}/behavior-videos"


def test_a_private_asset_is_read_from_its_mirror():
    private = assets.Asset(f"{RAW}_nwb_2026-08-18_13-28-44", "nwb", None, None, f"{RAW}_sorted_2026-07-29_16-03-08")
    copy = f"s3://aind-scratch-data/escapewheel-nwb/{private.name}/"
    held, notes = assets.mirrored(_catalogue(private), {private.name: copy, "absent": copy})
    assert assets.choose(held, RAW).nwb.uri == copy.rstrip("/")
    assert notes == [f"{private.name} is private and read from a copy at {copy}"]
    layout = draft.Layout(nwb_file=f"{copy}{RAW}_experiment1_recording1.nwb")
    text, _ = _render(assets.choose(held, RAW), layout)
    kinds = {s["kind"]: s for s in tomllib.loads(text)["source"]}
    assert kinds["aind_nwb"]["storage_options"] == kinds["lfp"]["storage_options"] == {"anon": False}
    assert "nwb" not in kinds["aind_unit_qc"] and "storage_options" not in kinds["session"]


def test_a_combined_nwb_binds_the_task_and_a_local_copy_adds_the_videos(tmp_path):
    sorting = f"{RAW}_sorted_2026-07-29_16-03-08"
    nwb = assets.Asset(f"{RAW}_nwb_2026-08-18_13-28-44", "nwb", f"{OPEN}/{RAW}_nwb_2026-08-18_13-28-44", None, sorting)
    choice = assets.choose(_catalogue(nwb), RAW)
    videos = f"{OPEN}/{RAW}/behavior/b/behavior-videos"
    layout = draft.Layout(["experiment1", "experiment2"], True, videos, f"{nwb.uri}/{RAW}_experiment2_recording1.nwb")
    text, missing = _render(choice, layout, local_videos=tmp_path)
    recipe = tomllib.loads(text)
    kinds = {s["kind"]: s for s in recipe["source"]}
    assert kinds["aind_nwb"]["interval_kind"] == "dynamic_foraging.trials"
    assert recipe["packet"]["extensions"] == ["aind_unit_qc.json", "dynamic_foraging.json"]
    # The NWB names the experiment, and every scoped source follows it.
    assert {kinds[k]["experiment"] for k in ("sorter", "waveforms", "aind_unit_qc")} == {"experiment2"}
    assert kinds["video"] == {
        "kind": "video",
        "root": str(tmp_path),
        "uri_base": videos,
        "in_process": True,
        "owns": ["core.media_assets", "core.media_frames"],
    }
    assert "GUESS" in text and missing == []


def test_a_needed_extension_not_given_is_reported():
    choice = assets.choose(_catalogue(), RAW)
    _, missing = draft.render(
        choice,
        draft.Layout(),
        session={},
        subject={},
        notes=[],
        packet_id=RAW,
        out=RAW,
        registry="core.json",
        extensions={},
    )
    assert missing == ["aind_unit_qc"]
