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


def col(name, typ, pres, desc):
    return {"name": name, "type": typ, "presence": pres, "description": desc}


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

    index, op = call["index"], call["overlap_op"]
    by = ", ".join(subject)
    rules.append({"id": f"{resource}.index_contiguous", "level": "error",
                  "message": f"{index} is not contiguous from 0",
                  "sql": (f"SELECT {by}, COUNT(*) AS n FROM {name} GROUP BY {by} "
                          f"HAVING MAX({index}) <> COUNT(*) - 1 OR MIN({index}) <> 0")})
    rules.append({"id": f"{resource}.non_overlapping", "level": "error",
                  "message": call["overlap_message"],
                  "sql": (f"SELECT {report}, {start}, {stop} FROM (SELECT *, LAG({stop}) OVER "
                          f"(PARTITION BY {by} ORDER BY {index}) AS prev_stop FROM {name}) "
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
            "sort": None,
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
            if c["name"] == old: c["name"] = new

    # ---- R3 §3.0 : tables do not restate what the array declares -----------------------
    for c in ("dtype", "shape"):
        drop_col("core.array_assets", c)

    # ---- R3 §3.1-3.3 : repeated values become child tables ------------------------------
    tables["core.session_experimenters"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("experimenter", "string", "required", "One experimenter.")],
        "primary_key": ["session_id", "experimenter"],
        "references": [{"columns": ["session_id"], "resource": "core.sessions",
                        "resource_columns": ["session_id"]}], "sort": None, "rules": []}
    tables["core.trial_tags"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("trial_id", "string", "required", "Trial ID."),
                    col("tag", "string", "required", "Tag value.")],
        "primary_key": ["session_id", "trial_id", "tag"],
        "references": [{"columns": ["session_id", "trial_id"], "resource": "core.trials",
                        "resource_columns": ["session_id", "trial_id"]}], "sort": None, "rules": []}
    tables["core.array_dimensions"] = {
        "columns": [col("array_asset_id", "string", "required", "Array asset ID."),
                    col("axis_index", "int64", "required",
                        "0-based axis position in stored order (R3 §5)."),
                    col("dimension_name", "string", "required", "Axis name.")],
        "primary_key": ["array_asset_id", "axis_index"],
        "references": [{"columns": ["array_asset_id"], "resource": "core.array_assets",
                        "resource_columns": ["array_asset_id"]}], "sort": None, "rules": []}

    # ---- R3 §3.4 : typed clock transform ------------------------------------------------
    add_col("core.clocks", col("transform_slope", "float64", "nullable",
            "Parent ticks per this clock's tick, as measured."), after="parent_clock_id")
    add_col("core.clocks", col("transform_offset", "float64", "nullable",
            "Parent-clock tick at this clock's tick 0."), after="transform_slope")

    # ---- R6 §2 : wall-clock binding -------------------------------------------------------
    add_col("core.clocks", col("tick_zero_utc", "timestamp", "nullable",
            "Wall-clock instant of tick 0 on this clock."), after="origin")

    # ---- R3 §6.1 : bind array_channels to an axis ---------------------------------------
    add_col("core.array_channels", col("axis_index", "int64", "required",
            "Axis that channel_index indexes, in stored order."), after="array_asset_id")
    T("core.array_channels")["references"].append(
        {"columns": ["array_asset_id", "axis_index"], "resource": "core.array_dimensions",
         "resource_columns": ["array_asset_id", "axis_index"]})

    # ---- R5 : flat spikes ----------------------------------------------------------------
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
    for t, n in [("core.electrodes", "local_electrode_label"),
                 ("core.electrodes", "local_channel_label"),
                 ("core.units", "local_unit_label")]:
        for c in T(t)["columns"]:
            if c["name"] == n:
                c["type"] = "string"
                c["description"] = "Opaque source label; undefined base, not an offset."

    # ---- R8 §3-4 : vocabularies -----------------------------------------------------------
    for c in T("core.processing_runs")["columns"]:
        if c["name"] == "status":
            c["enum"] = ["succeeded", "failed", "partial"]
    for t, n in [("core.array_assets", "kind"), ("core.array_assets", "semantic_type"),
                 ("core.media_assets", "semantic_type"),
                 ("core.processing_runs", "activity_type")]:
        for c in T(t)["columns"]:
            if c["name"] == n:
                c["vocabulary"] = "open"

    # ---- R11 §6 : trial_id conflates authored fact with derived join ------------------------
    drop_col("core.events", "trial_id")
    T("core.events")["references"] = [r for r in T("core.events")["references"]
                                      if "trial_id" not in r["columns"]]

    # ---- R11 §2 : amplitude units live on the sorting run -----------------------------------
    add_col("core.sorting_runs", col("amplitude_unit", "string", "nullable",
            "Unit of core.spike_events.amplitude for this run, e.g. uV, adc."),
            after="sorter_version")
    for c in T("core.sorting_runs")["columns"]:
        if c["name"] == "amplitude_unit":
            c["vocabulary"] = "open"

    # ---- R11 §3-4 : declared-open vocabularies ------------------------------------------------
    for c in T("core.units")["columns"]:
        if c["name"] == "quality_label":
            c["enum"] = ["sua", "mua", "noise"]                            # R11 §3
    for c in T("core.events")["columns"]:
        if c["name"] == "event_type":
            c["vocabulary"] = "open"
            c["reserved_values"] = ["stimulus_onset", "reward", "lick",
                                    "threshold_crossing", "ttl_edge", "sync_pulse"]

    # ---- R9 : provenance simplification ----------------------------------------------------
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
                        "resource_columns": ["source_file_id"]}], "sort": None, "rules": []}

    # ---- R10 : sort by primary key unless overridden -----------------------------------------
    OVERRIDE = {                                                          # R10 §3, from 03
        "core.spike_events": ["session_id", "sorting_run_id", "curation_id",
                              "unit_id", "t_tick"],
        "core.events": ["session_id", "clock_id", "t_tick", "event_type"],
    }
    for n, t in tables.items():
        t["sort"] = OVERRIDE.get(n) or t["primary_key"]                   # R10 §2, §6

    # ---- R18 §2 : units drift in and out of a recording -----------------------------------------
    tables["core.unit_observation_intervals"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("unit_id", "string", "required", "Unit ID."),
                    col("sorting_run_id", "string", "required", "Sorting run ID."),
                    col("curation_id", "string", "required", "Curation ID."),
                    col("interval_index", "int64", "required",
                        "0-based position in this unit's interval sequence."),
                    col("start_tick", "int64", "required", "First tick, inclusive."),
                    col("stop_tick", "int64", "required", "Last tick, inclusive."),
                    col("clock_id", "string", "required", "Clock for the interval bounds.")],
        "primary_key": ["session_id", "unit_id", "sorting_run_id", "curation_id",
                        "interval_index"],
        "references": [{"columns": ["session_id", "unit_id", "sorting_run_id", "curation_id"],
                        "resource": "core.units",
                        "resource_columns": ["session_id", "unit_id", "sorting_run_id",
                                             "curation_id"]},
                       {"columns": ["clock_id"], "resource": "core.clocks",
                        "resource_columns": ["clock_id"]}],
        "sort": None, "rules": []}

    # ---- R19 §2 : scaling and sample timing are per channel --------------------------------------
    for name, typ, desc in [
            ("conversion", "float64", "Multiply stored values by this before offset."),
            ("offset", "float64", "Add after conversion."),
            ("unit", "string", "Physical unit of the converted value."),
            ("inter_sample_shift", "float64",
             "Acquisition time offset within one sample period, in sample periods.")]:
        add_col("core.array_channels", col(name, typ, "nullable", desc), after="channel_label")

    # ---- R19 §3 : an electrode sits in more than one coordinate frame ----------------------------
    for c in ("x_um", "y_um", "z_um", "coordinate_frame"):
        drop_col("core.electrodes", c)
    tables["core.electrode_coordinates"] = {
        "columns": [col("electrode_id", "string", "required", "Electrode ID."),
                    dict(col("coordinate_frame", "string", "required",
                             "The frame these coordinates are in."), vocabulary="open"),
                    col("x_um", "float64", "nullable", "X in micrometres, in that frame."),
                    col("y_um", "float64", "nullable", "Y in micrometres."),
                    col("z_um", "float64", "nullable", "Z in micrometres.")],
        "primary_key": ["electrode_id", "coordinate_frame"],
        "references": [{"columns": ["electrode_id"], "resource": "core.electrodes",
                        "resource_columns": ["electrode_id"]}],
        "sort": None, "rules": []}

    # ---- R20 §2 : four coordinate forms per axis -------------------------------------------------
    for name, typ, desc in [
            ("clock_id", "string", "Clock the ticks are counted on (regular tick axis)."),
            ("origin_tick", "int64", "Tick at position 0."),
            ("step_ticks", "int64", "Ticks advanced per position."),
            ("origin_value", "float64", "Value at position 0 (regular numeric axis)."),
            ("step_value", "float64", "Increment per position."),
            ("coordinate_unit", "string", "Unit of the numeric coordinate values."),
            ("coordinate_array_asset_id", "string",
             "A 1-D array holding one value per position (irregular axis)."),
            ("coordinate_resource", "string",
             "Resource whose rows are this axis's positions (labelled axis)."),
            ("coordinate_position_column", "string",
             "Which column of that resource holds the 0-based position.")]:
        add_col("core.array_dimensions", col(name, typ, "nullable", desc),
                after="dimension_name")
    T("core.array_dimensions")["references"].append(
        {"columns": ["clock_id"], "resource": "core.clocks", "resource_columns": ["clock_id"]})

    # ---- R16 §2-3 : unit quality is many labels, attributed ------------------------------------
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
        "sort": None, "rules": []}
    add_col("core.units", dict(col("quality_label_source", "string", "nullable",
            "Which core.unit_quality_labels source the designated label came from."),
            vocabulary="open"), after="quality_label")

    # ---- R23 §2-3 : events get the context table every other core stream has -----------------
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
                        "table."),
                    col("metadata", "json_string", "optional", "Free-form metadata.")],
        "primary_key": ["event_stream_id"],
        "references": [{"columns": ["session_id"], "resource": "core.sessions",
                        "resource_columns": ["session_id"]},
                       {"columns": ["device_id"], "resource": "core.devices",
                        "resource_columns": ["device_id"]},
                       {"columns": ["clock_id"], "resource": "core.clocks",
                        "resource_columns": ["clock_id"]},
                       {"columns": ["processing_run_id"], "resource": "core.processing_runs",
                        "resource_columns": ["processing_run_id"]}],
        "sort": None, "rules": []}
    add_col("core.events", col("stream_id", "string", "required",
                               "The stream this event belongs to."), after="event_id")
    T("core.events")["references"].append(
        {"columns": ["stream_id"], "resource": "core.event_streams",
         "resource_columns": ["event_stream_id"]})

    # ---- R25 §2 : streams drop out too; absence of an event is ambiguous without this -------
    tables["core.event_stream_observation_intervals"] = {
        "columns": [col("event_stream_id", "string", "required", "The stream being observed."),
                    col("interval_index", "int64", "required",
                        "0-based position in this stream's interval sequence."),
                    col("start_tick", "int64", "required",
                        "First observed tick, on the stream's clock."),
                    col("stop_tick", "int64", "required",
                        "Last observed tick, on the stream's clock.")],
        "primary_key": ["event_stream_id", "interval_index"],
        # No clock_id: core.event_streams declares one, and an interval is meaningless without
        # joining to its stream anyway, so repeating it buys nothing (R25 2.1).
        "references": [{"columns": ["event_stream_id"], "resource": "core.event_streams",
                        "resource_columns": ["event_stream_id"]}],
        "sort": None, "rules": []}
    add_col("core.sessions", col("session_end_time", "timestamp", "nullable",
            "When the session ended, UTC. Metadata, not derived from the tables (R25 5)."),
            after="session_start_time")

    # ---- R27 §2 : "synchronized" has to name a clock ------------------------------------------
    # A reader's default is to return times on one clock. A session with two unparented clocks
    # has two roots and nothing chooses between them, so the session says which.
    add_col("core.sessions", col("reference_clock_id", "string", "nullable",
            "The clock this session's times are reported on by default (R27 2)."),
            after="session_end_time")
    T("core.sessions")["references"].append(
        {"columns": ["reference_clock_id"], "resource": "core.clocks",
         "resource_columns": ["clock_id"]})

    # ---- R13 §3 : anchor-point clock alignment ------------------------------------------------
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
        "sort": None, "rules": []}

    # ---- R28 §2-4 : a unit sits on many electrodes, and somewhere -----------------------------
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
                    col("channel_ordinal", "int64", "nullable",
                        "0-based position in the unit's channel list, where a dense array axis "
                        "is indexed by it (R20 §2). Not an identifier; nothing joins on it."),
                    col("is_primary", "bool", "nullable",
                        "Whether this is the unit's peak electrode."),
                    col("amplitude", "float64", "nullable",
                        "The unit's amplitude here, in core.sorting_runs.amplitude_unit.")],
        "primary_key": [*unit_key, "electrode_id"],
        "references": [unit_ref,
                       {"columns": ["electrode_id"], "resource": "core.electrodes",
                        "resource_columns": ["electrode_id"]}],
        "sort": None, "rules": []}
    tables["core.unit_coordinates"] = {
        "columns": [col("session_id", "string", "required", "Session ID."),
                    col("unit_id", "string", "required", "Unit ID."),
                    col("sorting_run_id", "string", "required", "Sorting run ID."),
                    col("curation_id", "string", "required", "Curation ID."),
                    col("coordinate_frame", "string", "required",
                        "The frame these coordinates are in. Open, as R19 §3 left it."),
                    col("x_um", "float64", "nullable", "X in micrometres, in that frame."),
                    col("y_um", "float64", "nullable", "Y in micrometres."),
                    col("z_um", "float64", "nullable", "Z in micrometres.")],
        "primary_key": [*unit_key, "coordinate_frame"],
        "references": [unit_ref],
        "sort": None, "rules": []}
    # The one link between a dense array's channels and the electrodes they came from, which
    # until now nothing validated.
    T("core.array_channels")["references"].append(
        {"columns": ["electrode_id"], "resource": "core.electrodes",
         "resource_columns": ["electrode_id"]})

    # ---- Tier 2 rules, merged from rules.json (R2 §7.2) --------------------------------------
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

    # ---- R20 §5 : analysis arrays are described by analysis tables -------------------------------
    import copy
    for core_name in ("core.array_assets", "core.array_dimensions"):
        mirror = copy.deepcopy(T(core_name))
        mirror["references"] = [
            dict(r, resource=r["resource"].replace("core.array_", "analysis.array_"))
            if r["resource"].startswith("core.array_") else r
            for r in mirror["references"]]
        mirror["rules"] = []
        tables[core_name.replace("core.", "analysis.")] = mirror

    # ---- R7 : every table declares a key ---------------------------------------------------
    for n, k in [("core.media_assets", ["media_asset_id"]),
                 ("core.processing_runs", ["processing_run_id"]),
                 ("core.source_files", ["source_file_id"])]:
        T(n)["primary_key"] = k

    return {"registry_version": "0.1.0",
            "semantic_standard_version": "nwb-lake-semantic-v0.1",
            "logical_standard_version": "nwb-lake-logical-v0.1",
            "derived_from": {"specification": "nwb_lake_poc_docs/02_core_logical_schemas.md",
                             "revisions": ["R1", "R2", "R3", "R4", "R5",
                                           "R6", "R7", "R8", "R9"]},
            "tables": dict(sorted(tables.items()))}


if __name__ == "__main__":
    reg = build()
    OUT.write_text(json.dumps(reg, indent=2) + "\n")
    print(f"wrote {OUT.name}: {len(reg['tables'])} tables, "
          f"{sum(len(t['columns']) for t in reg['tables'].values())} columns, "
          f"{sum(len(t['rules']) for t in reg['tables'].values())} rules merged from {RULES.name}")
