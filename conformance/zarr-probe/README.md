# Zarr cross-language conformance probe

Produces the evidence cited in
[R3 §7.4](../../revisions/R3-cross-language-physical-floor.md).

Writes Zarr arrays from `zarr-python` under a range of codec configurations, then reads
each back from `Zarr.jl` and verifies values by element sum. Re-run this against newer
library versions before trusting R3's codec floor.

```bash
uv run --with 'zarr>=3' --with numcodecs --with zstandard python write.py   # writes arrays/
julia read.jl                                                              # reads them from Julia
julia dtype.jl                                                             # dtype + axis-order surface
uv run --with 'zarr>=3' --with numcodecs --with zstandard python realistic.py  # codec sizes on noisy int16
```

Last run: zarr-python 3.3.0, numcodecs 0.16.5, Zarr.jl 0.10.2, Julia 1.12.0.
