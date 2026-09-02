import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from nwb_lake_reader import PacketError, open_packet

from nwb_lake_validator import generate, validate
from nwb_lake_validator.generate import Check, concerns


def _rewrite(root, name, table):
    pq.write_table(table, root / "tables" / "core" / f"{name}.parquet", compression="zstd")


def test_conforming_packet_passes(packet_root):
    report = validate(open_packet(packet_root))
    assert report.passed
    assert report.errors == 0 and report.warnings == 0


def test_duplicate_primary_key(packet_root):
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    _rewrite(packet_root, "trials", pa.concat_tables([trials, trials.slice(0, 1)]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "core.trials.primary_key_unique" for f in report.findings)


def test_unresolved_foreign_key(packet_root):
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    broken = trials.set_column(0, "session_id", pa.array(["s999", "s999"]))
    _rewrite(packet_root, "trials", broken)
    report = validate(open_packet(packet_root))
    assert any(f.check == "core.trials.session_id_resolves" for f in report.findings)


def test_closed_vocabulary(packet_root):
    units = pq.read_table(packet_root / "tables" / "core" / "units.parquet")
    broken = units.set_column(4, "quality_label", pa.array(["good", "mua"]))
    _rewrite(packet_root, "units", broken)
    report = validate(open_packet(packet_root))
    finding = next(f for f in report.findings if f.check == "core.units.quality_label.in_vocabulary")
    assert finding.rows == (("good",),)


def test_open_vocabulary_accepts_anything(packet_root):
    events = pq.read_table(packet_root / "tables" / "core" / "events.parquet")
    renamed = events.set_column(2, "event_type", pa.array(["whatever", "reward", "lick"]))
    _rewrite(packet_root, "events", renamed)
    assert validate(open_packet(packet_root)).passed


def test_tier_two_rule(packet_root):
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    broken = trials.set_column(3, "stop_tick", pa.array([0, 10000], type=pa.int64()))
    _rewrite(packet_root, "trials", broken)
    report = validate(open_packet(packet_root))
    assert any(f.check == "core.trials.interval_valid" for f in report.findings)


def test_wrong_column_type_is_caught_before_any_query(packet_root):
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    narrowed = trials.set_column(2, "start_tick", trials.column("start_tick").cast(pa.int32()))
    _rewrite(packet_root, "trials", narrowed)
    report = validate(open_packet(packet_root))
    assert any(f.check == "schema.column_type" for f in report.findings)


def test_physical_order_is_a_warning_not_an_error(packet_root):
    """Ordering is a performance property; a packet in the wrong order still conforms."""
    events = pq.read_table(packet_root / "tables" / "core" / "events.parquet")
    _rewrite(packet_root, "events", events.take([2, 0, 1]))
    report = validate(open_packet(packet_root))
    assert report.passed
    assert any(f.check == "core.events.physical_order" and f.level == "warning" for f in report.findings)


def test_registry_version_must_match_the_manifest(packet_root):
    path = packet_root / "schemas" / "logical_schemas.json"
    registry = json.loads(path.read_text())
    registry["registry_version"] = "0.2.0"
    path.write_text(json.dumps(registry))
    report = validate(open_packet(packet_root))
    assert any(f.check == "registry.version_mismatch" for f in report.findings)


def test_no_registry_anywhere_is_an_error(packet_root):
    (packet_root / "schemas" / "logical_schemas.json").unlink()
    with pytest.raises(PacketError, match="embeds no registry"):
        validate(open_packet(packet_root))


def test_supplied_registry_overrides_the_absent_one(packet_root):
    path = packet_root / "schemas" / "logical_schemas.json"
    registry = json.loads(path.read_text())
    path.unlink()
    assert validate(open_packet(packet_root), registry=registry).passed


def test_absent_tables_are_not_required(packet_root):
    """A packet need not carry every table the registry defines."""
    import json as _json

    path = packet_root / "nwb.packet.json"
    entry = _json.loads(path.read_text())
    entry["resources"] = [r for r in entry["resources"] if r["resource_id"] != "core.spike_events"]
    path.write_text(_json.dumps(entry))
    assert validate(open_packet(packet_root)).passed


def test_report_renders_as_json(packet_root):
    report = validate(open_packet(packet_root))
    rendered = report.to_dict("session_001")
    assert rendered["status"] == "passed"
    assert rendered["summary"] == {"errors": 0, "warnings": 0}


def test_generator_emits_nothing_for_an_empty_registry():
    assert generate({"tables": {}}) == []


def test_nullable_foreign_keys_are_guarded(packet_root):
    """Without an IS NOT NULL guard, every absent optional key reports as a violation."""
    registry = json.loads((packet_root / "schemas" / "logical_schemas.json").read_text())
    registry["tables"]["core.trials"]["columns"].append(
        {"name": "probe_id", "type": "string", "presence": "nullable", "description": "probe"}
    )
    registry["tables"]["core.trials"]["references"].append(
        {"columns": ["probe_id"], "resource": "core.sessions", "resource_columns": ["session_id"]}
    )
    check = next(c for c in generate(registry) if c.id == "core.trials.probe_id_resolves")
    assert "IS NOT NULL" in check.sql


def test_required_codecs_must_equal_the_union(packet_root):
    path = packet_root / "nwb.packet.json"
    entry = json.loads(path.read_text())
    entry["resources"].append(
        {
            "resource_id": "array.probe0",
            "layer": "core",
            "kind": "dense_array_asset",
            "uri": "s3://example/p.zarr",
            "external": True,
            "codecs": ["wavpack"],
        }
    )
    entry["required_codecs"] = []  # the union says wavpack
    path.write_text(json.dumps(entry))
    report = validate(open_packet(packet_root))
    finding = next(f for f in report.findings if f.check == "manifest.required_codecs_is_the_union")
    assert "wavpack" in finding.message


def test_external_resources_are_reported_as_unverified(packet_root):
    """A default-mode pass must not imply external claims were checked."""
    path = packet_root / "nwb.packet.json"
    entry = json.loads(path.read_text())
    entry["resources"].append(
        {
            "resource_id": "array.probe0",
            "layer": "core",
            "kind": "dense_array_asset",
            "uri": "s3://example/p.zarr",
            "external": True,
            "codecs": ["wavpack"],
        }
    )
    entry["required_codecs"] = ["wavpack"]
    path.write_text(json.dumps(entry))
    report = validate(open_packet(packet_root))
    assert report.passed  # unreachable externals do not invalidate
    info = next(f for f in report.findings if f.check == "external.unverified")
    assert info.level == "info"
    assert info.rows == (("array.probe0",),)


def test_advisory_rules_are_off_by_default(packet_root):
    """An advisory rule does not run unless asked (R26 §3)."""
    registry = json.loads((packet_root / "schemas" / "logical_schemas.json").read_text())
    registry["tables"]["core.trials"]["rules"].append(
        {
            "id": "core.trials.advice",
            "level": "info",
            "advisory": True,
            "message": "advice",
            "sql": "SELECT session_id, trial_id FROM core_trials",
        }
    )
    quiet = validate(open_packet(packet_root), registry=registry)
    assert not any(f.check == "core.trials.advice" for f in quiet.findings)

    loud = validate(open_packet(packet_root), registry=registry, advisory=True)
    assert any(f.check == "core.trials.advice" for f in loud.findings)


def test_advisory_cannot_change_the_verdict(packet_root):
    """`passed` is invariant under the flag, because advisory rules are never errors."""
    registry = json.loads((packet_root / "schemas" / "logical_schemas.json").read_text())
    registry["tables"]["core.trials"]["rules"].append(
        {
            "id": "core.trials.advice",
            "level": "info",
            "advisory": True,
            "message": "advice",
            "sql": "SELECT session_id, trial_id FROM core_trials",
        }
    )
    quiet = validate(open_packet(packet_root), registry=registry)
    loud = validate(open_packet(packet_root), registry=registry, advisory=True)
    assert quiet.passed is loud.passed is True
    assert loud.errors == quiet.errors == 0


def test_report_records_whether_advisories_ran(packet_root):
    """An empty advisory result is ambiguous unless the report says (R26 §5)."""
    assert validate(open_packet(packet_root)).to_dict("p")["advisory"] is False
    assert validate(open_packet(packet_root), advisory=True).to_dict("p")["advisory"] is True


def test_a_finding_that_projects_a_timestamp_is_reported_without_pytz(monkeypatch):
    """A rule that projects a wall-clock column must report its rows, not an engine error.

    DuckDB's own Python conversion imports `pytz` to render a ``TIMESTAMP WITH TIME ZONE``.
    An empty result converts nothing, so such a rule ran fine until it had something to say
    and then failed -- and whether that happened depended on whether an unrelated package had
    pulled `pytz` in.
    """
    import sys

    import duckdb

    from nwb_lake_validator.validator import _offending

    connection = duckdb.connect()
    connection.sql("CREATE TABLE core_clocks (clock_id VARCHAR, tick_zero_utc TIMESTAMP WITH TIME ZONE)")
    connection.sql("INSERT INTO core_clocks VALUES ('harp', '2024-11-27T00:51:12+00:00')")
    query = "SELECT clock_id, tick_zero_utc FROM core_clocks"

    monkeypatch.setitem(sys.modules, "pytz", None)  # makes `import pytz` raise, as an absent one does
    with pytest.raises(duckdb.InvalidInputException):
        connection.sql(query).fetchall()
    assert _offending(connection, query)[0][0] == "harp"
    assert _offending(connection, "SELECT clock_id, tick_zero_utc FROM core_clocks WHERE FALSE") == []


# -- materialization provenance (R31 §5) ------------------------------------------------


def _declare(root, **overrides):
    """Add an analysis resource to the manifest, pointing at a table that already exists."""
    path = root / "nwb.packet.json"
    manifest = json.loads(path.read_text())
    manifest["resources"].append(
        {
            "resource_id": "analysis.spike_events",
            "layer": "analysis",
            "kind": "table",
            "physical_profile": "parquet",
            "uri": "tables/core/trials.parquet",
            "canonical": True,
            "validation_state": "passed",
            **overrides,
        }
    )
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def test_an_analysis_resource_without_a_run_is_an_error(packet_root):
    """R31 §3: a derived resource that does not say how it was derived is not conforming."""
    _declare(packet_root)
    report = validate(open_packet(packet_root))
    assert any(f.check == "provenance.no_processing_run" for f in report.findings)


def test_a_run_that_resolves_to_nothing_is_an_error(packet_root):
    """Manifest-to-table, so no query can see it and the shim has to (R12 §4)."""
    _declare(packet_root, processing_run_id="ghost")
    report = validate(open_packet(packet_root))
    assert any(
        f.check in {"provenance.unknown_processing_run", "provenance.no_processing_runs_table"} for f in report.findings
    )


def test_a_core_resource_needs_no_run(packet_root):
    """R31 §4: the MUST is about derivation, not acquisition."""
    report = validate(open_packet(packet_root))
    assert not [f for f in report.findings if f.check.startswith("provenance.")]


# -- uniqueness by adjacency (the sort order makes it free) ------------------------------


def test_a_duplicate_beside_its_twin_is_caught_by_the_scan(packet_root):
    """core.trials is sorted by its key, so duplicates are neighbours and no GROUP BY runs."""
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    _rewrite(packet_root, "trials", trials.take([0, 0, 1]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "core.trials.primary_key_unique" for f in report.findings)


def test_a_duplicate_out_of_order_still_fails(packet_root):
    """Adjacency is unsound on an unordered file, so uniqueness falls back to the aggregate.

    Ordering stays a warning -- a packet in the wrong order still conforms -- so the fallback
    is what keeps the check from passing by omission.
    """
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    _rewrite(packet_root, "trials", trials.take([1, 0, 0]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "core.trials.primary_key_unique" for f in report.findings)


def test_validation_leaves_nothing_in_the_packet(packet_root):
    """The spill goes beside the packet, not inside it: a packet's bytes are settled, and one
    on read-only media must still be validatable."""
    before = {p.name for p in packet_root.iterdir()}
    validate(open_packet(packet_root))
    assert {p.name for p in packet_root.iterdir()} == before


# -- packet-owned arrays (R15 §4, level 2) ------------------------------------------------
#
# These are shim checks, not SQL (R12 §4): a query cannot see a chunk grid. The store below
# is a real Zarr v3 array with no chunk files, which is valid -- every chunk reads as
# `fill_value` -- so the metadata under test is the whole array.


def _zarr_v3(*, sharded=True, fill_value=0, grid="regular"):
    codecs = [{"name": "bytes"}, {"name": "blosc"}]
    document = {
        "zarr_format": 3,
        "node_type": "array",
        "shape": [4, 2, 3],
        "data_type": "int16",
        "chunk_grid": {"name": grid, "configuration": {"chunk_shape": [4, 2, 3] if sharded else [1, 2, 3]}},
        "chunk_key_encoding": {"name": "default"},
        "codecs": (
            [{"name": "sharding_indexed", "configuration": {"chunk_shape": [1, 2, 3], "codecs": codecs}}]
            if sharded
            else codecs
        ),
    }
    if fill_value is not None:
        document["fill_value"] = fill_value
    return document


def _add_array(root, *, declared, document=None, axes=3, external=False):
    """Bolt an array onto a packet, with whatever the manifest should claim about it."""
    manifest = json.loads((root / "nwb.packet.json").read_text())
    uri = "arrays/core/wf.zarr"
    store = root / uri
    store.mkdir(parents=True)
    (store / "zarr.json").write_text(json.dumps(document or _zarr_v3()))

    if axes is not None:
        dimensions = pa.table(
            {
                "array_asset_id": pa.array(["wf"] * axes),
                "axis_index": pa.array(list(range(axes)), type=pa.int64()),
                "dimension_name": pa.array(["unit", "channel", "sample"][:axes]),
            }
        )
        (root / "tables" / "core").mkdir(parents=True, exist_ok=True)
        pq.write_table(dimensions, root / "tables" / "core" / "array_dimensions.parquet")
        manifest["resources"].append(
            {
                "resource_id": "core.array_dimensions",
                "layer": "core",
                "kind": "table",
                "schema_id": "core.array_dimensions.v0.1",
                "physical_profile": "parquet",
                "uri": "tables/core/array_dimensions.parquet",
                "canonical": True,
                "validation_state": "passed",
            }
        )

    entry = {
        "resource_id": "core.waveform_mean",
        "layer": "core",
        "kind": "dense_array_asset",
        "physical_profile": "zarr_v3",
        "uri": uri,
        "array_asset_id": "wf",
        "canonical": True,
        "validation_state": "passed",
        "codecs": declared,
    }
    if external:
        entry |= {"external": True, "uri": f"file://{store}"}
    manifest["resources"].append(entry)
    manifest["required_codecs"] = sorted(declared)
    (root / "nwb.packet.json").write_text(json.dumps(manifest, indent=2))
    return root


def _checks(report, prefix="array."):
    return {f.check for f in report.findings if f.check.startswith(prefix)}


def test_an_array_declaring_its_codecs_correctly_is_clean(packet_root):
    _add_array(packet_root, declared=["sharding_indexed", "blosc"])
    assert _checks(validate(open_packet(packet_root))) == set()


def test_an_omitted_sharding_codec_is_caught(packet_root):
    """Sharding is a codec. A manifest omitting it understates what a reader needs (R15 §2)."""
    _add_array(packet_root, declared=["blosc"])
    report = validate(open_packet(packet_root))
    assert "array.codecs_disagree_with_store" in _checks(report)
    assert any("sharding_indexed" in f.message for f in report.findings)


def test_a_declared_codec_the_store_does_not_use_is_caught(packet_root):
    _add_array(packet_root, declared=["sharding_indexed", "blosc", "gzip"])
    assert "array.codecs_disagree_with_store" in _checks(validate(open_packet(packet_root)))


def test_a_packet_owned_array_must_be_zarr_v3(packet_root):
    """R21 §3.1 allows v2 only for an array the packet references."""
    v2 = {"zarr_format": 2, "shape": [4, 2, 3], "chunks": [1, 2, 3], "dtype": "<i2", "fill_value": 0}
    store = packet_root / "arrays" / "core" / "wf.zarr"
    _add_array(packet_root, declared=[])
    (store / "zarr.json").unlink()
    (store / ".zarray").write_text(json.dumps(v2))
    assert "array.not_zarr_v3" in _checks(validate(open_packet(packet_root)))


def test_an_array_without_a_fill_value_is_caught(packet_root):
    """R3 §7.1 requires one: without it an unwritten chunk has no defined value."""
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], document=_zarr_v3(fill_value=None))
    assert "array.no_fill_value" in _checks(validate(open_packet(packet_root)))


def test_an_irregular_chunk_grid_is_caught(packet_root):
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], document=_zarr_v3(grid="rectilinear"))
    assert "array.irregular_chunk_grid" in _checks(validate(open_packet(packet_root)))


