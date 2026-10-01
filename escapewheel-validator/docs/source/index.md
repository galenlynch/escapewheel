# Escapewheel Validator

Tools to validate escapewheel packets

## Installation

No release is published to an index; install from the monorepo:

```bash
git clone https://github.com/galenlynch/escapewheel.git
cd escapewheel/escapewheel-validator
uv sync
```

## Quick Start

```python
from escapewheel_reader import open_packet
from escapewheel_validator import validate

report = validate(open_packet("packet/"))
report.passed, report.errors, report.warnings
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
