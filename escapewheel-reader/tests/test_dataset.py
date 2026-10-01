"""Many packets as one relation (R86)."""

import json
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from escapewheel_reader import (
    Dataset,
    MultiSessionUnresolved,
    ResourceNotFoundError,
    open_dataset,
    open_packet,
    session_scoped,
)

from .conftest import SESSION, SESSION_NAME, install_registry, read_registry

SECOND_SESSION = SESSION  # deliberately the same number in the other packet
SECOND_NAME = "s002"


def _second(packet_root, tmp_path):
    """A second packet holding a different session under the same identifiers.

    The point of R86: two packets number their sessions and units independently, so the second
    reuses `session_id` and `unit_id` for things that are not the first's.
    """
    root = tmp_path / "session_002"
    shutil.copytree(packet_root, root)
    sessions = pq.read_table(root / "tables/core/sessions.parquet")
    pq.write_table(
        sessions.set_column(
            sessions.schema.get_field_index("session_name"),
            "session_name",
            pa.array([SECOND_NAME]),
        ),
        root / "tables/core/sessions.parquet",
    )
    manifest = json.loads((root / "packet.json").read_text())
    manifest["packet_id"] = "session_002"
    manifest["sessions"] = [SECOND_NAME]
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return root


@pytest.fixture
def two(packet_root, tmp_path):
    return open_dataset([packet_root, _second(packet_root, tmp_path)])


# -- §2.1 a table is session-scoped where it reaches core.sessions ----------------------


def _registry(**references):
    return {
        "resources": {
            name: {
                "kind": "table",
                "table": {
                    "columns": [],
                    "references": [
                        {"columns": ["x"], "resource": parent, "resource_columns": ["x"]} for parent in parents
                    ],
                },
            }
            for name, parents in {"core.sessions": (), **references}.items()
        }
    }


def test_a_table_referencing_sessions_directly_is_scoped():
    assert session_scoped(_registry(**{"core.units": ("core.sessions",)})) == {
        "core.sessions",
        "core.units",
    }


def test_a_table_reaching_sessions_through_a_parent_is_scoped():
    """Part 02 §7.1: scope follows declared references to `core.sessions`."""
    registry = _registry(**{"core.units": ("core.sessions",), "core.spikes": ("core.units",)})
    assert session_scoped(registry) == {"core.sessions", "core.units", "core.spikes"}


def test_a_table_sessions_references_is_not_scoped():
    """`core.subjects` and `core.source_files` fall out because `core.sessions` references them."""
    registry = _registry(**{"core.subjects": ()})
    registry["resources"]["core.sessions"]["table"]["references"] = [
        {"columns": ["subject_id"], "resource": "core.subjects", "resource_columns": ["subject_id"]}
    ]
    assert session_scoped(registry) == {"core.sessions"}


def test_a_self_reference_is_not_a_route_to_sessions():
    """Part 01 §3.5's chain is well-founded, and a device is not scoped by pointing at itself."""
    assert session_scoped(_registry(**{"core.devices": ("core.devices",)})) == {"core.sessions"}


# -- §2.2 a reader discriminates by what it knows --------------------------------------


def test_every_session_of_every_packet_is_numbered(two):
    assert [(s.session_key, s.packet_id, s.session_id, s.session_name) for s in two.sessions] == [
        (0, "session_001", SESSION, SESSION_NAME),
        (1, "session_002", SECOND_SESSION, SECOND_NAME),
    ]


def test_a_scoped_table_carries_the_discriminator(two):
    units = two.table("core.units")
    assert units.num_rows == 4
    assert units.column("session_key").to_pylist() == [0, 0, 1, 1]
    assert units.column("session_name").to_pylist() == [SESSION_NAME] * 2 + [SECOND_NAME] * 2


