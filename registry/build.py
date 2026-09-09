"""Build the schema registry from the specification, the revisions, and the rule set.

Two sources, kept apart because they are maintained differently.

**Structure** — columns, keys, references, ordering — is *derived*. ``parse02.py`` reads 02's
markdown tables and the transformations below apply R3-R11, each labelled with the revision
that mandates it, so a column's type or presence traces to the decision that set it. Changing
structure means changing a revision and re-running this script.

**Tier 2 rules** are *hand-authored*, in ``rules.json``, because nothing derives a check that
the structure cannot imply.

Merging them here keeps ``logical_schemas.json`` wholly generated, so it can be rebuilt
without losing hand-written work. Do not edit it directly.
"""
import json
from pathlib import Path

from parse02 import parse

HERE = Path(__file__).resolve().parent
OUT = HERE / "logical_schemas.json"

#: Where each hand-written schema is vendored. A sibling distribution cannot read a file from
#: another repository, so it carries a copy -- which makes the copy an output of this build.
VENDORED = {
    "registry.schema.json": HERE.parent / "escapewheel-validator/src/escapewheel_validator/schemas/registry.schema.json",
    "manifest.schema.json": HERE.parent / "escapewheel-reader/src/escapewheel_reader/schemas/manifest.schema.json",
    "sources.schema.json": HERE.parent / "escapewheel-reader/src/escapewheel_reader/schemas/sources.schema.json",
}
RULES = HERE / "rules.json"

# 02's type spellings -> R2 §4 vocabulary. Nested spellings are removed by R3, not mapped.
TYPES = {
    "string": "string", "int32": "int32", "int64": "int64", "float32": "float32",
    "float64": "float64", "bool": "bool", "timestamp": "timestamp", "date": "date",
    "date or timestamp": "date",                      # R4 §3.6
    "struct/map/json_string": "json_string",          # R3 §2.1
}


def presence(required: str, typ: str) -> str:
    """02's yes/no/conditional -> R2 §5's three states.

    json_string columns are optional because R3 §2.1 confines JSON to optional columns:
    a conforming reader must satisfy every required column without a parser.
    """
    if required == "yes":
        return "required"
    if typ == "json_string":
        return "optional"
    return "nullable"                                  # 02: prefer present-nullable


class _Since(list):
    """The revision whose block is executing, which also records that the block ran.

    Assignment is the only way a block declares itself, so recording it here is what keeps
    `derived_from` from drifting: a revision that stamps a column can no longer be applied and
    left out of the list, which R54, R65 and R66 each were.
    """

    def __init__(self, initial):
        super().__init__(initial)
        #: Every revision assigned during this build, by number.
        self.applied: set[str] = set()

    def __setitem__(self, index, value):
        if value:
            self.applied.add(value.split()[0])
        super().__setitem__(index, value)


#: The revision whose block is executing, stamped onto whatever it creates (R29 §2). A block
#: sets it once; `col` and `new` read it, so the comment naming the revision and the data
#: recording it cannot disagree. None while 02 is being carried forward, because a column 02
#: declares and no revision touched carries no `since` -- absence is the meaningful state.
SINCE = _Since([None])

#: Revisions applied above that stamp no column, so nothing records them but this list: a rule,
#: a key, a sort order, a withdrawal, or a decision about the format rather than about a table.
#: R42 is withdrawn and so is not here.
UNSTAMPED = (1, 2, 4, 7, 10, 12, 14, 15, 17, 21, 22, 24, 26, 29, 30, 31, 32, 34, 35, 36, 37, 40,
             43, 46, 47, 48, 51, 52, 55, 57, 58, 60, 61, 62, 63, 64, 69, 71, 72, 74, 75, 76, 77, 78, 79,
             80, 82, 84, 86, 87, 90, 92, 93, 94)


#: Every column's role (R48 §2.1), keyed by column name. **Required**: a name absent here is a
#: build error, so a column cannot be added without deciding what kind of thing it is. There is
#: deliberately no default -- a default would make a forgotten classification indistinguishable
#: from a deliberate one, which is the drift R48 exists to stop.
#:
#: Keyed by name rather than by (table, column) because a name means one thing throughout: no
#: name in the registry carries two roles. R50's renames are what made that true -- before them
#: `supersedes` held a run ID without saying so, and `step_ticks` read as a coordinate while
#: holding a duration.
#: Names that exist only between `02` and the revision that renames them (R5 §5, R8 §2). They
#: need a role because they pass through `col`, and they are `data` for the same reason their
#: renamed forms are: R8 §2 made them strings, and a string cannot be an offset (R48 §2.4).
TRANSIENT = ("local_electrode_index", "local_channel_index", "local_unit_index")

#: Names on tables and columns a revision withdraws, which `02` still defines and which therefore
#: pass through `col` before being struck. They carry their honest role rather than a placeholder,
#: so that reviving one would not revive a wrong classification with it.
WITHDRAWN = {
    # R9 §2: the entity/activity/edge provenance graph.
    "activity_id": "identifier", "entity_id": "identifier", "source_entity_id": "identifier",
    "target_entity_id": "identifier", "resource_id": "identifier",
    "entity_type": "data", "relationship_type": "data",
    # R5 §4: core.unit_spike_chunks, withdrawn with its table.
    "chunk_index": "sequence_position", "t_min_tick": "coordinate", "t_max_tick": "coordinate",
    # R3 §3.3: the array declares its own dtype.
    "dtype": "data",
    # R59 §2.1: an atlas annotation states a fact about a position, so it moves to the coordinate.
    "brain_region": "data",
}

ROLES: dict[str, str] = dict.fromkeys(TRANSIENT, "data") | WITHDRAWN
for _role, _names in {
    "identifier": (
        "array_asset_id", "calibration_id", "clock_id", "condition_id", "coordinate_array_asset_id", "curation_id",
        "default_electrode_id", "device_id", "electrode_id", "event_id", "event_stream_id",
        "input_array_asset_id", "media_asset_id", "parent_clock_id", "parent_curation_id", "probe_id",
        "processing_run_id", "reference_clock_id", "region_id", "session_id", "sorting_run_id",
        "source_file_id",
        "interval_id", "parent_device_id", "source_session_id", "stimulus_id", "stream_id", "subject_id", "supersedes_run_id", "trial_id",
        "unit_id",
    ),
    "coordinate": (
        "first_spike_tick", "last_spike_tick", "origin_tick", "parent_tick", "start_tick", "stop_tick",
        "t_tick", "t_zero_tick", "time_bucket_tick",
    ),
    "structural_index": (
        "axis_index", "channel_index", "frame_index", "point_index",
    ),
    "sequence_position": (
        "anchor_index",
    ),
    # R55 §2.1. A column a consumer resolves to a table, which `data` said nothing about -- so
    # nothing checked that `scope_kind` held a resource ID at all.
    "discriminator": (
        "detail_kind", "interval_kind", "scope_kind",
    ),
    "data": (
        "activity_type", "amplitude", "amplitude_unit", "calibrated_at", "calibration_name",
        "calibration_type", "channel_label", "choice",
        "chosen_at", "code_uri", "confidence", "conversion", "coordinate_frame",
        "coordinate_basis", "coordinate_position_column", "coordinate_resource", "coordinate_unit",
        "created_at", "description", "region_label",
        "curation_tool", "curation_tool_version", "curator", "date_of_birth", "dimension_name", "dropped",
        "ended_at", "event_type", "experimenter", "firing_rate_hz", "firmware_version", "format",
        "genotype", "hardware_version", "impedance_ohm", "input_unit", "input_value",
        "insertion_name", "institution", "inter_sample_shift", "is_primary", "kind", "label",
        "local_channel_label", "local_electrode_label", "local_unit_label", "manufacturer", "metadata",
        "model", "modified_at", "n_spikes", "name", "normalized_label", "notes", "offset", "origin",
        "origin_value", "output_unit", "output_value", "parameters", "parent_port", "payload",
        "probe_type", "pts", "pts_rate_den",
        "pts_rate_num", "quality_label",
        "quality_label_source", "reason", "rewarded", "sample_rate_hz", "scope",
        "semantic_type", "serial_number", "session_description", "session_end_time", "session_start_time",
        "sex", "sha256", "size_bytes", "software_name", "software_version", "sorter_name", "sorter_version",
        "source", "species", "started_at", "status", "step_tick_den", "step_tick_num", "step_value",
        "strain", "tag", "target_region", "task_name", "tick_rate_den", "tick_rate_hz", "tick_rate_num",
        "tick_zero_utc", "transform_offset", "transform_slope", "transform_to_parent", "unit", "uri",
        "x_um", "y_um", "z_um",
    ),
}.items():
    ROLES.update(dict.fromkeys(_names, _role))



#: R53 §2.3. Whether an identifier is the source's own value or a number this format chose.
#: Not derivable: the sorter supplies `unit_ids` as int64 and the writer replaced them with
#: composed strings, so what decides this is whether the value survives the write.
IDENTITY: dict[str, str] = {
    # Carried -- the source's own, so two independent builds agree without being told to.
    "interval_id": "carried",         # R54 §2.2: each kind keeps its source's own numbering
    "trial_id": "carried",            # NWB intervals/trials/id, int64, already 0..n
    "unit_id": "assigned",            # R81 §2.1: the packet numbers its units; the sorter's
                                      # label stays in local_unit_label, which R53 §2.3 requires
    # electrode_id looked carried and is not: `_electrode_ids` composes (group, channel)
    # because no NWB column is unique on its own -- electrode_name repeats across the shanks of
    # a quad-base probe, and channel_name is per-probe.
    "electrode_id": "assigned",
    "region_id": "carried",           # the atlas's structure number, which coordinate_frame names
    # Declared until R81 §2.7 drops the column: it exists earlier in this build.
    "default_electrode_id": "assigned",
    # Assigned -- this format chose the number, and something must record what it stands for.
    "array_asset_id": "assigned",
    "calibration_id": "assigned",
    "clock_id": "assigned",
    "condition_id": "assigned",
    "coordinate_array_asset_id": "assigned",
    "curation_id": "assigned",
    "device_id": "assigned",
    "event_id": "assigned",
    "event_stream_id": "assigned",
    "input_array_asset_id": "assigned",
    "media_asset_id": "assigned",
    "parent_clock_id": "assigned",
    "parent_curation_id": "assigned",
    "probe_id": "assigned",
    "processing_run_id": "assigned",
    "reference_clock_id": "assigned",
    "session_id": "assigned",
    "sorting_run_id": "assigned",
    "source_file_id": "assigned",
    "source_session_id": "assigned",
    "parent_device_id": "assigned",
    "stimulus_id": "assigned",
    "stream_id": "assigned",
    "subject_id": "assigned",
    "supersedes_run_id": "assigned",
    # Withdrawn columns still pass through `col` on their way to being struck, so they need a
    # value; none reaches the built registry.
    "activity_id": "assigned", "entity_id": "assigned", "source_entity_id": "assigned",
    "target_entity_id": "assigned", "resource_id": "assigned",
}


