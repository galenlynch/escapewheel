"""Executable queries projected by the informative example part."""

import pyarrow as pa


def test_unit_quality_query_uses_the_packet_local_unit_key():
    """Part 08 §4 joins current core and extension shapes through `unit_id` alone."""
    import duckdb

    con = duckdb.connect()
    con.register("core_units", pa.table({"unit_id": [1, 2]}))
    con.register(
        "aind_unit_qc_metrics",
        pa.table({"unit_id": [1, 2], "isi_violations_ratio": [0.1, 0.2]}),
    )
    con.register(
        "core_unit_quality_labels",
        pa.table(
            {
                "unit_id": [1, 2],
                "source": ["decoder", "decoder"],
                "normalized_label": ["sua", "mua"],
            }
        ),
    )
    rows = con.sql(
        """SELECT q.normalized_label, count(*) AS units,
                  round(avg(m.isi_violations_ratio), 3) AS isi
           FROM core_units u
           JOIN aind_unit_qc_metrics m USING (unit_id)
           JOIN core_unit_quality_labels q USING (unit_id)
           WHERE q.source = 'decoder'
           GROUP BY 1 ORDER BY units DESC"""
    ).fetchall()
    assert set(rows) == {("sua", 1, 0.1), ("mua", 1, 0.2)}