def test_the_identifier_collides_and_the_pair_does_not(two):
    """R86 §1.2. 4,505 `unit_id` values name a unit in both real packets; no pair does."""
    units = two.table("core.units")
    ids = units.column("unit_id").to_pylist()
    pairs = list(zip(units.column("session_key").to_pylist(), ids, strict=True))
    assert len(set(ids)) == 2
    assert len(set(pairs)) == 4


def test_an_unscoped_table_carries_no_discriminator(packet_root, tmp_path):
    """Part 05 §13.1: `core.subjects` is not session-scoped, so it gets no key."""
    subjects = pa.table({"subject_id": pa.array([7], type=pa.int32()), "subject_name": pa.array(["m001"])})
    for root in (packet_root, _second(packet_root, tmp_path)):
        pq.write_table(subjects, root / "tables/core/subjects.parquet")
        manifest = json.loads((root / "packet.json").read_text())
        manifest["resources"].append(
            {
                "resource_id": "core.subjects",
                "declaration_id": "core.subjects",
                "uri": "tables/core/subjects.parquet",
                "validation_state": "passed",
            }
        )
        (root / "packet.json").write_text(json.dumps(manifest, indent=2))
        registry = read_registry(root)
        registry["resources"]["core.subjects"] = {
            "content_class": "core",
            "kind": "table",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "optional",
            "table": {
                "columns": [
                    {
                        "name": "subject_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "",
                    },
                    {
                        "name": "subject_name",
                        "type": "string",
                        "presence": "nullable",
                        "role": "data",
                        "description": "",
                    },
                ],
                "primary_key": ["subject_id"],
                "references": [],
                "rules": [],
            },
        }
        install_registry(root, registry)
    data = open_dataset([packet_root, tmp_path / "session_002"])
    assert "core.subjects" not in data.scoped
    assert set(data.table("core.subjects").column_names) == {"subject_id", "subject_name"}


def test_one_packet_gets_the_same_shape_as_many(packet_root):
    """Part 05 §13.1: one or many sessions expose the same relation shape."""
    one = open_dataset([packet_root])
    assert one.table("core.units").column("session_key").to_pylist() == [0, 0]


def test_a_dataset_needs_a_packet():
    with pytest.raises(ValueError, match="at least one packet"):
        Dataset([])


# -- §2.4 the identity is projected, not joined for -------------------------------------


def test_the_sql_view_projects_the_identity(two):
    """Part 05 §13.1 uses a scalar projection, so an unused key is pruned."""
    duckdb = pytest.importorskip("duckdb")
    assert duckdb
    con = two.duckdb(tables=["core.units"])
    assert con.sql(
        "SELECT session_key, session_name, count(*) FROM core_units GROUP BY 1, 2 ORDER BY 1"
    ).fetchall() == [(0, SESSION_NAME, 2), (1, SECOND_NAME, 2)]


def test_the_view_is_a_projection_rather_than_a_join(two):
    """A join cannot be pruned; the projected form must not name `core.sessions` at all."""
    statement = two._view("core.units")
    assert "AS session_key" in statement
    assert "core_sessions" not in statement and "JOIN" not in statement.upper()


def test_the_arrow_path_and_the_sql_path_agree(two):
    """The reader's standing rule: a semantic operation exists on both paths and they agree."""
    duckdb = pytest.importorskip("duckdb")
    assert duckdb
    con = two.duckdb(tables=["core.units"])
    from_sql = con.sql("SELECT session_key, unit_id FROM core_units ORDER BY 1, 2").fetchall()
    arrow = two.table("core.units", columns=["unit_id"])
    from_arrow = sorted(zip(arrow.column("session_key").to_pylist(), arrow.column("unit_id").to_pylist(), strict=True))
    assert from_sql == from_arrow