#: R55 §2.2, §2.3.2. What a discriminator declares: whether an unresolvable value is a defect or
#: a fact, and which column holds the paired value where the shape is paired rather than shared-key.
#: Required and with no default, for R48 §2.2's reason.
DISCRIMINATOR: dict[str, dict[str, str]] = {
    # R49 §2.2: a run may be about a rig or a camera the packet does not hold, so a kind naming
    # nothing is what the packet has to say, not a finding against it.
    "scope_kind": {"resolves": "optional", "discriminates": "scope"},
    # R54 §2.1: an interval whose kind names no resource is uninterpretable -- the row says a
    # span exists and nothing says what it was. R55 §2.3's shared-key shape, so no
    # `discriminates`: the detail table joins on the whole key rather than on a paired value.
    "interval_kind": {"resolves": "required"},
    # R89 §2.5: a calibration whose shape core does not define points at the table that does. A
    # kind naming a table the packet does not carry says the content is unrecorded rather than
    # that the row is wrong, which is R49 §2.2's judgement. Shared-key, so no `discriminates`:
    # a detail table is keyed by its calibration and so has a composite key (R55 §2.3.1).
    "detail_kind": {"resolves": "optional"},
}


def discriminator_of(name: str) -> dict[str, str]:
    """Return a discriminator's declarations, refusing one nobody has classified."""
    try:
        return DISCRIMINATOR[name]
    except KeyError:
        raise SystemExit(
            f"column {name!r} is a discriminator and declares no `resolves`; add it to "
            "DISCRIMINATOR (R55 §2.2). The choice is required or optional."
        ) from None


#: R56 §2.1. A unit a column's name already encodes, declared from the name at one point so a
#: new column carrying one cannot be added without it by forgetting -- the discipline `role_of`
#: and `identity_of` apply to role and identity. A unit that varies row to row is not here; it
#: is `unit_from`, which names the column carrying it and must be declared at the call site.
UNIT_SUFFIX = {"_um": "um", "_hz": "Hz", "_ohm": "ohm", "_bytes": "byte"}


def unit_of(name: str) -> str | None:
    """Return the unit a column's name encodes, or None where it encodes none."""
    for suffix, unit in UNIT_SUFFIX.items():
        if name.endswith(suffix):
            return unit
    return None


def identity_of(name: str) -> str:
    """Return whether an identifier was carried or assigned, refusing an unclassified one."""
    try:
        return IDENTITY[name]
    except KeyError:
        raise SystemExit(
            f"identifier {name!r} declares no identity; add it to IDENTITY (R53 §2.3). "
            "The choice is carried (the source's own value) or assigned (a number we chose)."
        ) from None


def role_of(name: str) -> str:
    """Return a column's role, refusing a column nobody has classified (R48 §2.2)."""
    try:
        return ROLES[name]
    except KeyError:
        raise SystemExit(
            f"column {name!r} declares no role; add it to ROLES (R48 §2.2). "
            "The choice is data, identifier, coordinate, structural_index or sequence_position."
        ) from None

#: R56. Where a coordinate's clock comes from, and where a value's unit does, for the columns
#: convention does not settle. A coordinate beside a `clock_id` needs no entry -- R56 §2.2 makes
#: that the default -- so these are exactly the cases that were prose.
CONTEXT: dict[tuple[str, str], dict[str, str]] = {
    # Two coordinates on two clocks in one table, distinguished only by a description until now.
    ("core.clock_anchors", "parent_tick"): {"clock_from": "core.clocks.parent_clock_id"},
    # The clock is named, and not `clock_id` (R39 §2).
    ("core.sessions", "t_zero_tick"): {"clock_from": "reference_clock_id"},
    # R38 §3 gave the sorting run a clock precisely so a unit's ticks have one.
    # The stream's clock, reached through the stream (R25 §2).
    ("core.event_stream_observation_intervals", "start_tick"): {"clock_from": "core.event_streams.clock_id"},
    ("core.event_stream_observation_intervals", "stop_tick"): {"clock_from": "core.event_streams.clock_id"},
    # R11 §2: the unit is a property of the sorting context, not of the spike.
    # R19 §2: an offset is in the converted value's unit, which the asset carries. `conversion`
    # gets no entry: it is a ratio of two units and so is in neither of them.
    ("core.array_assets", "offset"): {"unit_from": "unit"},
    ("analysis.array_assets", "offset"): {"unit_from": "unit"},
}


def col(name, typ, pres, desc, since=None, determined_by=None):
    role = role_of(name)
    if role == "identifier":
        # R53 §2.1. Declared at one point rather than at 110 call sites, so a new identifier
        # cannot be added as a string by forgetting.
        typ = "int64" if typ == "int64" else "int32"
    entry = {"name": name, "type": typ, "presence": pres, "role": role, "description": desc}
    if role == "identifier":
        entry["identity"] = identity_of(name)
    if role == "discriminator":
        entry.update(discriminator_of(name))
    if role == "data" and (measured := unit_of(name)):
        entry["unit"] = measured
    if stamp := (since or SINCE[0]):
        entry["since"] = stamp
    if determined_by is not None:
        entry["determined_by"] = list(determined_by)
    return entry


def expand(template: str, resource: str, call: dict, key: list[str]) -> list[dict[str, str]]:
    """Expand a rules.json template invocation into concrete Tier 2 rules (R24 §3).

    Templates stay a build-time device: the registry a packet embeds carries plain SQL, so no
    validator has to learn a new vocabulary to run them.

    Parameters
    ----------
    template : str
        Template name; only ``interval`` exists.
    resource : str
        The table being expanded for.
    call : dict
        The invocation, carrying the template's parameters.
    key : list of str
        The table's primary key, used to identify offending rows.

    Returns
    -------
    list of dict
        Rules in the same shape a hand-authored one has.
    """
    if template != "interval":
        raise SystemExit(f"{resource}: unknown rule template {template!r}")

    name = resource.replace(".", "_")
    start, stop = call["start"], call["stop"]
    report = ", ".join(key)
    rules = [{"id": f"{resource}.interval_valid", "level": "error",
              "message": f"{stop} precedes {start}",
              "sql": f"SELECT {report}, {start}, {stop} FROM {name} WHERE {stop} < {start}"}]

    subject = call.get("partition_of")
    if subject is None:
        return rules

    # R47 §2.3: `index` is optional. Without one the rule orders by `start`, which is what it
    # compares against, so the check is an overlap test and nothing else -- ordering by a stored
    # index was correct only while index order happened to be time order, which nothing required.
    index, op = call.get("index"), call["overlap_op"]
    by = ", ".join(subject)
    if index is not None:
        rules.append({"id": f"{resource}.index_contiguous", "level": "error",
                      "message": f"{index} is not contiguous from 0",
                      "sql": (f"SELECT {by}, COUNT(*) AS n FROM {name} GROUP BY {by} "
                              f"HAVING MAX({index}) <> COUNT(*) - 1 OR MIN({index}) <> 0")})
    rules.append({"id": f"{resource}.non_overlapping", "level": "error",
                  "message": call["overlap_message"],
                  "sql": (f"SELECT {report}, {start}, {stop} FROM (SELECT *, LAG({stop}) OVER "
                          f"(PARTITION BY {by} ORDER BY {index or start}) AS prev_stop FROM {name}) "
                          f"WHERE prev_stop IS NOT NULL AND {start} {op} prev_stop")})
    return rules


