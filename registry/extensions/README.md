# Extensions

An extension is a **registry document in R2's format** (R17 §2), namespaced by its `extension_id`.
Nothing here is a second format, and nothing here ships code: a packet embeds these documents, so
reading one of their tables needs nothing installed.

| | tables | columns | drawn from |
|---|---|---|---|
| `dynamic_foraging` | `trials`, `blocks` | 23 | the 10 trial columns measured to vary in a real session, plus its blocks |
| `aind_unit_qc` | `metrics`, `waveform_metrics` | 56 | 48 of the 74 columns the real NWB's `units` table carries |
| `aind_opto` | `stimulations` | 16 | the 17 `laser_*` columns the real NWB's `trials` table carries |

## Why these, and why they are not core

Measured on `ecephys_776259_2025-04-09`, comparing what each NWB `DynamicTable` carries against
what `02` models by name:

```
NWB DynamicTable  columns  unmodelled
units                  74          73
electrodes             21          19
trials                 68          67
```

The comparison is naive — it matches on name, so a renamed equivalent (`num_spikes` against
`n_spikes`, `unit_name` against `local_unit_label`) counts as unmodelled, and R28's
`core.unit_coordinates` covers the CCF columns under different names. It is still the shape of
the thing: **a `DynamicTable` accretes, and what accretes is a task's or a pipeline's vocabulary,
not a format's.** R17 §1 measured the same file and put it plainly — most columns in it conform to
nothing.

That is exactly what an extension is for, and it is why R43 §3, R16 §5, R9 §2 and `09` §2.3 all
send their columns here.

## Tagging and inactivation are one extension

They differ in the **values**, not the columns: a short pulse train against sustained
illumination, on the same `wavelength_nm`, `power_mw`, `duration_s`, `frequency_hz`,
`ramping_down_s`. So `aind_opto.stimulations` is one table with an open `protocol` saying which,
rather than two schemas of the same shape. Splitting them would be R3 §3.0's duplication with the
intent encoded in a table name.

## Not yet written

**`vr_foraging`.** `inventory/vr-foraging-packaging.md` describes it in detail — seven tables, a
`Site` model of ~30 fields, eleven index columns, a half-open interval, and `odor_concentration`
as a `list[float]` that R3 §2.1 forbids and R54 §2.6 says must be converted. But the description
is prose, and no packet here has been built from that pipeline. Drafting a registry from a
document rather than from data would invent the types, which is the one thing
`nwb-lake extension` exists to avoid: point it at `sites.parquet` and it reads them.
