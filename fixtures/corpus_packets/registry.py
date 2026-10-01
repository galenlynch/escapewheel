"""The registries a corpus packet binds, read from the specification, not restated."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = json.loads((ROOT / "spec" / "artifacts" / "logical_schemas.json").read_text())
_PROFILE = json.loads(
    (ROOT / "spec" / "artifacts" / "physical_profiles" / "escapewheel-portable-v0.1.json").read_text()
)
#: Part 03 §5.4's overriding orders, read from the descriptor that owns them.
OVERRIDING_ORDERS = _PROFILE["interfaces"][_PROFILE["kind_interfaces"]["table"]].get("overriding_orders", {})

#: The one extension this corpus carries. Part 01 §3.10a makes an `interval_kind` naming a resource
#: the packet does not declare an error, and no core table specialises an interval -- so a packet
#: with intervals carries an extension by construction, and the corpus has to as well.
EXTENSION_ID = "dynamic_foraging"
EXTENSION = json.loads((ROOT / "extensions" / f"{EXTENSION_ID}.json").read_text())

#: The interval kind the fixture declares, which is the extension table that carries it.
KIND = "dynamic_foraging.trials"
