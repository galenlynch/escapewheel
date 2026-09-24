import numpy as np
import zarr
import zarrs

from sets import arrays

# Strict: a codec zarrs cannot run fails rather than falling back to zarr-python's pipeline.
zarr.config.set(
    {
        "codec_pipeline.path": "zarrs.ZarrsCodecPipeline",
        "codec_pipeline.strict": True,
        "codec_pipeline.validate_checksums": True,
    }
)
print("zarrs-python", zarrs.__version__)
for group, name, path, _, expected in arrays():
    try:
        total = int(np.asarray(zarr.open_array(str(path), mode="r")[:]).astype(np.int64).sum())
        print(f"{group}/{name}:", "READ OK" if total == expected else f"WRONG {total}")
    except Exception as error:
        print(f"{group}/{name}: FAIL {type(error).__name__}: {str(error)[:150]}")
