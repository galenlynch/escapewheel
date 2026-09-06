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

## Shard size: AWS's guidance, and the fetch it comes from

Amazon publishes four numbers that bracket how big one object should be:

| | |
|---|---|
| 8-16 MB | recommended byte-range fetch size for parallel reads |
| 128 KB | minimum *billed* object size in Standard-IA, One Zone-IA, Glacier Instant Retrieval |
| 5 MB | smallest multipart part |
| 100 MB | size above which multipart upload is recommended |

Measured against `aind-open-data` from outside AWS, the reason for the band is visible in how
much of a fetch is spent waiting rather than moving bytes:

```text
range      median    MB/s   latency as a share of the fetch
128 KB    39.4 ms     3.4        86%
  1 MB    46.3 ms    22.6        73%
  4 MB   185.2 ms    22.6        18%
  8 MB   220.1 ms    38.1        15%
 16 MB   649.6 ms    25.8         5%
```

Round trip ~34 ms, single stream ~40 MB/s. Requiring a share *f* of the fetch to be transfer
gives `S = f/(1-f) * latency * bandwidth`, which at 90% is 12.2 MB -- inside AWS's band, and
4.5 MB from inside the region, where the latency is an order lower. `escapewheel_writer.arrays`
derives the size that way rather than storing 8-16 MB as a constant, since the constant is
only correct for one kind of reader.

## Sharding: keep the compressor inside

`sharding_indexed` exists so that a reader fetches one inner chunk out of a shard by byte
range. It stops doing that if the shard is wrapped in an outer codec, because the whole shard
must then be inflated to reach anything inside it. zarr-python applies a default compressor
when `compressors` is not given, so writing

```python
zarr.create_array(..., serializer=ShardingCodec(chunk_shape=inner, codecs=[BytesCodec(), ZstdCodec()]))
```

silently produces that -- and measured on 6,781 unit waveforms it costs **188 ms against
0.7 ms** to read one unit, with only a `ZarrUserWarning` to say so. Pass `compressors=None`
and put the compression inside the shard's own `codecs`.

Last run: zarr-python 3.3.0, numcodecs 0.16.5, Zarr.jl 0.10.2, Julia 1.12.0.
