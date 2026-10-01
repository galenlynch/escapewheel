"""The NWB adapter: one module per group of tables, composed by `source.NWBSource`.

- `names` -- the values and contact names every adapter reading the file shares.
- `file` -- the opened file, its tables, and its times as ticks.
- `devices`, `electrodes`, `signals`, `events` -- the method groups, each a base of `NWBSource`.
- `source` -- :class:`~escapewheel_writer.sources.nwb.source.NWBSource`.

A dialect overrides a hook by subclassing `NWBSource`, whichever group defines the hook.
"""

__all__: list[str] = []