def test_a_rank_the_dimensions_do_not_cover_is_caught(packet_root):
    """R3 §5: axis_index enumerates every stored axis, so two rows cannot describe rank 3."""
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], axes=2)
    assert "array.rank_disagrees_with_dimensions" in _checks(validate(open_packet(packet_root)))


def test_no_array_dimensions_at_all_is_caught(packet_root):
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], axes=None)
    assert "array.no_array_dimensions_table" in _checks(validate(open_packet(packet_root)))


def test_an_external_array_is_left_to_the_external_mode(packet_root):
    """Level 3, not level 2: reaching it is the reader's situation, not the packet's defect."""
    _add_array(packet_root, declared=["blosc"], external=True)
    assert _checks(validate(open_packet(packet_root))) == set()


# -- verify_order: the same comparison, made on the way in ---------------------------------


def _batch(first_tick, n=5, unit="u1"):
    return pa.record_batch(
        {
            "unit_id": pa.array([unit] * n),
            "t_tick": pa.array(range(first_tick, first_tick + n), type=pa.int64()),
        }
    )


KEYS = ["unit_id", "t_tick"]


def test_ordered_batches_pass_through_unchanged():
    from nwb_lake_validator import verify_order

    batches = [_batch(0), _batch(5), _batch(10)]
    assert [b.num_rows for b in verify_order(iter(batches), KEYS)] == [5, 5, 5]


