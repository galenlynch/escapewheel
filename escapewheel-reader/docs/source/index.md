# Escapewheel Reader

Read Escapewheel packets: Parquet tables, Zarr arrays, and the JSON manifest binding them.

## Installation

No release is published to an index; install from the monorepo:

```bash
git clone https://github.com/galenlynch/escapewheel.git
cd escapewheel/escapewheel-reader
uv sync
```

## Quick start

Open a packet, then pass it to the functions that read it:

```python
from escapewheel_reader import open_packet, spike_times, units

packet = open_packet("session_packet/")
good = units(packet, quality_label="sua")
spikes = spike_times(packet, units=good)  # a pyarrow.Table, ticks on the reference clock
```

For several packets at once, `open_packets` presents them as one relation.

## Documentation

```{toctree}
:maxdepth: 2
:caption: Contents

api
design
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
