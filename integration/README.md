# Integration

The package suites each test one implementation against fixtures of its own, so a writer and a
reader can each pass while disagreeing about the same packet. These tests commit a packet with
the writer, read it only through the reader's public API, and judge it with the validator, all
against the current registries.

```bash
uv run --project ../escapewheel-writer pytest              # the matrix
uv run --project ../escapewheel-writer python example.py   # rewrite Part 08's generated regions
```

This directory is not a project of its own: the writer's environment installs all three packages
from their sibling directories. `verify.py` runs `example.py` on every run and the tests on a full
run.

## The example packet

`example.py` builds it from the conformance corpus's valid session (`fixtures/build.py`) with every
shipped extension bound, and adds one resource of each kind the corpus lacks:

| resource | kind |
|---|---|
| `core.waveform_mean` | a packet-owned array |
| `core.probe0_lfp` | an external array, referenced and not copied |
| `analysis.spike_events` | a materialized analysis table, from `escapewheel_writer.materialize` |
| `analysis.unit_rates` | a derived analysis array, with its lineage |
| `aind_unit_qc.metrics` | an extension table beside the corpus's `dynamic_foraging.trials` |

Part 08 §§2–3 are generated regions filled from this packet's manifest, and `test_matrix.py`
fails when they no longer match it.

## The matrix

| cell | what fails it |
|---|---|
| core | the packet does not validate clean, or a table reads back with a different row count |
| manifest | `packet.json` breaks the published schema with `date-time` asserted, or a malformed timestamp passes |
| valid extension | an extension table is not declared under its own ID, not read back, or not validated |
| invalid extension | a row breaking an extension rule is committed, or a registry the contract rejects reaches the writer |
| derived resource | a derived array loses its lineage, or one without lineage is committed |
| external resource | an external array is copied, carries a digest, or goes unreported as unassessed |
| Part 08 | §§2–3 differ from this packet, or a §4 query fails or returns other rows |