def test_a_descent_inside_a_batch_is_caught():
    from nwb_lake_validator import OrderViolation, verify_order

    bad = pa.record_batch({"unit_id": pa.array(["u1"] * 3), "t_tick": pa.array([0, 5, 2], type=pa.int64())})
    with pytest.raises(OrderViolation, match="row 2 sorts before"):
        list(verify_order(iter([bad]), KEYS))


def test_a_descent_on_a_batch_seam_is_caught():
    """The case a per-batch check misses: each batch is ordered, the pair is not."""
    from nwb_lake_validator import OrderViolation, verify_order

    with pytest.raises(OrderViolation, match="row 5 sorts before"):
        list(verify_order(iter([_batch(10), _batch(0)]), KEYS))


def test_a_duplicate_on_a_batch_seam_is_caught():
    from nwb_lake_validator import OrderViolation, verify_order

    tail = pa.record_batch({"unit_id": pa.array(["u1"]), "t_tick": pa.array([4], type=pa.int64())})
    with pytest.raises(OrderViolation, match="row 5 repeats"):
        list(verify_order(iter([_batch(0), tail]), KEYS, unique=KEYS))


def test_an_empty_batch_does_not_break_the_seam():
    from nwb_lake_validator import verify_order

    empty = _batch(0, n=0)
    assert [b.num_rows for b in verify_order(iter([_batch(0), empty, _batch(5)]), KEYS)] == [5, 0, 5]