def test_cross_packet_unit_join_adds_the_session_discriminator(two):
    """Part 05 §13.2: packet-local `unit_id` is widened only by presentation context."""
    con = two.duckdb(tables=["core.units", "core.spike_events"])
    correct = con.sql(
        "SELECT count(*) FROM core_spike_events s JOIN core_units u "
        "ON s.session_key = u.session_key AND s.unit_id = u.unit_id"
    ).fetchone()
    cross_product = con.sql(
        "SELECT count(*) FROM core_spike_events s JOIN core_units u ON s.unit_id = u.unit_id"
    ).fetchone()
    assert correct == (10,)
    assert cross_product == (20,)


def test_nothing_is_registered_unless_asked_for(two):
    """As `Packet.duckdb`: binding a view reads a footer, a round trip per table over a store."""
    duckdb = pytest.importorskip("duckdb")
    assert duckdb
    con = two.duckdb()
    assert con.sql("SELECT count(*) FROM duckdb_views() WHERE NOT internal").fetchone()[0] == 0


def test_a_query_names_what_it_needs(two):
    duckdb = pytest.importorskip("duckdb")
    assert duckdb
    con = two.duckdb(for_query="SELECT * FROM core_units")
    assert con.sql("SELECT count(*) FROM core_units").fetchone()[0] == 4


def test_a_resource_no_packet_holds_is_not_a_view(two):
    assert two._view("core.absent") is None
    with pytest.raises(ResourceNotFoundError) as refused:
        two.table("core.absent")
    assert refused.value.resource_id == "core.absent"


# -- what R86 requires and does not specify --------------------------------------------


def test_a_multi_session_packet_refuses_a_table_that_cannot_say_which(packet_root, tmp_path):
    """Part 05 §13.1 requires a discriminator derived from packet and session, not a guessed name."""
    root = tmp_path / "two_sessions"
    shutil.copytree(packet_root, root)
    i32 = pa.int32()
    sessions = pa.table(
        {
            "session_id": pa.array([SESSION, SESSION + 1], type=i32),
            "session_name": pa.array([SESSION_NAME, SECOND_NAME]),
            "subject_id": pa.array([7, 8], type=i32),
            "session_start_time": pa.array([1_756_000_000_000_000] * 2, type=pa.timestamp("us", tz="UTC")),
        }
    )
    pq.write_table(sessions, root / "tables/core/sessions.parquet")
    # A scoped table reaching core.sessions through a parent rather than carrying the column.
    anchors = pa.table({"clock_id": pa.array([3, 4], type=i32), "anchor_index": pa.array([0, 1], type=i32)})
    pq.write_table(anchors, root / "tables/core/clock_anchors.parquet")
    manifest = json.loads((root / "packet.json").read_text())
    manifest["sessions"] = [SESSION_NAME, SECOND_NAME]
    manifest["resources"].append(
        {
            "resource_id": "core.clock_anchors",
            "declaration_id": "core.clock_anchors",
            "uri": "tables/core/clock_anchors.parquet",
            "validation_state": "passed",
        }
    )
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    registry = read_registry(root)
    registry["resources"]["core.clock_anchors"] = {
        "content_class": "core",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "optional",
        "table": {
            "columns": [
                {
                    "name": "clock_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "assigned",
                    "description": "",
                },
                {
                    "name": "anchor_index",
                    "type": "int32",
                    "presence": "required",
                    "role": "sequence_position",
                    "description": "",
                },
            ],
            "primary_key": ["clock_id", "anchor_index"],
            "references": [{"columns": ["clock_id"], "resource": "core.units", "resource_columns": ["unit_id"]}],
            "rules": [],
        },
    }
    install_registry(root, registry)

    data = open_dataset([root])
    assert len(data.sessions) == 2
    assert data.table("core.units").column("session_key").to_pylist() == [0, 0]
    with pytest.raises(MultiSessionUnresolved, match="core.clock_anchors"):
        data.table("core.clock_anchors")


def test_an_already_opened_packet_may_be_handed_over(packet_root):
    assert open_dataset([open_packet(packet_root)]).sessions[0].session_name == SESSION_NAME
