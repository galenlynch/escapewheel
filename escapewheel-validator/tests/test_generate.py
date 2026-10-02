"""The checks a registry's structure implies, and which of them an amendment re-runs (Part 02 §10.1)."""

from escapewheel_reader import open_packet
from packet_fixture import read_registry

from escapewheel_validator import check_table, validate
from escapewheel_validator import generate as generating
from escapewheel_validator.generate import Check, adjacency_settles_uniqueness, concerns
from escapewheel_validator.generate import _generate as generate


def test_generator_emits_nothing_for_an_empty_registry():
    assert generate({"resources": {}}) == []


def test_nullable_foreign_keys_are_guarded(packet_root):
    """Without an IS NOT NULL guard, every absent optional key reports as a violation."""
    registry = read_registry(packet_root)
    registry["resources"]["core.intervals"]["table"]["columns"].append(
        {"name": "probe_id", "type": "string", "presence": "nullable", "description": "probe"}
    )
    registry["resources"]["core.intervals"]["table"]["references"].append(
        {"columns": ["probe_id"], "resource": "core.sessions", "resource_columns": ["session_id"]}
    )
    check = next(c for c in generate(registry) if c.id == "core.intervals.probe_id_resolves")
    assert "IS NOT NULL" in check.sql


def test_a_column_determined_by_the_key_cannot_separate_duplicates():
    """R30 sorts `analysis.spike_events` by two columns that precede its key.

    `clock_id` is the session's reference clock and `time_bucket_tick` is a function of
    `t_tick`, so neither varies between rows sharing a key, and duplicates stay neighbours.
    """
    # The resource names the order: the descriptor's override for this one (Part 03 §5.4) is what
    # puts two non-key columns ahead of the key.
    table = {
        "primary_key": ["session_id", "unit_id", "t_tick"],
        "columns": [
            {"name": "clock_id", "type": "int32", "presence": "required", "determined_by": ["session_id"]},
            {"name": "time_bucket_tick", "type": "int64", "presence": "required", "determined_by": ["t_tick"]},
        ],
    }
    assert adjacency_settles_uniqueness("analysis.spike_events", table)


def test_a_column_determined_by_a_non_key_still_refuses(monkeypatch):
    """The dependency must be on the key: anything else can order duplicates apart."""
    table = {
        "primary_key": ["a", "b"],
        "columns": [{"name": "x", "type": "string", "presence": "required", "determined_by": ["c"]}],
    }
    monkeypatch.setattr(generating, "stored_order", lambda resource, table: ["a", "x", "b"])
    assert not adjacency_settles_uniqueness("x.y", table)


def test_an_undeclared_column_ahead_of_the_key_refuses(monkeypatch):
    table = {"primary_key": ["a", "b"], "columns": [{"name": "x"}]}
    monkeypatch.setattr(generating, "stored_order", lambda resource, table: ["a", "x", "b"])
    assert not adjacency_settles_uniqueness("x.y", table)


def _check(sql, resource="core.units", dependencies=()):
    return Check(
        check_table.rule(f"{resource}.rule", "error"),
        "message",
        sql,
        resource,
        dependencies=frozenset(dependencies or {resource}),
    )


def test_a_rule_attached_to_a_written_resource_runs():
    assert concerns(_check("SELECT * FROM core_units"), {"core.units"})


def test_a_rule_whose_query_names_a_written_resource_runs():
    """Parsed base relations are authoritative dependencies for Tier 2."""
    sql = "SELECT c.unit_id FROM core_units c LEFT JOIN analysis_spike_events p ON c.unit_id = p.unit_id"
    assert concerns(_check(sql, dependencies={"core.units", "analysis.spike_events"}), {"analysis.spike_events"})


def test_a_rule_reading_only_untouched_resources_may_be_skipped():
    assert not concerns(_check("SELECT * FROM core_units"), {"analysis.spike_events"})


def test_resource_text_in_a_comment_is_not_a_dependency():
    """Part 05 §15.4: comments do not create Tier 2 dependencies."""
    sql = "SELECT * FROM core_units -- nothing to do with analysis_spike_events"
    assert not concerns(_check(sql), {"analysis.spike_events"})


def test_recheck_narrows_the_rules_that_run(packet_root):
    """A packet that passes still passes, over fewer checks."""
    packet = open_packet(packet_root)
    registry = packet.registry
    every = generate(
        registry,
        only={name for name, declaration in registry["resources"].items() if declaration["kind"] == "table"},
    )
    narrowed = [c for c in every if concerns(c, {"core.intervals"})]
    assert 0 < len(narrowed) < len(every)
    assert validate(open_packet(packet_root), recheck={"core.intervals"}).passed


def _discriminated(role="discriminator", **extra):
    """A one-table registry whose `k_kind` discriminates `k` (Part 02 §8.3)."""
    column = {"name": "k_kind", "type": "string", "presence": "nullable", "role": role, **extra}
    return {
        "resources": {
            "core.runs": {
                "kind": "table",
                "table": {
                    "columns": [
                        {"name": "run_id", "type": "int32", "presence": "required", "role": "identifier"},
                        column,
                        {"name": "k", "type": "string", "presence": "nullable", "role": "data"},
                    ],
                    "primary_key": ["run_id"],
                    "references": [],
                    "rules": [],
                },
            }
        }
    }


def test_a_discriminator_is_checked_for_being_a_resource_id():
    """Part 02 §8.3. Nothing checked this: `scope_kind` could hold an empty string and no rule saw it."""
    checks = generate(_discriminated(resolves="optional", discriminates="k"))
    ids = {c.id for c in checks}
    assert "core.runs.k_kind.is_a_resource_id" in ids