def test_scanning_nothing_leaves_the_ordering_unchecked(packet_root):
    """What `commit` relies on: a caller that established the order elsewhere skips the read."""
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    _rewrite(packet_root, "trials", trials.sort_by([("trial_id", "descending")]))
    assert any(f.check == "core.trials.physical_order" for f in validate(open_packet(packet_root)).findings)
    assert not any(
        f.check == "core.trials.physical_order" for f in validate(open_packet(packet_root), scan=set()).findings
    )


def test_a_column_determined_by_the_key_cannot_separate_duplicates():
    """R30 sorts `analysis.spike_events` by two columns that precede its key.

    `clock_id` is the session's reference clock and `time_bucket_tick` is a function of
    `t_tick`, so neither varies between rows sharing a key, and duplicates stay neighbours.
    """
    from nwb_lake_validator.generate import adjacency_settles_uniqueness

    table = {
        "primary_key": ["session_id", "t_tick"],
        "sort": ["session_id", "clock_id", "time_bucket_tick", "t_tick"],
        "columns": [
            {"name": "clock_id", "type": "string", "presence": "required", "determined_by": ["session_id"]},
            {"name": "time_bucket_tick", "type": "int64", "presence": "required", "determined_by": ["t_tick"]},
        ],
    }
    assert adjacency_settles_uniqueness(table)


