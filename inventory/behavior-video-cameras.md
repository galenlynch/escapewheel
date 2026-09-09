# What a rig states about its behaviour cameras

Measured on `ecephys_786867_2025-09-25_12-43-56`, reading `rig.json` and `session.json` from the
sorted asset in `aind-open-data`. The question is where a camera's **view** lives — what
distinguishes `bottom_camera` from `side_camera_left` — because a packet records the videos and
nothing in it says what any of them shows.

## 1. The rig declares two cameras and the session names three

`rig.json` carries a `cameras` array of two assemblies:

| assembly | `camera_target` | `position` | `camera.name` | serial | model |
|---|---|---|---|---|---|
| `Right Camera assembly` | `Face side right` | **null** | `Right size of face camera` | `23022730` | Blackfly S BFS-U3-04S2M |
| `Bottom Camera assembly` | `Face bottom` | **null** | `bottom of face camera` | `23022721` | Blackfly S BFS-U3-04S2M |

`session.json`'s one `behavior-videos` data stream names **three**: `Face Side Left`,
`Face Side Right`, `Face Bottom`. The left camera the session recorded from is in no rig
assembly.

The packet holds **four** media assets — `bottom_camera`, `side_camera_left`,
`side_camera_right`, and `clip`. So the three artifacts disagree about how many cameras there
were, and `clip` is described by neither JSON.

## 2. The view is stated; the pose is modelled and empty

`camera_target` is filled on both assemblies and is exactly the fact a consumer wants: `Face side
right`, `Face bottom`. It is a **label**, not a geometry — a named view rather than a position and
an orientation.

`position` is present in the schema and **null on both**. So a pose is available to be recorded
and is not recorded, which is the control case R66 §1.3 states: a field a producer models and
never fills is not evidence anyone needs it. `rig_axes` and `origin` are null too, so the rig
declares no coordinate frame for a pose to be in even if one were given.

Both cameras carry a real, distinct **serial number**, a manufacturer and a model, which is what
R67 §2.2 makes identity: a camera is an ordinary `core.devices` row today, and the packet has none
— its 21 devices are seven probes, a `SniffDetector` and the Open Ephys acquisition chain.

## 3. One camera has five names

The right-side camera is called:

```text
Right Camera assembly          rig.json, the assembly
Right size of face camera      rig.json, the camera (sic)
Face side right                rig.json, camera_target
Face Side Right                session.json, camera_names
side_camera_right              the video file's stem, and the packet's media_asset_name
```

None of the five is derivable from another by rule, and the packet carries only the last. That is
why the camera has to be a device a media asset references rather than a string a consumer parses:
R85 §2.2 permits a name to encode position and requires only that it be unique, so a name is a
per-packet label and never a cross-packet fact.

## 4. What this implies for the schema

- A camera is a `core.devices` row, identified by its serial, and a media asset should reference
  it. The adapter reads `rig.json` already, for the rig's time zone alone (`sources/aind.py`).
- The **view** is a label the source states, so it is carried as a label — not as a pose. A pose
  column would be the principled shape and would be null in every row this dataset can produce.
- Where the label goes is a schema question this inventory does not settle: `camera_target`
  describes the camera rather than the video, so it belongs beside the device, and a rig with one
  camera repositioned mid-session would need it beside the asset instead. Nothing here does that.
- The count disagreement is an upstream defect, not a schema gap: two assemblies, three named
  cameras, four videos. `upstream-defects.md` is where that belongs if it recurs.
