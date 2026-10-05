# Examples

Each example is a project of its own that depends on the escapewheel packages the way a project
outside this repository would, and a test suite that builds what it shows into a validated packet.
`verify.py` runs each suite on a full run.

| example | shows |
|---|---|
| [`lick-wheel/`](lick-wheel/) | a registered adapter delivering events with payloads, a sampled signal as a Zarr array on its own clock, the anchors placing that clock on the rig's, a source on an object store, a stated fact and a run report, in process and over `stream-v0.1` and `files-v0.1` |

`extensions/AUTHORING.md` explains the decisions they embody. An extension of one's own starts from
the copier template it names, which generates a project holding an extension and its adapter.