def test_a_column_determined_by_a_non_key_still_refuses():
    """The dependency must be on the key: anything else can order duplicates apart."""
    from nwb_lake_validator.generate import adjacency_settles_uniqueness

    table = {
        "primary_key": ["a", "b"],
        "sort": ["a", "x", "b"],
        "columns": [{"name": "x", "type": "string", "presence": "required", "determined_by": ["c"]}],
    }
    assert not adjacency_settles_uniqueness(table)


def test_an_undeclared_column_ahead_of_the_key_refuses():
    from nwb_lake_validator.generate import adjacency_settles_uniqueness

    table = {"primary_key": ["a", "b"], "sort": ["a", "x", "b"], "columns": [{"name": "x"}]}
    assert not adjacency_settles_uniqueness(table)


def test_a_dictionary_column_satisfies_a_string_declaration():
    """A dictionary is an encoding, not a type: Parquet stores BYTE_ARRAY/String either way."""
    from nwb_lake_validator import Report
    from nwb_lake_validator.validator import _check_column

    report = Report()
    column = {"name": "session_id", "type": "string", "presence": "required"}
    schema = pa.schema([pa.field("session_id", pa.dictionary(pa.int32(), pa.string()))])
    _check_column("core.units", column, schema, report)
    assert not report.findings


