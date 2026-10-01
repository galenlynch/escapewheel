# Escapewheel Writer

Tools to write escapewheel packets

## Installation

No release is published to an index; install from the monorepo:

```bash
git clone https://github.com/galenlynch/escapewheel.git
cd escapewheel/escapewheel-writer
uv sync
```

## Quick Start

```bash
escapewheel import session.toml --check  # everything wrong, before any I/O
escapewheel import session.toml          # stage, validate, commit
```

## Documentation

```{toctree}
:maxdepth: 2
:caption: Contents

api
performance
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