def test_a_data_column_generates_no_discriminator_checks():
    """The role is what turns it on, which is R55 §1.1's point: `data` said only 'may be read'."""
    checks = generate(_discriminated(role="data"))
    assert not [c for c in checks if "k_kind" in c.id]


def test_resolves_decides_the_level_not_whether_the_check_exists():
    """Part 02 §8.3. An optional kind naming nothing is a fact, and reported; R49 §2.5 passed it in silence."""
    kinds = {"core.sessions": "session_id"}
    optional = generate(_discriminated(resolves="optional", discriminates="k"), kinds=kinds)
    required = generate(_discriminated(resolves="required", discriminates="k"), kinds=kinds)
    levels = {c.id: c.level for c in optional + required}
    assert levels["core.runs.k_kind.kind_declared"] in ("info", "error")
    assert {c.level for c in optional if c.id.endswith("kind_declared")} == {"info"}
    assert {c.level for c in required if c.id.endswith("kind_declared")} == {"error"}


def test_the_forward_check_admits_only_what_the_manifest_declares():
    """Part 02 §8.3: a value naming a core table the packet does not carry names no declared resource."""
    kinds = {"core.sessions": "session_id", "core.probes": None}
    checks = generate(
        _discriminated(resolves="required", discriminates="k"), kinds=kinds, named={"core.runs", "core.sessions"}
    )
    (forward,) = [c for c in checks if c.id == "core.runs.k_kind.kind_declared"]
    assert "'core.sessions'" in forward.sql
    assert "core.probes" not in forward.sql


def test_a_shared_key_discriminator_generates_no_value_resolution():
    """Part 02 §8.3: the named table's own reference carries that integrity, pointing the other way."""
    checks = generate(_discriminated(resolves="required"), kinds={"core.sessions": "session_id"})
    assert not [c for c in checks if c.id.startswith("core.runs.k_kind.") and c.id.endswith("_resolves")]


def test_a_string_paired_value_is_cast_on_both_sides():
    """A carried key may be a number where the string value is not one; uncast, DuckDB raises on it."""
    checks = generate(
        _discriminated(resolves="required", discriminates="k"),
        only={"core.runs"},
        kinds={"core.runs": "run_id"},
    )
    sql = next(c.sql for c in checks if c.id == "core.runs.k_kind.core_runs_resolves")
    assert sql.count("CAST") == 2


def test_each_named_kind_gets_its_own_anti_join():
    """Per kind, so a value resolves only in the kind its own row names (Part 02 §8.3)."""
    checks = generate(
        _discriminated(resolves="required", discriminates="k"),
        only={"core.runs", "core.sessions"},
        kinds={"core.runs": "run_id", "core.sessions": "session_name", "ext.absent": "absent_id"},
    )
    ids = {c.id for c in checks}
    assert {"core.runs.k_kind.core_runs_resolves", "core.runs.k_kind.core_sessions_resolves"} <= ids
    assert not [i for i in ids if "ext_absent" in i], "a kind the packet does not carry is the declared-kind check's"
    declared = next(c.sql for c in checks if c.id == "core.runs.k_kind.kind_declared")
    assert "'ext.absent'" in declared


def test_an_optional_paired_value_generates_no_resolution():
    """Part 02 §8.3: a value an optional discriminator pairs may name nothing the packet holds."""
    checks = generate(
        _discriminated(resolves="optional", discriminates="k"),
        only={"core.runs"},
        kinds={"core.runs": "run_id"},
    )
    ids = {c.id for c in checks if c.id.startswith("core.runs.k_kind.")}
    assert ids == {"core.runs.k_kind.is_a_resource_id", "core.runs.k_kind.kind_declared"}


def _identifier_paired(resolves="required"):
    registry = _discriminated(resolves=resolves, discriminates="k")
    columns = registry["resources"]["core.runs"]["table"]["columns"]
    columns[2] = {"name": "k", "type": "int32", "presence": "nullable", "role": "identifier", "identity": "assigned"}
    columns[0]["identity"] = "assigned"
    return registry


def test_an_identifier_paired_value_joins_its_key_uncast():
    """An identifier value holds the named key's own value, so both sides share a type (Part 02 §8.3)."""
    registry = _identifier_paired()
    checks = generate(registry, only={"core.runs"}, kinds={"core.runs": None})
    sql = next(c.sql for c in checks if c.id == "core.runs.k_kind.core_runs_resolves")
    assert "CAST" not in sql and "run_id" in sql
    assert "core.runs.k_kind.key_fits_paired_value" not in {c.id for c in checks}


def test_a_key_an_identifier_value_cannot_hold_is_reported():
    """A kind whose key is another type, or not one column, can name no row through the value."""
    keys = {"core.runs": {"name": "run_id", "type": "int32", "identity": "assigned"}, "core.intervals": None}
    checks = generate(
        _identifier_paired(), only={"core.runs"}, kinds={"core.runs": None, "core.intervals": None}, keys=keys
    )
    shape = next(c for c in checks if c.id == "core.runs.k_kind.key_fits_paired_value")
    assert shape.level == "error" and "'core.intervals'" in shape.sql and "'core.runs'" not in shape.sql
    optional = generate(_identifier_paired("optional"), only={"core.runs"}, kinds={"core.intervals": None}, keys=keys)
    assert "core.runs.k_kind.key_fits_paired_value" not in {c.id for c in optional}