def test_a_dictionary_over_the_wrong_value_type_is_still_refused():
    """Unwrapping the encoding must not unwrap the check."""
    from nwb_lake_validator import Report
    from nwb_lake_validator.validator import _check_column

    report = Report()
    column = {"name": "session_id", "type": "string", "presence": "required"}
    schema = pa.schema([pa.field("session_id", pa.dictionary(pa.int32(), pa.int64()))])
    _check_column("core.units", column, schema, report)
    assert [f.check for f in report.findings] == ["schema.column_type"]


# -- R35 §5: an amendment re-runs only the rules its own resources implicate ---------------


def _check(sql, resource="core.units"):
    return Check(f"{resource}.rule", "error", "message", sql, resource)


def test_a_rule_attached_to_a_written_resource_runs():
    assert concerns(_check("SELECT * FROM core_units"), {"core.units"})


def test_a_rule_whose_query_names_a_written_resource_runs():
    """The syntactic test is what makes R32 §5's objection answerable without the registry
    promising that no existing rule references a resource added later."""
    sql = "SELECT c.unit_id FROM core_units c LEFT JOIN analysis_spike_events p ON c.unit_id = p.unit_id"
    assert concerns(_check(sql), {"analysis.spike_events"})


def test_a_rule_reading_only_untouched_resources_may_be_skipped():
    assert not concerns(_check("SELECT * FROM core_units"), {"analysis.spike_events"})


def test_the_test_errs_toward_running():
    """R35 §5: a match inside a comment costs time, a missed one costs correctness."""
    sql = "SELECT * FROM core_units -- nothing to do with analysis_spike_events"
    assert concerns(_check(sql), {"analysis.spike_events"})


def test_recheck_narrows_the_rules_that_run(packet_root):
    """A packet that passes still passes, over fewer checks."""
    packet = open_packet(packet_root)
    registry = packet.registry
    every = generate(registry, only=set(registry["tables"]))
    narrowed = [c for c in every if concerns(c, {"core.trials"})]
    assert 0 < len(narrowed) < len(every)
    assert validate(open_packet(packet_root), recheck={"core.trials"}).passed


def test_recheck_still_catches_a_break_in_what_was_written(packet_root):
    """Narrowing must not narrow away the resource the amendment actually wrote."""
    duplicated = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    _rewrite(packet_root, "trials", pa.concat_tables([duplicated, duplicated.slice(0, 1)]))
    report = validate(open_packet(packet_root), recheck={"core.trials"})
    assert not report.passed


# -- R14/R15/R21: external resources -------------------------------------------------------


