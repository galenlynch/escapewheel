# Escapewheel Validator

Validate Escapewheel packets against the registries they bind.

## Installation

No release is published to an index; install from the monorepo:

```bash
git clone https://github.com/galenlynch/escapewheel.git
cd escapewheel/escapewheel-validator
uv sync
```

## Quick start

Open a packet with the reader and pass it to `validate`:

```python
from escapewheel_reader import open_packet
from escapewheel_validator import validate

report = validate(open_packet("packet/"))
report.passed, report.errors, report.warnings
```

`escapewheel validate packet/` is the same call from the command line.

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