def build() -> dict:
    src = parse()
    tables = {}

    # ---- carry 02 forward, applying R3 §2.1's type floor -------------------------------
    for name, t in src.items():
        columns = []
        for c in t["columns"]:
            typ = TYPES.get(c["type"])
            if typ is None:
                continue                               # nested; removed or replaced below
            columns.append(col(c["name"], typ, presence(c["required"], typ), c["description"]))
        tables[name] = {
            "columns": columns,
            "primary_key": t["primary_key"],
            "references": [{"columns": r["columns"], "resource": r["resource"],
                            "resource_columns": r["resource_columns"] or r["columns"]}
                           for r in t["references"]],
            "rules": [],
        }

    def T(n): return tables[n]
    def drop_col(t, n): T(t)["columns"] = [c for c in T(t)["columns"] if c["name"] != n]
    def add_col(t, c, after=None):
        cols = T(t)["columns"]
        i = next((k for k, x in enumerate(cols) if x["name"] == after), len(cols) - 1) + 1
        cols.insert(i, c)
    def rename(t, old, new):
        for c in T(t)["columns"]:
            if c["name"] == old:
                c["name"] = new
                # The role follows the name (R48 §2.1): a rename that changes what a column is
                # must change its role, and one that does not is a no-op here.
                c["role"] = role_of(new)
                if SINCE[0]: c["since"] = SINCE[0]
    def amend(t, name, **changes):
        """Change a column in place, recording the revision that did it (R29 §2).

        In-place amendments are most of what a revision does to a 02 column -- a type, a
        vocabulary, a description -- and they do not go through `col`, so without this they
        would carry no provenance at all. R8 §2 making `local_unit_label` a string is the
        example R29 opens with.
        """
        for c in T(t)["columns"]:
            if c["name"] == name:
                c.update(changes)
                if SINCE[0]: c["since"] = SINCE[0]
                return
        raise SystemExit(f"{t} has no column {name} to amend")

    # ---- R3 §3.0 : tables do not restate what the array declares -----------------------
    SINCE[0] = "R3 §3.0"
    for c in ("dtype", "shape"):
        drop_col("core.array_assets", c)

    # ---- R3 §3.1-3.3 : repeated values become child tables ------------------------------
    SINCE[0] = "R3 §3.1-3.3"
    tables["core.session_experimenters"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("experimenter", "string", "required", "One experimenter.")],
        "primary_key": ["session_id", "experimenter"],
        "references": [{"columns": ["session_id"], "resource": "core.sessions",
                        "resource_columns": ["session_id"]}], "rules": [], "since": SINCE[0]}
    tables["core.trial_tags"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("trial_id", "string", "required", "Trial ID."),
                    col("tag", "string", "required", "Tag value.")],
        "primary_key": ["session_id", "trial_id", "tag"],
        "references": [{"columns": ["session_id", "trial_id"], "resource": "core.trials",
                        "resource_columns": ["session_id", "trial_id"]}], "rules": [], "since": SINCE[0]}
    tables["core.array_dimensions"] = {
        "columns": [col("array_asset_id", "string", "required", "Array asset ID."),
                    col("axis_index", "int64", "required",
                        "0-based axis position in stored order (R3 §5)."),
                    col("dimension_name", "string", "required", "Axis name.")],
        "primary_key": ["array_asset_id", "axis_index"],
        "references": [{"columns": ["array_asset_id"], "resource": "core.array_assets",
                        "resource_columns": ["array_asset_id"]}], "rules": [], "since": SINCE[0]}

    # ---- R3 §3.4 : typed clock transform ------------------------------------------------
    SINCE[0] = "R3 §3.4"
    add_col("core.clocks", col("transform_slope", "float64", "nullable",
            "Parent ticks per this clock's tick, as measured."), after="parent_clock_id")
    add_col("core.clocks", col("transform_offset", "float64", "nullable",
            "Parent-clock tick at this clock's tick 0."), after="transform_slope")

    # ---- R6 §2 : wall-clock binding -------------------------------------------------------
    SINCE[0] = "R6 §2"
    add_col("core.clocks", col("tick_zero_utc", "timestamp", "nullable",
            "Wall-clock instant of tick 0 on this clock."), after="origin")

    # ---- R3 §6.1 : bind array_channels to an axis ---------------------------------------
    SINCE[0] = "R3 §6.1"
    add_col("core.array_channels", col("axis_index", "int64", "required",
            "Axis that channel_index indexes, in stored order."), after="array_asset_id")
    T("core.array_channels")["references"].append(
        {"columns": ["array_asset_id", "axis_index"], "resource": "core.array_dimensions",
         "resource_columns": ["array_asset_id", "axis_index"]})

    # ---- R5 : flat spikes ----------------------------------------------------------------
    SINCE[0] = "R5"
    del tables["core.unit_spike_chunks"]                                        # §3
    drop_col("core.spike_events", "trial_id")                                   # §2.1
    T("core.spike_events")["primary_key"] = [                                   # §2
        "session_id", "unit_id", "sorting_run_id", "curation_id", "t_tick"]
    T("core.spike_events")["references"] = [
        {"columns": ["session_id"], "resource": "core.sessions",
         "resource_columns": ["session_id"]},
        {"columns": ["clock_id"], "resource": "core.clocks",
         "resource_columns": ["clock_id"]},
        {"columns": ["session_id", "unit_id", "sorting_run_id", "curation_id"],
         "resource": "core.units",
         "resource_columns": ["session_id", "unit_id", "sorting_run_id", "curation_id"]}]
    prev = "firing_rate_hz"                                                        # §4
    for n, d in [("n_spikes", "Total spikes for this unit in this context."),
                 ("first_spike_tick", "Lowest t_tick for this unit."),
                 ("last_spike_tick", "Highest t_tick for this unit.")]:
        add_col("core.units", col(n, "int64", "nullable", d), after=prev)
        prev = n
    for t, old in [("core.electrodes", "local_electrode_index"),                   # §5
                   ("core.electrodes", "local_channel_index"),
                   ("core.units", "local_unit_index")]:
        rename(t, old, old.replace("_index", "_label"))

    # ---- R8 §2 : source labels are strings ------------------------------------------------
    SINCE[0] = "R8 §2"
    for t, n in [("core.electrodes", "local_electrode_label"),
                 ("core.electrodes", "local_channel_label"),
                 ("core.units", "local_unit_label")]:
        amend(t, n, type="string",
              description="Opaque source label; undefined base, not an offset.")

    # ---- R8 §3-4 : vocabularies -----------------------------------------------------------
    SINCE[0] = "R8 §3-4"
    amend("core.processing_runs", "status", enum=["succeeded", "failed", "partial"])
    for t, n in [("core.array_assets", "kind"), ("core.array_assets", "semantic_type"),
                 ("core.media_assets", "semantic_type"),
                 ("core.processing_runs", "activity_type")]:
        amend(t, n, vocabulary="open")

    # ---- R11 §6 : trial_id conflates authored fact with derived join ------------------------
    SINCE[0] = "R11 §6"
    drop_col("core.events", "trial_id")
    T("core.events")["references"] = [r for r in T("core.events")["references"]
                                      if "trial_id" not in r["columns"]]

    # ---- R11 §2 : amplitude units live on the sorting run -----------------------------------
    SINCE[0] = "R11 §2"
    add_col("core.sorting_runs", col("amplitude_unit", "string", "nullable",
            "Unit of core.spike_events.amplitude for this run, e.g. uV, adc."),
            after="sorter_version")
    amend("core.sorting_runs", "amplitude_unit", vocabulary="open")

    # ---- R11 §3-4 : declared-open vocabularies ------------------------------------------------
    SINCE[0] = "R11 §3-4"
    amend("core.units", "quality_label", enum=["sua", "mua", "noise"])          # R11 §3
    amend("core.events", "event_type", vocabulary="open",
          reserved_values=["stimulus_onset", "reward", "lick",
                           "threshold_crossing", "ttl_edge", "sync_pulse"])

    # ---- R9 : provenance simplification ----------------------------------------------------
    SINCE[0] = "R9"
    for n in ("core.provenance_entities", "core.provenance_activities",
              "core.provenance_edges"):
        del tables[n]
    tables["core.processing_run_inputs"] = {
        "columns": [col("processing_run_id", "string", "required", "The run."),
                    col("source_file_id", "string", "required",
                        "A source file the run consumed.")],
        "primary_key": ["processing_run_id", "source_file_id"],
        "references": [{"columns": ["processing_run_id"], "resource": "core.processing_runs",
                        "resource_columns": ["processing_run_id"]},
                       {"columns": ["source_file_id"], "resource": "core.source_files",
                        "resource_columns": ["source_file_id"]}], "rules": [], "since": SINCE[0]}

    # R10 §2's ordering rule is R92 §2.2's, and R93 §3.3 removed the `sort` field it was
    # declared through: a table's stored order is its primary key's unless `03` §5.4 names
    # another, and that list is `escapewheel_reader`'s rather than the registry's.

    # ---- R18 §2 : units drift in and out of a recording -----------------------------------------
    SINCE[0] = "R18 §2"
    tables["core.unit_observation_intervals"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("unit_id", "string", "required", "Unit ID."),
                    col("sorting_run_id", "string", "required", "Sorting run ID."),
                    col("curation_id", "string", "required", "Curation ID."),
                    col("start_tick", "int64", "required", "First tick, inclusive."),
                    col("stop_tick", "int64", "required", "Last tick, inclusive."),
                    col("clock_id", "string", "required", "Clock for the interval bounds.")],
        # R47 §2.2: `start_tick` keys it. Two rows of one partition cannot share a start while
        # interval_valid and non_overlapping hold, so uniqueness is by construction.
        "primary_key": ["session_id", "unit_id", "sorting_run_id", "curation_id", "start_tick"],
        "references": [{"columns": ["session_id", "unit_id", "sorting_run_id", "curation_id"],
                        "resource": "core.units",
                        "resource_columns": ["session_id", "unit_id", "sorting_run_id",
                                             "curation_id"]},
                       {"columns": ["clock_id"], "resource": "core.clocks",
                        "resource_columns": ["clock_id"]}],
        "rules": [], "since": SINCE[0]}

    # ---- R19 §2 : scaling and sample timing are per channel --------------------------------------
    SINCE[0] = "R19 §2"
    for name, typ, desc in [
            ("conversion", "float64", "Multiply stored values by this before offset."),
            ("offset", "float64", "Add after conversion."),
            ("unit", "string", "Physical unit of the converted value."),
            ("inter_sample_shift", "float64",
             "Acquisition time offset within one sample period, in sample periods.")]:
        entry = col(name, typ, "nullable", desc)
        if name == "offset":
            # R56 §2.1: an offset is in the converted value's unit, which this table carries
            # per channel. `conversion` is not: it is a ratio of two units, not either one.
            entry["unit_from"] = "unit"
        add_col("core.array_channels", entry, after="channel_label")

    # ---- R19 §3 : an electrode sits in more than one coordinate frame ----------------------------
    SINCE[0] = "R19 §3"
    for c in ("x_um", "y_um", "z_um", "coordinate_frame"):
        drop_col("core.electrodes", c)
    tables["core.electrode_coordinates"] = {
        "columns": [col("electrode_id", "string", "required", "Electrode ID."),
                    dict(col("coordinate_frame", "string", "required",
                             "The frame these coordinates are in."), vocabulary="open"),
                    dict(col("coordinate_basis", "string", "required",
                             "What the coordinate asserts: `planned` where the probe was meant to "
                             "go, `measured` where it was, `nominal` where it is by construction "
                             "and nothing aimed or observed it (R64 §2.1). A consumer that does "
                             "not recognise a basis MUST NOT treat it as measured (R58 §2.2).",
                             since="R58 §2.1"), vocabulary="open"),
                    col("region_id", "int32", "nullable",
                        "The atlas structure this position falls in, numbered by the atlas that "
                        "`coordinate_frame` names.", since="R59 §2.1"),
                    dict(col("region_label", "string", "nullable",
                             "That structure's short name, so a consumer without the atlas can "
                             "read the annotation.", since="R59 §2.1"), vocabulary="open"),
                    col("processing_run_id", "int32", "nullable",
                        "The run that produced this coordinate.", since="R58 §2.3"),
                    col("x_um", "float64", "nullable", "X in micrometres, in that frame."),
                    col("y_um", "float64", "nullable", "Y in micrometres."),
                    col("z_um", "float64", "nullable", "Z in micrometres.")],
        "primary_key": ["electrode_id", "coordinate_frame", "coordinate_basis"],
        "references": [{"columns": ["electrode_id"], "resource": "core.electrodes",
                        "resource_columns": ["electrode_id"]},
                       {"columns": ["processing_run_id"], "resource": "core.processing_runs",
                        "resource_columns": ["processing_run_id"]}],
        "rules": [], "since": SINCE[0]}

    # ---- R59 §2.1 : the atlas annotation belongs to the position, not the electrode ------------
    SINCE[0] = "R59 §2.1"
    drop_col("core.electrodes", "brain_region")

    # ---- R20 §2 : four coordinate forms per axis -------------------------------------------------
    SINCE[0] = "R20 §2"
    for name, typ, desc in [
            ("clock_id", "string", "Clock the ticks are counted on (regular tick axis)."),
            ("origin_tick", "int64", "Tick at position 0."),
            ("step_tick_num", "int64", "Ticks advanced per position (numerator)."),
            ("origin_value", "float64", "Value at position 0 (regular numeric axis)."),
            ("step_value", "float64", "Increment per position."),
            ("coordinate_unit", "string", "Unit of the numeric coordinate values."),
            ("coordinate_array_asset_id", "string",
             "A 1-D array holding one value per position (irregular axis)."),
            ("coordinate_resource", "string",
             "Resource whose rows are this axis's positions (labelled axis)."),
            ("coordinate_position_column", "string",
             "Which column of that resource holds the 0-based position.")]:
        entry = col(name, typ, "nullable", desc)
        if name in ("origin_value", "step_value"):
            # R56 §2.1: both are in the axis's own unit, which this table carries per axis.
            entry["unit_from"] = "coordinate_unit"
        add_col("core.array_dimensions", entry, after="dimension_name")
    T("core.array_dimensions")["references"].append(
        {"columns": ["clock_id"], "resource": "core.clocks", "resource_columns": ["clock_id"]})

    # ---- R33 §2 : an axis step may be rational -----------------------------------------------
    # `step_tick_num` is the numerator. Absent denominator means 1, so every row written
    # under R20 keeps its meaning. A 30 ms PSTH bin is 937.5 ticks at 31,250 Hz and 29.97 fps
    # is 1042.708..., neither of which an integer step can say.
    SINCE[0] = "R33 §2"
    add_col("core.array_dimensions",
            col("step_tick_den", "int64", "nullable",
                "Denominator of the step, in ticks. Absent means 1."),
            after="step_tick_num")

    # ---- R38 §2 : observation belongs to the clock ----------------------------------------------
    # A unit was observable while its probe was running; a sensor was watched while its
    # acquisition was. Written per unit that is one window copied once per unit -- 6,781 on a
    # session of this size -- and per stream another copy. The window is a property of the
    # device, so it lives on the clock, and the ticks need no clock column because the key is
    # the clock. That is what keeps every containment check a same-clock comparison, which is
    # the conversion R25 §4 could not write.
    SINCE[0] = "R38 §2.1"
    tables["core.clock_observation_intervals"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("clock_id", "string", "required", "The clock that was observing."),
                    col("start_tick", "int64", "required",
                        "First tick observed, on `clock_id` itself."),
                    col("stop_tick", "int64", "required",
                        "Last tick observed, on `clock_id` itself.")],
        "primary_key": ["session_id", "clock_id", "start_tick"],  # R47 §2.2
        "references": [{"columns": ["session_id"], "resource": "core.sessions",
                        "resource_columns": ["session_id"]},
                       {"columns": ["clock_id"], "resource": "core.clocks",
                        "resource_columns": ["clock_id"]}],
        "rules": [], "since": SINCE[0]}

    # A unit finds its clock through its sorting run. Without this the only route is the string
    # convention `{sorting_run_id}.samples`, which the adapters agree on and no rule can see.
    SINCE[0] = "R38 §2.2"
    add_col("core.sorting_runs",
            col("clock_id", "string", "required",
                "Clock the run's spike ticks are counted on."),
            after="probe_id")
    T("core.sorting_runs").setdefault("references", []).append(
        {"columns": ["clock_id"], "resource": "core.clocks", "resource_columns": ["clock_id"]})

    # ---- R39 §2.2 : the session's time origin ---------------------------------------------------
    # The earliest observation start, on the reference clock. Declared rather than recomputed by
    # every reader: it survives amendment unchanged, and a reader need not know which resources
    # carry windows. Optional, because a packet declaring no observation declares no origin.
    SINCE[0] = "R39 §2.2"
    add_col("core.sessions",
            col("t_zero_tick", "int64", "nullable",
                "Earliest observed tick, on `reference_clock_id`; the origin seconds count from."),
            after="session_end_time")

    # ---- R16 §2-3 : unit quality is many labels, attributed ------------------------------------
    SINCE[0] = "R16 §2-3"
    tables["core.unit_quality_labels"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("unit_id", "string", "required", "Unit ID."),
                    col("sorting_run_id", "string", "required", "Sorting run ID."),
                    col("curation_id", "string", "required", "Curation ID."),
                    dict(col("source", "string", "required",
                             "What produced the label, e.g. kilosort, decoder, bombcell."),
                         vocabulary="open"),
                    dict(col("label", "string", "required",
                             "The source's own label, verbatim."),
                         vocabulary="open"),
                    dict(col("normalized_label", "string", "nullable",
                             "Declared projection onto the closed set. Null where the "
                             "source's label does not project."),
                         enum=["sua", "mua", "noise"]),
                    col("confidence", "float64", "nullable",
                        "The source's confidence, where it reports one.")],
        "primary_key": ["session_id", "unit_id", "sorting_run_id", "curation_id", "source"],
        "references": [{"columns": ["session_id", "unit_id", "sorting_run_id", "curation_id"],
                        "resource": "core.units",
                        "resource_columns": ["session_id", "unit_id", "sorting_run_id",
                                             "curation_id"]}],
        "rules": [], "since": SINCE[0]}
    add_col("core.units", dict(col("quality_label_source", "string", "nullable",
            "Which core.unit_quality_labels source the designated label came from."),
            vocabulary="open"), after="quality_label")

    # ---- R23 §2-3 : events get the context table every other core stream has -----------------
    SINCE[0] = "R23 §2-3"
    tables["core.event_streams"] = {
        "columns": [col("event_stream_id", "string", "required", "Stable ID."),
                    col("session_id", "string", "required", "Session ID."),
                    col("name", "string", "required",
                        "Human-readable name, e.g. left_lick_sensor."),
                    col("device_id", "string", "nullable",
                        "The device that produced it, where one is identified."),
                    col("clock_id", "string", "required",
                        "The clock its events are timed on."),
                    col("processing_run_id", "string", "nullable",
                        "The run that produced it. Null means it came off the device as "
                        "recorded. A narrow exception to R9 §4: the manifest records "
                        "outputs per resource and cannot distinguish streams within one "
                        "table.")],
        "primary_key": ["event_stream_id"],
        "references": [{"columns": ["session_id"], "resource": "core.sessions",
                        "resource_columns": ["session_id"]},
                       {"columns": ["device_id"], "resource": "core.devices",
                        "resource_columns": ["device_id"]},
                       {"columns": ["clock_id"], "resource": "core.clocks",
                        "resource_columns": ["clock_id"]},
                       {"columns": ["processing_run_id"], "resource": "core.processing_runs",
                        "resource_columns": ["processing_run_id"]}],
        "rules": [], "since": SINCE[0]}
    add_col("core.events", col("stream_id", "string", "required",
                               "The stream this event belongs to."), after="event_id")
    T("core.events")["references"].append(
        {"columns": ["stream_id"], "resource": "core.event_streams",
         "resource_columns": ["event_stream_id"]})

    # ---- R25 §2 : streams drop out too; absence of an event is ambiguous without this -------
    SINCE[0] = "R25 §2"
    tables["core.event_stream_observation_intervals"] = {
        "columns": [col("event_stream_id", "string", "required", "The stream being observed."),
                    col("start_tick", "int64", "required",
                        "First observed tick, on the stream's clock."),
                    col("stop_tick", "int64", "required",
                        "Last observed tick, on the stream's clock.")],
        "primary_key": ["event_stream_id", "start_tick"],  # R47 §2.2
        # No clock_id: core.event_streams declares one, and an interval is meaningless without
        # joining to its stream anyway, so repeating it buys nothing (R25 2.1).
        "references": [{"columns": ["event_stream_id"], "resource": "core.event_streams",
                        "resource_columns": ["event_stream_id"]}],
        "rules": [], "since": SINCE[0]}
    add_col("core.sessions", col("session_end_time", "timestamp", "nullable",
            "When the session ended, UTC. Metadata, not derived from the tables (R25 5)."),
            after="session_start_time")

    # ---- R27 §2 : "synchronized" has to name a clock ------------------------------------------
    SINCE[0] = "R27 §2"
    # A reader's default is to return times on one clock. A session with two unparented clocks
    # has two roots and nothing chooses between them, so the session says which.
    add_col("core.sessions", col("reference_clock_id", "string", "nullable",
            "The clock this session's times are reported on by default (R27 2)."),
            after="session_end_time")
    T("core.sessions")["references"].append(
        {"columns": ["reference_clock_id"], "resource": "core.clocks",
         "resource_columns": ["clock_id"]})

    # ---- R13 §3 : anchor-point clock alignment ------------------------------------------------
    SINCE[0] = "R13 §3"
    tables["core.clock_anchors"] = {
        "columns": [col("clock_id", "string", "required", "The clock being aligned."),
                    col("anchor_index", "int64", "required",
                        "0-based position in this clock's anchor sequence."),
                    col("t_tick", "int64", "required", "Tick on clock_id."),
                    col("parent_tick", "int64", "required",
                        "The corresponding tick on parent_clock_id.")],
        "primary_key": ["clock_id", "anchor_index"],
        "references": [{"columns": ["clock_id"], "resource": "core.clocks",
                        "resource_columns": ["clock_id"]}],
        "rules": [], "since": SINCE[0]}

    # ---- R28 §2-4 : a unit sits on many electrodes, and somewhere -----------------------------
    SINCE[0] = "R28 §2-4"
    # `default_electrode_id` is the peak channel and not the set, and nothing said where a unit
    # is. NWB relates the two through three index spaces in one row; naming the electrode is
    # the alternative R3 §2.1's physical floor already implies.
    unit_key = ["session_id", "unit_id", "sorting_run_id", "curation_id"]
    unit_ref = {"columns": unit_key, "resource": "core.units", "resource_columns": unit_key}
    tables["core.unit_electrodes"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("unit_id", "string", "required", "Unit ID."),
                    col("sorting_run_id", "string", "required", "Sorting run ID."),
                    col("curation_id", "string", "required", "Curation ID."),
                    col("electrode_id", "string", "required",
                        "An electrode this unit was detected on."),
                    col("channel_index", "int64", "nullable",
                        "0-based position in the unit's channel list, where a dense array axis "
                        "is indexed by it (R20 §2). Not an identifier; nothing joins on it."),
                    col("is_primary", "bool", "nullable",
                        "Whether this is the unit's peak electrode.")],
        "primary_key": [*unit_key, "electrode_id"],
        "references": [unit_ref,
                       {"columns": ["electrode_id"], "resource": "core.electrodes",
                        "resource_columns": ["electrode_id"]}],
        "rules": [], "since": SINCE[0]}
    tables["core.unit_coordinates"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("unit_id", "string", "required", "Unit ID."),
                    col("sorting_run_id", "string", "required", "Sorting run ID."),
                    col("curation_id", "string", "required", "Curation ID."),
                    col("coordinate_frame", "string", "required",
                        "The frame these coordinates are in. Open, as R19 §3 left it."),
                    dict(col("coordinate_basis", "string", "required",
                             "What the coordinate asserts: `planned` where the probe was meant to "
                             "go, `measured` where it was, `nominal` where it is by construction "
                             "and nothing aimed or observed it (R64 §2.1). A consumer that does "
                             "not recognise a basis MUST NOT treat it as measured (R58 §2.2).",
                             since="R58 §2.1"), vocabulary="open"),
                    col("region_id", "int32", "nullable",
                        "The atlas structure this position falls in, numbered by the atlas that "
                        "`coordinate_frame` names.", since="R59 §2.1"),
                    dict(col("region_label", "string", "nullable",
                             "That structure's short name, so a consumer without the atlas can "
                             "read the annotation.", since="R59 §2.1"), vocabulary="open"),
                    col("processing_run_id", "int32", "nullable",
                        "The run that produced this coordinate.", since="R58 §2.3"),
                    col("x_um", "float64", "nullable", "X in micrometres, in that frame."),
                    col("y_um", "float64", "nullable", "Y in micrometres."),
                    col("z_um", "float64", "nullable", "Z in micrometres.")],
        "primary_key": [*unit_key, "coordinate_frame", "coordinate_basis"],
        "references": [unit_ref,
                       {"columns": ["processing_run_id"], "resource": "core.processing_runs",
                        "resource_columns": ["processing_run_id"]}],
        "rules": [], "since": SINCE[0]}
    # The one link between a dense array's channels and the electrodes they came from, which
    # until now nothing validated.
    T("core.array_channels")["references"].append(
        {"columns": ["electrode_id"], "resource": "core.electrodes",
         "resource_columns": ["electrode_id"]})

    # ---- R66 §2.1 : a device declares what version it was -----------------------------------------
    # A serial number identifies the object; its firmware determines what the object does. Strings
    # rather than numbers, and unordered: `3.0196`, `2.1` and `UNKNOWN` are all real values from one
    # session, and two manufacturers' schemes share no precedence a consumer could rely on.
    SINCE[0] = "R66 §2.1"
    for name, description in (
        ("hardware_version", "The instrument's hardware revision, verbatim as its source stated it."),
        ("firmware_version", "The firmware the instrument was running, verbatim as its source stated it."),
    ):
        add_col("core.devices", col(name, "string", "nullable", description), after="model")

    # ---- R65 §2.1 : an array names the instrument that made it -----------------------------------
    # core.probes has named its device since 02; an array asset was the only acquired thing in core
    # that could not. Nullable, because a derived array has no instrument and a referenced one may
    # come from a producer the packet cannot attribute. Placed before the R20 §5 mirror, so the
    # analysis copy gains it too -- its reference stays pointing at core.devices, which is right:
    # there is no analysis.devices and R17 §2 lets a layer reference core's tables.
    SINCE[0] = "R65 §2.1"
    add_col("core.array_assets",
            col("device_id", "int32", "nullable", "The device that produced this array."),
            after="clock_id")
    T("core.array_assets")["references"].append(
        {"columns": ["device_id"], "resource": "core.devices", "resource_columns": ["device_id"]})

    # ---- R67 §2.1 : a device names what it was attached to ---------------------------------------
    # R66 made each element of an acquisition chain a device and left them unable to say they
    # were connected. Self-referencing (R46 §2), nullable because a chain has a root and because
    # a source that does not state the attachment must not be made to invent one.
    SINCE[0] = "R67 §2.1"
    add_col("core.devices",
            col("parent_device_id", "int32", "nullable",
                "The device this one was attached to -- a probe's headstage, a headstage's "
                "connect board. Null at the root of a chain, or where no source states it."),
            after="serial_number")
    T("core.devices")["references"].append(
        {"columns": ["parent_device_id"], "resource": "core.devices", "resource_columns": ["device_id"]})

    # ---- R70 §2.1 : an asset declares the rate its timestamps count at ---------------------------
    # R68 §2.4 left the time base to the container, which is reachable only while the referenced
    # file is -- the one thing R14 §2.3 does not promise. Rational and expressed as a rate, in the
    # shape core.clocks.tick_rate_num already uses, so a consumer needs no second convention.
    SINCE[0] = "R70 §2.1"
    # Reversed, because each inserts directly after `format` and the numerator reads first.
    for name, description in (
        ("pts_rate_den", "Presentation timestamps per second in this asset's container: denominator."),
        ("pts_rate_num", "Presentation timestamps per second in this asset's container: numerator."),
    ):
        add_col("core.media_assets", col(name, "int64", "nullable", description), after="format")

    # ---- R68 §2.1 : a presentation timestamp is an integer ---------------------------------------
    # 02's float64 named two quantities a container offers -- its own integer timestamp and that
    # value in seconds -- and the type argued for the one nothing records. An integer admits only
    # the recorded reading, and it is the only type DELTA_BINARY_PACKED is defined for, which on a
    # frame timeline is 6.3x the best a float can reach.
    SINCE[0] = "R68 §2.1"
    amend("core.media_frames", "pts", type="int64",
          description="Container presentation timestamp, verbatim in the container's own time base.")

    # ---- R20 §5 : analysis arrays are described by analysis tables -------------------------------
    SINCE[0] = "R20 §5"
    import copy
    for core_name in ("core.array_assets", "core.array_dimensions"):
        mirror = copy.deepcopy(T(core_name))
        mirror["references"] = [
            dict(r, resource=r["resource"].replace("core.array_", "analysis.array_"))
            if r["resource"].startswith("core.array_") else r
            for r in mirror["references"]]
        mirror["rules"] = []
        # The mirror and its columns exist in this namespace because of R20 §5, whatever put
        # them in core. Carrying the original's provenance would send a reader to a revision
        # that says nothing about the analysis layer.
        mirror["since"] = SINCE[0]
        for column in mirror["columns"]:
            column["since"] = SINCE[0]
        tables[core_name.replace("core.", "analysis.")] = mirror

    # ---- 06 : spikes on the reference clock -------------------------------------------------
    # The columns 06 defined carry no `since`, which under R29 §2 means exactly that. Only
    # time_bucket_tick is new, and only the order is overridden -- R30 §3.2 replaces 03's
    # recommendation for this table alone, because a common clock is what makes ordering by
    # time meaningful and core does not have one.
    SINCE[0] = None
    tables["analysis.spike_events"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("unit_id", "string", "required", "Unit ID."),
                    col("sorting_run_id", "string", "required", "Sorting run ID."),
                    col("curation_id", "string", "required", "Curation ID."),
                    col("t_tick", "int64", "required",
                        "Spike tick on clock_id, mapped through core.clock_anchors."),
                    col("clock_id", "string", "required",
                        "The clock these ticks are on, normally the session's reference.",
                        determined_by=["session_id"]),
                    col("time_bucket_tick", "int64", "required",
                        "First tick of the bucket this spike falls in, on clock_id.",
                        since="R30 §3.1", determined_by=["t_tick"])],
        "primary_key": ["session_id", "unit_id", "sorting_run_id", "curation_id", "t_tick"],
        "references": [{"columns": ["session_id", "unit_id", "sorting_run_id", "curation_id"],
                        "resource": "core.units",
                        "resource_columns": ["session_id", "unit_id", "sorting_run_id",
                                             "curation_id"]},
                       {"columns": ["clock_id"], "resource": "core.clocks",
                        "resource_columns": ["clock_id"]}],
        "rules": []}

    # ---- R7 : every table declares a key ---------------------------------------------------
    SINCE[0] = "R7"
    for n, k in [("core.media_assets", ["media_asset_id"]),
                 ("core.processing_runs", ["processing_run_id"]),
                 ("core.source_files", ["source_file_id"])]:
        T(n)["primary_key"] = k

    # ---- R41 : which derived thing is current ----------------------------------------------
    # A project re-sorts, re-curates and runs new models over the same video, and the format
    # already lets the alternatives coexist. What it could not say is which to use. R32 gives
    # snapshots and `parent_curation_id` gives lineage for curation alone; a snapshot cannot
    # express currency, because all three sortings are inside it.
    #
    # Keyed on the producing run rather than on any core table, so an R17 extension's outputs
    # are reachable without the core registry knowing its tables. That needs the graph wired
    # up first: only `core.event_streams` referenced `core.processing_runs` (R23).
    SINCE[0] = "R41 §2.1"
    for name, after in (("core.sorting_runs", "sorter_version"),
                        ("core.curation_versions", "curation_tool_version")):
        add_col(name, col("processing_run_id", "string", "nullable",
                          "The run that produced this record, where provenance is recorded."),
                after=after)
        T(name).setdefault("references", []).append(
            {"columns": ["processing_run_id"], "resource": "core.processing_runs",
             "resource_columns": ["processing_run_id"]})

    # Lineage, generalising `parent_curation_id` to every activity. A claim about intent, not
    # about correctness: the superseded run keeps its rows, which is the point of keeping both.
    SINCE[0] = "R41 §2.2"
    add_col("core.processing_runs",
            col("supersedes_run_id", "string", "nullable", "The run this one replaces, if any."),
            after="activity_type")
    T("core.processing_runs").setdefault("references", []).append(
        {"columns": ["supersedes_run_id"], "resource": "core.processing_runs",
         "resource_columns": ["processing_run_id"]})

    # The choice itself. Separate from the run log because that log should never be revised
    # while a preference changes whenever someone changes their mind -- objects and refs.
    SINCE[0] = "R41 §2.3"
    tables["core.preferred_runs"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("activity_type", "string", "required",
                        "Which kind of output this preference is about. Open, as R9 §6 leaves it."),
                    col("scope_kind", "string", "required", "The resource whose primary key "
                        "`scope` holds, as a dotted resource ID (R49 §2.2). Open.", since="R49 §2.1"),
                    col("scope", "string", "required",
                        "What it applies to -- a probe_id, an array_asset_id, a camera -- or the "
                        "session_id itself where the preference is session-wide."),
                    col("processing_run_id", "string", "required", "The preferred run."),
                    col("chosen_at", "timestamp", "nullable", "When the choice was made."),
                    col("reason", "string", "nullable", "Why, in one line.")],
        # `scope` is required rather than nullable because R7 wants a real key, and a nullable
        # key column makes uniqueness ill-defined.
        # R49 §2.3: the pair is the address. Without the kind, a probe and a device sharing an
        # identifier would collide on one preference row.
        "primary_key": ["session_id", "activity_type", "scope_kind", "scope"],
        "references": [{"columns": ["session_id"], "resource": "core.sessions",
                        "resource_columns": ["session_id"]},
                       {"columns": ["processing_run_id"], "resource": "core.processing_runs",
                        "resource_columns": ["processing_run_id"]}],
        "rules": [], "since": SINCE[0]}

    # What the run is about, so `core.preferred_runs` has something to join to. Without it the
    # ambiguity rule groups by activity while the preference is keyed by activity and scope, and
    # twelve probes sorted once each are indistinguishable from one probe sorted twelve times.
    # Nullable because provenance is SHOULD (R9 §5); a run that omits it is undeterminable
    # rather than unique.
    SINCE[0] = "R44 §2.1"
    add_col("core.processing_runs",
            col("scope", "string", "nullable",
                "What this run is about -- a probe_id, an array_asset_id, a camera -- or the "
                "session_id itself where the run is session-wide. Open, as activity_type is."),
            after="activity_type")

    # `02` described these only as "Trial start tick" / "Trial stop tick", so a consumer
    # counting events in a trial had to choose `<` or `<=` and the packet did not say which.
    # No overlap rule is added: R25 §7's reasoning stands, since trials need not partition a
    # session and in some paradigms may nest by design.
    SINCE[0] = "R45 §2.4"
    amend("core.trials", "start_tick", description="First tick of the trial, inclusive, on `clock_id`.")
    amend("core.trials", "stop_tick", description="Last tick of the trial, inclusive, on `clock_id`.")

    # R49 §2.1-2.2: the kind is a dotted resource ID, so a consumer resolves generically --
    # read the kind, take that resource's primary key from the registry, resolve. That is what
    # lets an R17 extension scope to its own tables without the core registry knowing them.
    SINCE[0] = "R49 §2.1"
    add_col("core.processing_runs",
            col("scope_kind", "string", "nullable",
                "The resource whose primary key `scope` holds, as a dotted resource ID -- "
                "`core.probes`, `core.array_assets`. Open (R8 §4); a value naming no declared "
                "resource means the scope is not a packet resource. Set with `scope` or not at all."),
            after="scope")

    # ---- R50 : three columns are renamed -----------------------------------------------------
    # channel_ordinal -> channel_index: R28 chose `ordinal` to say "not an identifier"; R48's role
    # says that for every such column, leaving a name that claims a position where the value is a
    # 0-based offset. supersedes -> supersedes_run_id: the only reference column not following the
    # `_id` convention. step_ticks -> step_tick_num: agrees with step_tick_den and tick_rate_num,
    # and cannot be misread as a coordinate the way a `_ticks` plural can.
    SINCE[0] = "R50 §2"
    amend("core.unit_electrodes", "channel_index",
          description="0-based position of this electrode in the unit's channel list, where a "
                      "dense array axis is indexed by it (R20 §2). Nothing joins on it.")
    amend("core.processing_runs", "supersedes_run_id",
          description="The run this one replaces, if any.")

    # ---- R46 : the references the registry never declared -----------------------------------
    # Tier 1 generates an anti-join per declared reference, so an undeclared one is a check that
    # never runs: a packet naming a probe that is not in core.probes validated clean. The reader
    # degrades too -- `distinct` answers from the parent table only where a reference says it may.
    # `array_asset_id` keys both core and analysis assets; the layering settles it, since a core
    # table must not reference an analysis resource (06).
    SINCE[0] = "R46 §2.1"
    for child, column, parent, parent_column in [
            ("core.sorting_runs", "session_id", "core.sessions", "session_id"),
            ("core.sorting_runs", "probe_id", "core.probes", "probe_id"),
            ("core.sorting_runs", "input_array_asset_id", "core.array_assets", "array_asset_id"),
            ("core.curation_versions", "session_id", "core.sessions", "session_id"),
            ("core.curation_versions", "sorting_run_id", "core.sorting_runs", "sorting_run_id"),
            ("core.curation_versions", "parent_curation_id", "core.curation_versions", "curation_id"),
            ("core.processing_runs", "session_id", "core.sessions", "session_id"),
            ("core.devices", "session_id", "core.sessions", "session_id"),
            ("core.array_assets", "session_id", "core.sessions", "session_id"),
            ("core.array_assets", "clock_id", "core.clocks", "clock_id"),
            ("core.array_dimensions", "coordinate_array_asset_id", "core.array_assets", "array_asset_id"),
            ("core.media_assets", "session_id", "core.sessions", "session_id"),
            ("core.media_assets", "clock_id", "core.clocks", "clock_id"),
            ("core.media_frames", "clock_id", "core.clocks", "clock_id"),
            # Missed by R46's own sweep: a frame names the asset it belongs to and nothing checked
            # that the asset exists. Found by R53's ownership derivation, which reported this table
            # as *owning* media_asset_id -- which only a dimension table should.
            ("core.media_frames", "media_asset_id", "core.media_assets", "media_asset_id"),
            ("analysis.array_assets", "session_id", "core.sessions", "session_id"),
            ("analysis.array_assets", "clock_id", "core.clocks", "clock_id"),
            # Transitively implied by the composite reference into core.units, so the anti-join
            # will never fire -- but R56 §2.3 resolves a unit through a reference the table
            # *declares*, and core.spike_events.amplitude is in the unit its sorting run names
            # (R11 §2). Declaring it is what makes that hop available.
            ("core.spike_events", "sorting_run_id", "core.sorting_runs", "sorting_run_id")]:
        T(child).setdefault("references", []).append(
            {"columns": [column], "resource": parent, "resource_columns": [parent_column]})

    # ---- R53 §2.3.1 : an assigned identifier's owner carries its name --------------------
    SINCE[0] = "R53 §2.3.1"
    for resource, spec in tables.items():
        exported = {c for ref in spec.get("references", []) for c in ref["columns"]}
        for column in list(spec["columns"]):
            if column.get("identity") != "assigned" or column["name"] in exported:
                continue
            if column["name"] not in (spec.get("primary_key") or []):
                continue
            base = column["name"].removesuffix("_id")
            # `data`, not `identifier`: within this packet it identifies nothing -- the int32
            # does -- and nothing references it. R48 §2.1's role is about what a consumer may do
            # with the column here, and what it may do with a name is read it.
            ROLES[f"{base}_name"] = "data"
            entry = col(f"{base}_name", "string", "nullable",
                        f"What `{column['name']}` stands for: the identifier a source or an earlier "
                        f"packet used for this {base.replace('_', ' ')}. The only bridge between two "
                        "packets that numbered it differently (R53 §2.5).")
            spec["columns"].insert(spec["columns"].index(column) + 1, entry)

    # ---- R56 : a column declares its unit and its clock ---------------------------------
    SINCE[0] = "R56 §2"
    for (resource, column_name), context in CONTEXT.items():
        column = next((c for c in tables[resource]["columns"] if c["name"] == column_name), None)
        if column is None:
            raise SystemExit(f"R56 declares context for {resource}.{column_name}, which does not exist")
        column.update(context)

    # ---- R54 §2 : a trial is one kind of interval ---------------------------------------------
    # One base table holding many kinds, discriminated by the resource that specialises each. The
    # kind is part of the key (R54 §2.2), so every kind keeps its source's own numbering and
    # trial 0 and block 0 are different rows. R55 §2.3's shared-key shape: a detail table carries
    # the kind as a constant column and references all three, so the join is declared rather than
    # inferred and R46's generated anti-join enforces it.
    SINCE[0] = "R54 §2.1"
    rename("core.trials", "trial_id", "interval_id")
    add_col("core.trials", col("interval_kind", "string", "required",
                               "The resource that specialises this interval, as a dotted resource "
                               "ID. Open (R8 §4); resolved as R55 §2.3's shared key."),
            after="session_id")
    # R54 §2.3: a task's shape is not the format's. `dynamic_foraging.trials` already carries
    # `choice` and `rewarded` with a closed vocabulary core cannot declare -- `none` is not a
    # choice -- and condition_id/stimulus_id were assigned identifiers nothing ever populated.
    for struck in ("condition_id", "stimulus_id", "choice", "rewarded"):
        drop_col("core.trials", struck)
    T("core.trials")["primary_key"] = ["session_id", "interval_kind", "interval_id"]
    # R54 §2.2: the kind is a key column, so it is a sort column too -- each kind is then a
    # contiguous run and filtering to one prunes row groups. `rename` moves columns and not the
    # sort, so a sort naming the old column would survive it and name nothing.
    tables["core.intervals"] = tables.pop("core.trials")
    # R54 §2.3: the one place this format let meaning accrete without a schema, which R17 §3
    # exists to refuse. An extension needing a multi-valued attribute declares a typed child.
    del tables["core.trial_tags"]

    # ---- R81 §2 : the packet numbers its units -----------------------------------------------
    # `unit_id` was carried, so it repeated across runs -- 810 distinct values over 6,781
    # (unit_id, sorting_run_id) pairs -- and identity grew to four columns to compensate. It also
    # duplicated `local_unit_label` exactly, in 6,781 of 6,781 rows, which R3 §3.0 forbids.
    SINCE[0] = "R81 §2"
    one = ["unit_id"]
    T("core.units")["primary_key"] = one
    # R81 §2.7: `core.unit_electrodes.is_primary` already names the peak electrode, and this
    # column is null in every row of every packet because the adapter that knows the extremum
    # does not own this table.
    drop_col("core.units", "default_electrode_id")
    T("core.units")["references"] = [r for r in T("core.units")["references"]
                                     if r["columns"] != ["default_electrode_id"]]
    # R81 §2.3: every table keyed on a unit narrows to the one column, and so does its reference.
    narrowed = {"columns": one, "resource": "core.units", "resource_columns": one}
    for name in ("core.spike_events", "analysis.spike_events", "core.unit_electrodes",
                 "core.unit_coordinates", "core.unit_quality_labels",
                 "core.unit_observation_intervals"):
        table = T(name)
        table["references"] = [narrowed if r["resource"] == "core.units" else r
                               for r in table["references"]]
        table["primary_key"] = [c for c in table["primary_key"]
                                if c not in ("sorting_run_id", "curation_id")]
        for struck in ("sorting_run_id", "curation_id"):
            if any(c["name"] == struck for c in table["columns"]):
                drop_col(name, struck)
        # A reference on a struck column has nothing to join from. `core.units` still names the
        # run and the curation, so the fact is one hop away rather than gone.
        table["references"] = [r for r in table["references"]
                               if not set(r["columns"]) & {"sorting_run_id", "curation_id"}]
    # R81 §2.4: `03` §5.3's override named two columns that no longer exist. Numbering by
    # (run, curation, label) makes ascending unit_id run-major, so the clustering is unchanged
    # and the key, the sort and the uniqueness check finally agree -- R47 §2's outcome.
    T("core.spike_events")["primary_key"] = ["session_id", "unit_id", "t_tick"]
    T("analysis.spike_events")["primary_key"] = ["session_id", "unit_id", "t_tick"]
    # R81 §5: `amplitude` named its unit through `core.sorting_runs.amplitude_unit`, which was one
    # hop while the spike carried `sorting_run_id`. It is now two -- spike to unit to run -- and
    # R56 §2.2 permits one, so the declaration is dropped rather than made to name a hop that
    # cannot be followed. The same shape as the gap R70 §5 left and recorded.
    for column in T("core.spike_events")["columns"]:
        column.pop("unit_from", None)

    # ---- R83 §2 : a sorting run declares the channels it used ---------------------------------
    SINCE[0] = "R83 §2.1"
    # A sorting drops bad channels before it runs, so a channel index a source emits counts what
    # it kept and not the probe's contacts -- `extremum_channel_index` named the wrong electrode
    # for 5,071 of 6,781 units read the other way. The list it counts was in the analyzer and in
    # no file, so nothing in the packet could resolve it.
    tables["core.sorting_run_channels"] = {
        "columns": [col("session_id", "int32", "required", "Session ID."),
                    col("sorting_run_id", "int32", "required",
                        "The run whose channel list this row belongs to."),
                    col("channel_index", "int64", "required",
                        "0-based position in the run's own channel order, which is what a source's "
                        "channel index counts (R83 §1.1). int64 as every structural index is."),
                    col("electrode_id", "int32", "required", "The contact at that position.")],
        "primary_key": ["session_id", "sorting_run_id", "channel_index"],
        "references": [{"columns": ["sorting_run_id"], "resource": "core.sorting_runs",
                        "resource_columns": ["sorting_run_id"]},
                       {"columns": ["electrode_id"], "resource": "core.electrodes",
                        "resource_columns": ["electrode_id"]}],
        "rules": [], "since": SINCE[0]}

    # ---- R85 §2.1 : a device declares the port it attached to -----------------------------------
    # R67 §2.1 gave the chain its reference and stopped at which device; which *port of it* was
    # left in the child's name, and R67 §2.1 forbids reading a name. Thirteen of twenty rows have
    # no serial and repeat their part number, so position is what keeps them apart -- the name
    # cannot be cleaned up, and the fact moves into a column instead. Open, because the coordinate
    # a link is named by differs along the chain: a probe attaches to a dock, a headstage to a
    # port, a card to a slot. Nullable, since a writer knowing the parent and not the port must
    # leave it unstated rather than invent one (R66 §1.4).
    SINCE[0] = "R85 §2.1"
    add_col("core.devices",
            col("parent_port", "string", "nullable",
                "Which port, dock or slot of `parent_device_id` this device attached to. Null "
                "where the attachment is stated and its coordinate is not. Establishes nothing "
                "about identity: two rows may share a parent and a port (R85 §2.3)."),
            after="parent_device_id")

    SINCE[0] = "R88 §2.1"
    # A table reaching `core.sessions` through its declared references is session-scoped (R86
    # §2.1), which 33 of 35 are, and until now they used four conventions between them. Eight
    # held no session column at all, so R86 §2.2's discriminator had nothing to derive from and
    # the reader refused; six held one and declared no reference, so Tier 1 generated no
    # anti-join and 418,618,218 rows across the two packets carried a session key nothing
    # validated. `core.devices` and `core.processing_runs` were nullable for a question R86 §2.1
    # now answers, and neither is null in any packet built.
    SESSION_COLUMN = (
        "analysis.array_dimensions", "core.array_channels", "core.array_dimensions",
        "core.clock_anchors", "core.electrode_coordinates",
        "core.event_stream_observation_intervals", "core.media_frames",
        "core.processing_run_inputs",
    )
    SESSION_REFERENCE = (
        "analysis.spike_events", "core.sorting_run_channels", "core.unit_coordinates",
        "core.unit_electrodes", "core.unit_observation_intervals", "core.unit_quality_labels",
    )
    for resource in SESSION_COLUMN:
        # First, as the sixteen tables already doing this have it. R88 §2.3: a writer fills it
        # from the parent it is exactly one hop from, so the column costs no new read.
        T(resource)["columns"].insert(0, col("session_id", "int32", "required", "Session ID."))
    for resource in (*SESSION_COLUMN, *SESSION_REFERENCE):
        T(resource)["references"].append(
            {"columns": ["session_id"], "resource": "core.sessions",
             "resource_columns": ["session_id"]})
    SINCE[0] = "R88 §2.1"
    for resource in ("core.devices", "core.processing_runs"):
        # `02` hedged these as "if session-scoped", written before anything could compute scope.
        amend(resource, "session_id", presence="required")

    # ---- R89 §2 : a packet records the calibrations of its instruments ------------------------
    # A calibration is what someone measured about an instrument so that its numbers can be
    # interpreted, and nothing recorded one: two extensions carry a calibrated quantity
    # (`aind_opto.emissions.power_mw`, `dynamic_foraging.sessions.reward_size_left`) and neither
    # could say what calibrated it. Not a `core.processing_runs` row -- both packets cite water
    # curves measured 133 and 302 days before the session, and a run is what produced resources in
    # this packet (R89 §1.2).
    SINCE[0] = "R89 §2.1"
    tables["core.calibrations"] = {
        "columns": [
            col("calibration_id", "int32", "required", "Stable calibration ID."),
            col("session_id", "int32", "required", "Session ID."),
            col("calibration_name", "string", "required",
                "What `calibration_id` stands for: the identifier a source or an earlier packet "
                "used for this calibration. Required, and composed by the writer where the source "
                "names none, since R85 §2.2 makes two calibrations sharing a name one row."),
            col("calibration_type", "string", "required",
                "What was calibrated: `water_volume`, `light_power`, `manipulator_transform`. Open "
                "(R8 §4). Named `_type` rather than `_kind` because a `_kind` column is a "
                "discriminator (R55 §2.1), and this holds a value that resolves to no table."),
            col("calibrated_at", "timestamp", "nullable",
                "When the calibration was measured, which is not when it was in force: R89 §1.2 "
                "measures 133 and 302 days between them. Null where the source states none, since "
                "what a source did not say is not invented (R66 §2.1)."),
            col("description", "string", "nullable", "What the source said the calibration was."),
            col("input_unit", "string", "nullable",
                "The unit of measure of `core.calibration_points.input_value`. On the calibration "
                "because it varies per calibration -- seconds for water, volts for opto -- so no "
                "literal unit can sit on the value column (R89 §2.3)."),
            col("output_unit", "string", "nullable",
                "The unit of measure of `core.calibration_points.output_value`."),
            col("array_asset_id", "int32", "nullable",
                "The array holding this calibration where its content is one rather than a curve: "
                "a manipulator transform, a camera's intrinsics (R89 §2.4)."),
            col("detail_kind", "string", "nullable",
                "A table carrying a calibration shape core does not define, as a dotted resource "
                "ID. Open, and `resolves: optional`, so a kind the packet cannot resolve records "
                "that the content is elsewhere rather than that the row is wrong (R89 §2.5)."),
        ],
        "primary_key": ["calibration_id"],
        "references": [{"columns": ["session_id"], "resource": "core.sessions",
                        "resource_columns": ["session_id"]},
                       {"columns": ["array_asset_id"], "resource": "core.array_assets",
                        "resource_columns": ["array_asset_id"]}],
        "rules": [], "since": SINCE[0]}

    # R89 §2.2: the devices a calibration covers are a repeated value, so a child table and not a
    # column (R3 §3.0). One `device_id` on the calibration would record six calibrations of the
    # rig's manipulators where it performed one -- R67 §3's defect with its multiplicity reversed.
    SINCE[0] = "R89 §2.2"
    tables["core.calibration_devices"] = {
        "columns": [col("session_id", "int32", "required", "Session ID."),
                    col("calibration_id", "int32", "required",
                        "The calibration this row names a device for."),
                    col("device_id", "int32", "required", "A device the calibration covers.")],
        "primary_key": ["calibration_id", "device_id"],
        "references": [{"columns": ["session_id"], "resource": "core.sessions",
                        "resource_columns": ["session_id"]},
                       {"columns": ["calibration_id"], "resource": "core.calibrations",
                        "resource_columns": ["calibration_id"]},
                       {"columns": ["device_id"], "resource": "core.devices",
                        "resource_columns": ["device_id"]}],
        "rules": [], "since": SINCE[0]}

    # R89 §2.3: the measured curve, where `rig.json` holds two parallel JSON lists R3 §3.0 forbids.
    SINCE[0] = "R89 §2.3"
    _points = [col("session_id", "int32", "required", "Session ID."),
               col("calibration_id", "int32", "required", "The calibration this point belongs to."),
               col("point_index", "int64", "required",
                   "0-based position in the curve's own order. The key is not `input_value` even "
                   "though the inputs are distinct: an equality join on a float64 is not safe, "
                   "which is why R47 could strike `interval_index` and this stays."),
               col("input_value", "float64", "required", "The setting the point was measured at."),
               col("output_value", "float64", "required", "What the instrument then delivered.")]
    # Declared here rather than in CONTEXT, which is consumed above -- these columns do not exist
    # when that block runs. R56 §2.3's one-hop `resource.column` form, resolved through the
    # reference to `core.calibrations` below, and its first use for a unit rather than a clock.
    _points[3]["unit_from"] = "core.calibrations.input_unit"
    _points[4]["unit_from"] = "core.calibrations.output_unit"
    tables["core.calibration_points"] = {
        "columns": _points,
        "primary_key": ["calibration_id", "point_index"],
        "references": [{"columns": ["session_id"], "resource": "core.sessions",
                        "resource_columns": ["session_id"]},
                       {"columns": ["calibration_id"], "resource": "core.calibrations",
                        "resource_columns": ["calibration_id"]}],
        "rules": [], "since": SINCE[0]}

    # ---- R91 §3 : an event is an occurrence on a stream ---------------------------------------
    # Three of `core.events`' columns were the stream's. `clock_id` differed from its stream's on
    # 0 of 5,485 and 0 of 6,256 rows; `event_type` was computed from the stream's own name by the
    # only adapter that writes an event; `event_name` was that name plus an ordinal, generated by
    # R53 §2.3.1 to explain a surrogate nothing references. The surrogate and its name cost 41,164
    # of the table's 56,115 compressed bytes.
    SINCE[0] = "R91 §3.1"
    add_col("core.event_streams",
            col("event_type", "string", "required",
                "What kind of event this stream emits. Open (R8 §4); a stream emits one kind, so a "
                "source emitting several on one channel is written as several streams."),
            after="name")
    add_col("core.event_streams",
            col("detail_kind", "string", "nullable",
                "A table specialising this stream's events, as a dotted resource ID. Open, and "
                "`resolves: optional`, so a kind the packet cannot resolve records that the detail "
                "is elsewhere (R90 §3.4). Resolved against `core.events`' key by R90 §3.5's shared "
                "key, through the reference `discriminates_via` names."),
            after="event_type")
    # R90 §3.2: the discriminator sits a reference away from the rows it specialises, so it names
    # the referencing column. Set after `col`, which classifies from the name alone.
    next(c for c in T("core.event_streams")["columns"]
         if c["name"] == "detail_kind")["discriminates_via"] = "core.events.stream_id"

    SINCE[0] = "R91 §3.2"
    for _struck in ("event_id", "event_name", "event_type", "clock_id"):
        drop_col("core.events", _struck)
    T("core.events")["references"] = [r for r in T("core.events")["references"]
                                      if r["resource"] != "core.clocks"]
    T("core.events")["primary_key"] = ["session_id", "stream_id", "t_tick"]
    # R56 §2.3's one-hop form: with no `clock_id` on the row, §2.2's default no longer applies.
    next(c for c in T("core.events")["columns"]
         if c["name"] == "t_tick")["clock_from"] = "core.event_streams.clock_id"

    # ---- R95 §3.1 : one name column per table -------------------------------------------------
    # R53 §2.3.1 generates a `<base>_name` for every assigned identifier in a key, and seven tables
    # already declared a `name` from `02`, so they carried both -- equal on every row of every
    # packet that writes them. The generated column has R53 §2.5's meaning and the declared one has
    # `02`'s presence, so one survives with both: the generated name keeps its own description and
    # takes the presence `02` gave, and `name` is struck.
    SINCE[0] = "R95 §3.1"
    for resource, spec in tables.items():
        declared = next((c for c in spec["columns"] if c["name"] == "name"), None)
        if declared is None:
            continue
        generated = next((c for c in spec["columns"]
                          if c["name"].endswith("_name") and c.get("since") == "R53 §2.3.1"), None)
        if generated is None:
            raise SystemExit(f"R95 §3.1: {resource} declares `name` and no generated name to merge it into")
        generated["presence"] = declared["presence"]
        generated["since"] = SINCE[0]
        spec["columns"].remove(declared)

    # ---- R96 §3 : a unit declares what its spikes are counted on and measured in --------------
    # Both facts belong to the sorting run and a spike cannot reach it: R56 §2.3 admits one hop and
    # spike -> unit -> run is two. They move to `core.units`, which a spike references directly, so
    # each resolves in the one hop the format allows.
    SINCE[0] = "R96 §3.1"
    drop_col("core.sorting_runs", "amplitude_unit")
    add_col("core.units", col("amplitude_unit", "string", "nullable",
                              "Unit of measure of `core.spike_events.amplitude` for this unit's "
                              "spikes -- microvolts, or ADC counts. Open (R11 §2)."),
            after="quality_label")
    amend("core.units", "amplitude_unit", vocabulary="open")

    SINCE[0] = "R96 §3.2"
    drop_col("core.sorting_runs", "clock_id")
    T("core.sorting_runs")["references"] = [r for r in T("core.sorting_runs")["references"]
                                            if r["resource"] != "core.clocks"]
    add_col("core.units", col("clock_id", "int32", "required",
                              "The clock every tick of this unit is counted on."),
            after="amplitude_unit")
    T("core.units")["references"].append({"columns": ["clock_id"], "resource": "core.clocks",
                                          "resource_columns": ["clock_id"]})

    # §3.3: one hop each, through the reference `core.spike_events` already declares on `unit_id`.
    SINCE[0] = "R96 §3.3"
    amend("core.spike_events", "amplitude", unit_from="core.units.amplitude_unit")
    amend("core.spike_events", "t_tick", clock_from="core.units.clock_id")

    # §3.4: with the hop resolving, the copies say nothing the reference does not.
    SINCE[0] = "R96 §3.4"
    drop_col("core.spike_events", "clock_id")
    T("core.spike_events")["references"] = [r for r in T("core.spike_events")["references"]
                                            if r["resource"] != "core.clocks"]
    drop_col("core.unit_observation_intervals", "clock_id")
    T("core.unit_observation_intervals")["references"] = [
        r for r in T("core.unit_observation_intervals")["references"] if r["resource"] != "core.clocks"]
    for _bound in ("start_tick", "stop_tick"):
        amend("core.unit_observation_intervals", _bound, clock_from="core.units.clock_id")

    # ---- R97 §3 : the free-form metadata column -----------------------------------------------
    # Where the primary key decides the column, it is generated rather than declared (R97 §3.1). A
    # key holding an identifier of its own -- carried or assigned, and not part of a declared
    # reference -- makes the row a thing, and a thing may carry what its source said about it; a key
    # made entirely of other tables' identifiers makes the row a relationship, and nothing can be
    # said about a relationship that is not a fact about one of its ends. Both bands drop whatever
    # `02` or a revision gave them and take what this pass emits, so a table added later carries the
    # column without anyone remembering to, and a hand declaration of the wrong type cannot survive.
    #
    # Between the bands the declaration is a judgement and is left alone: `core.events` is the one
    # table that makes it, beside the `payload` R91 §3.3 keeps.
    #
    # Runs after every key change above, since the key is what it reads.
    SINCE[0] = "R97 §3.1"
    METADATA = ("What the source stated about this row that the standard does not model, carried "
                "in the source's own vocabulary and read by no rule.")
    # Three judgements withdrawn: no adapter writes these and no consumer asks (R97 §5).
    for _resource in ("core.spike_events", "core.media_frames", "core.array_channels"):
        drop_col(_resource, "metadata")

    for resource, spec in tables.items():
        referenced = {c for r in spec["references"] for c in r["columns"]}
        roles = {c["name"]: c["role"] for c in spec["columns"]}
        key = spec["primary_key"] or []
        own = [k for k in key if roles.get(k) == "identifier" and k not in referenced]
        if not own and not (key and all(k in referenced for k in key)):
            continue
        drop_col(resource, "metadata")
        if own:
            add_col(resource, col("metadata", "json_string", "optional", METADATA))

    # §3.4: one text for every declaration, replacing the sixteen reading "Additional metadata."
    # and the four naming their own table. The generated ones carry it already, so what this reaches
    # is the judgement `core.events` makes; it also stamps every column with the clause that settled
    # the wording. R2 §5's third presence state is what §3.2 spends, so a `metadata` column is
    # `optional` and a declaration outside the generated bands may not leave one otherwise.
    SINCE[0] = "R97 §3.4"
    for resource, spec in tables.items():
        if any(c["name"] == "metadata" for c in spec["columns"]):
            amend(resource, "metadata", presence="optional", description=METADATA)

    # ---- Tier 2 rules, merged from rules.json (R2 §7.2) --------------------------------------
    # Last, so every table exists to be named and every primary key is final -- R24's templates
    # expand against the key, and R7 above is what settles three of them.
    authored = json.loads(RULES.read_text())
    hand_written: dict[str, list[dict]] = authored["rules"]
    unknown = sorted(set(hand_written) - set(tables))
    if unknown:
        raise SystemExit(f"rules.json names tables the registry does not define: {', '.join(unknown)}")
    for resource, table_rules in hand_written.items():
        expanded: list[dict[str, str]] = []
        for rule in table_rules:
            if template := rule.get("use"):
                expanded.extend(expand(template, resource, rule, T(resource)["primary_key"]))
            else:
                expanded.append(rule)
        T(resource)["rules"] = expanded

    # Held while the schema is unreleased. Version discipline is Phase 6, and a bump per
    # revision numbers churn rather than releases.
    #
    # Holding it is safe because the thing R2 §8 protects -- a packet carrying a registry that
    # identifies its content -- can only be broken by an *amendment*, which is the one case
    # where a packet ends up retaining two. A packet built fresh embeds exactly one, so no
    # version can be ambiguous inside it. `PacketWriter._install_registry` refuses the
    # amendment that would create the ambiguity, so the bump happens when it is forced rather
    # than on a schedule.
    # R57 §2.1: first, so what governs the document is visible without reading it. Read from
    # the meta-schema rather than repeated, since a copy is what goes stale.
    return {"$schema": json.loads((HERE / "registry.schema.json").read_text())["$id"],
            "registry_version": "0.1.0",
            "semantic_standard_version": "escapewheel-semantic-v0.1",
            "logical_standard_version": "escapewheel-logical-v0.1",
            # Every revision whose decisions are applied above, so the registry says what it
            # was derived from rather than leaving it to the block comments. The union of what
            # the blocks stamped and what only this file records, so adding a column-touching
            # revision cannot leave the list behind.
            "derived_from": {"specification": "nwb_lake_poc_docs/02_core_logical_schemas.md",
                             "revisions": sorted({*SINCE.applied, *(f"R{n}" for n in UNSTAMPED)},
                                                 key=lambda r: int(r[1:]))},
            "tables": dict(sorted(tables.items()))}