def _external(root, **overrides):
    """Point a packet at a Zarr v2 array beside it, the way an LFP reference does."""
    array = root.parent / "external.zarr"
    array.mkdir(exist_ok=True)
    (array / ".zarray").write_text(
        json.dumps(
            {
                "shape": [4, 2],
                "chunks": [4, 2],
                "dtype": "<i2",
                "zarr_format": 2,
                "compressor": {"id": "blosc"},
                "filters": None,
                "order": "C",
                "fill_value": 0,
            }
        )
    )
    (array / "0.0").write_bytes(b"x" * 100)
    total = sum(f.stat().st_size for f in array.rglob("*") if f.is_file())
    manifest = json.loads((root / "nwb.packet.json").read_text())
    entry = {
        "resource_id": "core.probe.lfp",
        "layer": "core",
        "kind": "dense_array_asset",
        "physical_profile": "zarr_v2",
        "uri": array.resolve().as_uri(),
        "external": True,
        "codecs": ["blosc"],
        "size_bytes": total,
        **overrides,
    }
    manifest["resources"].append({k: v for k, v in entry.items() if v is not None})
    manifest["required_codecs"] = sorted({c for r in manifest["resources"] for c in r.get("codecs", [])})
    (root / "nwb.packet.json").write_text(json.dumps(manifest))
    return root


def test_an_external_resource_is_reported_as_unverified_by_default(packet_root):
    """R14 §2.3.2: structural validation must not reach for bytes the packet does not own."""
    report = validate(open_packet(_external(packet_root)))
    assert report.passed
    assert [f.check for f in report.findings if f.level == "info"] == ["external.unverified"]


def test_the_requested_mode_resolves_it(packet_root):
    report = validate(open_packet(_external(packet_root)), external=True)
    assert report.passed
    checks = {f.check for f in report.findings}
    assert "external.verified" in checks
    assert "external.unverified" not in checks, "the two modes must not both speak"


def test_size_bytes_counts_the_whole_prefix_including_its_metadata(packet_root):
    """A dense array asset is a prefix of many objects, so its size is a list, not a stat.
    Excluding the metadata document would make the writer and the validator disagree."""
    assert validate(open_packet(_external(packet_root)), external=True).passed


def test_a_size_that_disagrees_is_an_error_only_in_that_mode(packet_root):
    root = _external(packet_root, size_bytes=999)
    assert validate(open_packet(root)).passed
    report = validate(open_packet(root), external=True)
    assert not report.passed
    assert "external.size_bytes" in {f.check for f in report.findings}


def test_a_codec_that_disagrees_is_caught(packet_root):
    root = _external(packet_root, codecs=["zstd"])
    report = validate(open_packet(root), external=True)
    assert "external.codecs" in {f.check for f in report.findings}


def test_an_unreachable_resource_is_a_warning_not_an_error(packet_root):
    """Reachability is a property of the reader's situation, not of the packet."""
    root = _external(packet_root, uri="file:///nowhere/at/all.zarr")
    report = validate(open_packet(root), external=True)
    assert report.passed
    assert "external.unreachable" in {f.check for f in report.findings}


def test_a_codec_outside_its_versions_floor_is_reported(packet_root):
    """R21 §3.3: gzip is in R3 §7.2's baseline and Zarr.jl reads it in v3 and not in v2."""
    root = _external(packet_root, codecs=["gzip"])
    report = validate(open_packet(root))
    assert report.passed, "outside the floor is conforming, just not portable"
    assert "codec.outside_the_floor" in {f.check for f in report.findings}


def test_the_same_codec_inside_the_v3_floor_is_not_reported(packet_root):
    root = _external(packet_root, physical_profile="zarr_v3", codecs=["gzip"])
    assert "codec.outside_the_floor" not in {f.check for f in validate(open_packet(root)).findings}


def test_a_requested_digest_with_nothing_recorded_says_so(packet_root):
    """R36 §2.4: a packet need not record a sha256, and every packet built so far records none.
    Asking for checksums and finding nothing to compare must not report a clean verification."""
    report = validate(open_packet(_external(packet_root)), external=True, checksums=True)
    assert report.passed, "a claim the packet never made is not a failure"
    assert "external.no_checksum" in {f.check for f in report.findings}
    verified = next(f for f in report.findings if f.check == "external.verified")
    assert "sha256" not in verified.message, "it compared none, so it must not claim any"


