# Zarr cross-language conformance probe

Produces the evidence cited in
[R3 §7.3](../../revisions/accepted/R3-cross-language-physical-floor.md) and the reader matrix of
[Part 10 §5](../../spec/parts/10_performance_notes.md#ew-zarr-codec-floor-evidence),
which [R137](../../revisions/accepted/R137-the-zarr-floor-admits-blosc-zstd-and-sharding-and-a-feature-outside-a-floor-is-a-resource-finding.md)
raised the v3 reader floor on and
[R157](../../revisions/accepted/R157-the-reader-floor-bounds-an-arrays-byte-order.md) bounded
the v2 floor's byte order on.

Four writers produce array sets, each with an `expected.json` of element sums:

- `write.py` writes the floor and v2 arrays under `arrays/`;
- `write_more.py` writes Blosc shuffle modes and codecs and sharded pipelines under `more/`;
- `write_writer.py` writes the reference writer's default, sharded, and delta outputs under
  `writer_arrays/`;
- `write_endian.py` writes big-endian arrays under `endian/`, four as v3 and one as v2. The sum of
  their unswapped bytes differs from the sum of their values, so a reader that ignores the declared
  byte order reports a wrong sum.

Five readers check every set by int64 element sum. Re-run them
against newer library versions before trusting the floor. From this directory:

```bash
uv run --no-project --with 'zarr>=3' --with numcodecs --with zstandard python write.py
uv run --no-project --with 'zarr>=3' --with numcodecs --with zstandard python write_more.py
uv run --project ../../escapewheel-writer python write_writer.py
uv run --no-project --with 'zarr>=3' --with numcodecs --with zstandard python write_endian.py

uv run --no-project --with 'zarr>=3' --with numcodecs --with zstandard python read_zarr_python.py
uv run --no-project --with 'zarr>=3' --with tensorstore python read_tensorstore.py
uv run --no-project --with 'zarr>=3' --with zarrs python read_zarrs.py   # strict: no Python fallback
julia read_all.jl
npm ci && node read.mjs                                                   # zarrita

julia read.jl                                                             # R3's original Julia read
julia dtype.jl                                                            # dtype + axis-order surface
uv run --with 'zarr>=3' --with numcodecs --with zstandard python realistic.py  # codec sizes on noisy int16
```

The Julia scripts use the `zarrtest` environment under `~/.julia/environments`, which needs `Zarr`
added once.

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
zarr.create_array(
    ..., serializer=ShardingCodec(chunk_shape=inner, codecs=[BytesCodec(), ZstdCodec()])
)
```

silently produces that -- and measured on 6,781 unit waveforms it costs **188 ms against
0.7 ms** to read one unit, with only a `ZarrUserWarning` to say so. Pass `compressors=None`
and put the compression inside the shard's own `codecs`.

The floor probes last ran (2026-09-24) on zarr-python 3.4.0, numcodecs 0.17.0, Zarr.jl 0.10.2 on Julia 1.12.7,
TensorStore 0.1.85, zarrs-python 0.2.3, zarrita 0.7.5 on Node 22.22.2. The big-endian set ran on
2026-10-01 with the same versions.
