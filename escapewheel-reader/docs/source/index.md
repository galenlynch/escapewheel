# Escapewheel Reader

Tools to read escapewheel packets

## Installation

No release is published to an index; install from the monorepo:

```bash
git clone https://github.com/galenlynch/escapewheel.git
cd escapewheel/escapewheel-reader
uv sync
```

## Quick Start

```python
from escapewheel_reader import open_packet

packet = open_packet("session_packet/")
trials = packet.intervals(session_id=1, interval_kind="task.trials")  # a pyarrow.Table
```

## Documentation

```{toctree}
:maxdepth: 2
:caption: Contents

api
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
