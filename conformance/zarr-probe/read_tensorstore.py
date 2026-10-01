import importlib.metadata

import numpy as np
import tensorstore as ts
from sets import arrays

print("tensorstore", importlib.metadata.version("tensorstore"))
for group, name, path, version, expected in arrays():
    spec = {
        "driver": "zarr3" if version == 3 else "zarr",
        "kvstore": {"driver": "file", "path": str(path.resolve())},
    }
    try:
        total = int(np.asarray(ts.open(spec, read=True).result().read().result()).astype(np.int64).sum())
        print(f"{group}/{name}:", "READ OK" if total == expected else f"WRONG {total}")
    except Exception as error:
        # The cause is last in TensorStore's chained message, before its source locations.
        print(f"{group}/{name}: FAIL {str(error).split(' [source')[0][-160:]}")
