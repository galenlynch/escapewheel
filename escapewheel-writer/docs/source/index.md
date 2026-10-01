# Escapewheel Writer

Build Escapewheel packets from a recipe.

## Installation

No release is published to an index; install from the monorepo:

```bash
git clone https://github.com/galenlynch/escapewheel.git
cd escapewheel/escapewheel-writer
uv sync
```

## Quick start

A recipe names a session's sources and the resources each one owns. The command line checks it,
then builds, validates and commits the packet:

```bash
escapewheel import session.toml --check  # report every problem, before any I/O
escapewheel import session.toml          # stage, validate, commit
```

The same build in Python:

```python
import json

from escapewheel_writer import Recipe, import_packet

recipe = Recipe.load("session.toml")
registry = json.loads(recipe.registry.read_text())
report = import_packet(recipe, registry)
```

`import_packet` is `build`, which returns a `PacketWriter` holding the staged packet, followed by
that writer's `commit`. Call the two yourself to add records between them.

## Documentation

```{toctree}
:maxdepth: 2
:caption: Contents

api
design
performance
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
