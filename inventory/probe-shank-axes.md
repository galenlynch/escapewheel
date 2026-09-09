# What states which way a shank's axes run

Measured on `ecephys_786867_2025-09-25_12-43-56`, across the three artifacts a packet is built
from. The question is what a writer may read to say that a probe frame's first axis runs across
the shank and its second along it — because a packet records `rel_x` and `rel_y` and says neither.

## 1. No source states it

| source | what it offers | states an axis? |
|---|---|---|
| the NWB's electrodes table | `rel_x`, `rel_y`, whose own descriptions read **"rel_x from merged"** and "rel_y from merged" | no — the description restates the column name |
| Open Ephys `settings.xml` | `<ELECTRODE_XPOS>` and `<ELECTRODE_YPOS>` per channel | no — x and y again, with no statement of what either measures |
| the sorted asset's `preprocessed/*.json` | `probe_0_planar_contour`, `shank_tips`, `probes_info` | no — it is a SpikeInterface provenance record (`CommonReferenceRecording`), and carries **none** of ProbeInterface's `ndim`, `si_units`, `contact_positions` or `contact_plane_axes` |

Three artifacts, three spellings of x and y, and no sentence anywhere saying which way either runs.

## 2. The geometry shows it and does not state it

`settings.xml` gives one probe **2 distinct `ELECTRODE_XPOS` values** — 27 µm and 59 µm — against
**192 distinct `ELECTRODE_YPOS`** spanning 0 to 2,865 µm. The preprocessed record's
`probe_0_planar_contour` outlines the same shank at roughly 70 µm across and 10 mm long.

A reader can see from that which axis is which. A writer may not conclude it: two counts and a
bounding box are values, and a probe whose contacts were equally numerous on both axes would
defeat the reading entirely. This is why an axis is filled from what a source states and not from
what its values look like.

## 3. What is stated is the model

All three artifacts name the probe, and agree:

```text
settings.xml          probe_name       "Neuropixels 2.0 - Single Shank"
                      probe_part_number "NP2000"
preprocessed JSON     manufacturer     "imec"
                      model_name       "NP2020"
                      description      "Neuropixels 2.0 single shank probe with cap"
```

A Neuropixels 2.0's contact geometry is fixed by imec's specification, so the model **is** the
statement of what the axes are — held in a document outside the packet, the way a species name is
held by NCBI Taxonomy and a strain by MGI.

That makes this the same shape as a declared authority: the packet names the nomenclature and does
not copy it. An adapter that knows the model can supply the axes, and what it is reading is imec's
specification rather than the file in front of it.

## 4. What this implies

- A probe frame's axes are **unfillable from the session's own artifacts**, so a packet built only
  from them declares none, and a consumer reports a probe coordinate's axes unresolvable.
- Filling them is a lookup keyed on `probe_part_number`, which is `core.probes.probe_type`
  already. Whether that lookup belongs in an adapter, in an extension, or in a declared authority
  is a schema question this inventory does not settle.
- The two-column-by-192-row geometry means the *packet* could carry the axes as a measurement, as
  `core.electrodes` positions rather than as a frame's declaration. Nothing asks for that today.
