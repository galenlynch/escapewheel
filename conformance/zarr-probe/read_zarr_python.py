import importlib.metadata

import numpy as np
import zarr
from sets import arrays

print("zarr-python", zarr.__version__, "numcodecs", importlib.metadata.version("numcodecs"))
for group, name, path, _, expected in arrays():
    try:
        total = int(np.asarray(zarr.open_array(str(path), mode="r")[:]).astype(np.int64).sum())
        print(f"{group}/{name}:", "READ OK" if total == expected else f"WRONG {total}")
    except Exception as error:
        print(f"{group}/{name}: FAIL {type(error).__name__}: {str(error)[:150]}")