def test_a_recorded_digest_is_compared(packet_root):
    from nwb_lake_validator.stores import digest

    root = _external(packet_root)
    manifest = json.loads((root / "nwb.packet.json").read_text())
    entry = next(r for r in manifest["resources"] if r.get("external"))
    entry["sha256"] = digest(entry["uri"])
    (root / "nwb.packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root), external=True, checksums=True)
    assert report.passed
    assert "external.no_checksum" not in {f.check for f in report.findings}
    assert "1 sha256" in next(f for f in report.findings if f.check == "external.verified").message


def test_a_digest_that_disagrees_is_an_error(packet_root):
    root = _external(packet_root, sha256="0" * 64)
    assert validate(open_packet(root), external=True).passed, "not read without checksums"
    report = validate(open_packet(root), external=True, checksums=True)
    assert not report.passed
    assert "external.sha256" in {f.check for f in report.findings}


def test_the_summary_names_what_it_compared(packet_root):
    """"Resolved and checked" said nothing about which claims were actually tested."""
    report = validate(open_packet(_external(packet_root)), external=True)
    message = next(f for f in report.findings if f.check == "external.verified").message
    assert "1 codecs" in message and "1 size_bytes" in message


def _with_members(root, *, mutate=None):
    """Declare R51 §2.1 members for the external resource, as a writer at verify="members" would."""
    from nwb_lake_validator.stores import listing

    manifest = json.loads((root / "nwb.packet.json").read_text())
    entry = next(r for r in manifest["resources"] if r.get("external"))
    entry["members"] = [{"key": m.key, "size_bytes": m.size_bytes} for m in listing(entry["uri"]).members]
    if mutate is not None:
        mutate(entry)
    (root / "nwb.packet.json").write_text(json.dumps(manifest))
    return root


def test_declared_members_are_checked_against_the_store(packet_root):
    report = validate(open_packet(_with_members(_external(packet_root))), external=True)
    assert report.passed
    assert "1 members" in next(f for f in report.findings if f.check == "external.verified").message


def test_a_member_the_store_does_not_hold_is_an_error(packet_root):
    root = _with_members(_external(packet_root), mutate=lambda e: e["members"].append({"key": "9.9", "size_bytes": 1}))
    report = validate(open_packet(root), external=True)
    assert not report.passed
    assert "external.members" in {f.check for f in report.findings}


def test_a_member_size_that_disagrees_is_caught_where_the_total_would_not(packet_root):
    """Two members changing in opposite directions leave `size_bytes` correct. R51 §2.1."""

    def swap(entry):
        entry["members"][0]["size_bytes"] += 10
        entry["members"][1]["size_bytes"] -= 10

    root = _with_members(_external(packet_root), mutate=swap)
    report = validate(open_packet(root), external=True)
    assert not report.passed, "the total still agrees, so only a per-member check sees this"
    assert "external.members" in {f.check for f in report.findings}


def test_store_digests_report_what_they_could_not_check(packet_root):
    """A local filesystem offers no content hash, so every member is skipped, not passed."""
    report = validate(open_packet(_with_members(_external(packet_root))), external=True, store_digests=True)
    assert report.passed
    assert "external.no_store_digest" in {f.check for f in report.findings}
    assert "store_digest" not in next(f for f in report.findings if f.check == "external.verified").message


def test_a_store_digest_that_changed_in_place_is_an_error(packet_root, monkeypatch):
    """Neither the size nor a recorded sha256 need change for this to fire."""
    from nwb_lake_validator import validator as module
    from nwb_lake_validator.stores import Listing, Member, StoreDigest, listing

    def stamped(uri, **kwargs):
        found = listing(uri, **kwargs)
        return Listing(
            tuple(Member(m.key, m.size_bytes, StoreDigest("md5", f"{index:032x}")) for index, m in enumerate(found.members)),
            found.size_bytes,
        )

    root = _with_members(_external(packet_root))
    monkeypatch.setattr(module, "listing", stamped)
    passing = validate(open_packet(_with_members(root, mutate=lambda e: [
        m.update(store_digest={"algorithm": "md5", "value": f"{i:032x}"}) for i, m in enumerate(e["members"])
    ])), external=True, store_digests=True)
    assert passing.passed
    assert "1 store_digest" in next(f for f in passing.findings if f.check == "external.verified").message

    changed = validate(open_packet(_with_members(root, mutate=lambda e: [
        m.update(store_digest={"algorithm": "md5", "value": "f" * 32}) for m in e["members"]
    ])), external=True, store_digests=True)
    assert not changed.passed
    assert "external.store_digest" in {f.check for f in changed.findings}
