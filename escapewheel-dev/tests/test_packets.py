import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from corpus_packets import VALID

import escapewheel_dev as ew


@pytest.fixture(scope="module")
def valid(tmp_path_factory):
    root = tmp_path_factory.mktemp("corpus") / VALID.name
    VALID.build(root)
    return root


def test_the_valid_packet_stores_only_declared_columns(valid):
    assert ew.undeclared_columns(ew.open_packet(valid)) == {}


def test_a_stored_column_nobody_declared_is_found(valid, tmp_path):
    packet = ew.open_packet(valid)
    path = packet.path("core.units")
    table = pq.read_table(path)
    pq.write_table(table.append_column("stray", pa.array([0] * table.num_rows)), path)
    try:
        assert ew.undeclared_columns(ew.open_packet(valid)) == {"core.units": ("stray",)}
    finally:
        pq.write_table(table, path)


def test_query_and_validate(valid):
    packet = ew.open_packet(valid)
    assert packet.sql("SELECT count(*) AS n FROM core_units")["n"][0].as_py() > 0
    assert ew.validate(packet).passed