if __name__ == "__main__":
    reg = build()
    OUT.write_text(json.dumps(reg, indent=2) + "\n")
    print(f"wrote {OUT.name}: {len(reg['tables'])} tables, "
          f"{sum(len(t['columns']) for t in reg['tables'].values())} columns, "
          f"{sum(len(t['rules']) for t in reg['tables'].values())} rules merged from {RULES.name}")

    # Rendered here rather than by hand, so the readable form cannot drift from the content.
    # The README's counts go the same way: it claimed 33 tables and 51 rules against a registry
    # holding 34 and 61, and `check.py` now fails on a stale one.
    import render

    print(f"wrote {', '.join(p.name for p in render.main())}")

    # The two hand-written schemas are consumed by sibling distributions, which vendor them
    # because a wheel cannot read a file from another repository. A vendored copy is therefore a
    # *build artifact* and not a file to maintain: a stale one has broken every packet three
    # times -- R48, R53 and R56 -- each time reported as a hundred findings about the data rather
    # than one about the copy. Written here so the class of bug cannot recur, and compared by
    # `check.py` so a build nobody ran is still caught.
    for schema, consumer in VENDORED.items():
        source = HERE / schema
        if not consumer.parent.is_dir():
            print(f"skip  {schema} -> {consumer} (sibling not present)")
            continue
        if consumer.exists() and consumer.read_text() == source.read_text():
            continue
        consumer.write_text(source.read_text())
        print(f"wrote {consumer.relative_to(HERE.parent)}")
