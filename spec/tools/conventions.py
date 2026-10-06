"""The core registry's declared exceptions to the naming conventions of `checkers/registry_conventions.py`.

`check.py` applies the conventions to the core registry with these; an extension declares its own
in a `conventions.toml` beside its document.
"""

#: The core registry's columns breaking a naming convention on purpose, each with the reason. An
#: exception is declared, never inferred, so removing a column here without renaming it fails.
NAMING_EXCEPTIONS = {
    "core.array_assets.resource_id": "Part 02 §2.6: packet identity is a carried string before row numbering",
    "analysis.array_assets.resource_id": "as core.array_assets.resource_id",
    "core.media_assets.resource_id": "as core.array_assets.resource_id",
    "core.sidecars.resource_id": "as core.array_assets.resource_id, and the table's whole key (Part 02 §12.10)",
    "core.sidecar_scopes.resource_id": "references core.sidecars.resource_id, which Part 02 §2.6 makes a string",
    "core.array_assets.offset": "NWB-standard name; the reserved word is handled by unconditional quoting",
    "analysis.array_assets.offset": "as core.array_assets.offset",
    "core.array_channels.offset": "as core.array_assets.offset, per channel",
    "core.units.n_spikes": "a count, not a plural duration",
    "core.source_files.size_bytes": "a quantity in bytes, not a plural of `size_byte`",
    "core.media_frames.pts": "the container's own initialism for one timestamp, not a plural (Part 01 §3.18)",
    # Part 02 §12.11: `_kind` reads as a category, and this holds the table whose rows an axis's
    # positions stand for, which its role says and its name cannot.
    "core.array_dimensions.coordinate_resource": "names the table whose rows the axis's positions stand for, "
    "not a kind of thing (Part 02 §12.11)",
    "analysis.array_dimensions.coordinate_resource": "as core.array_dimensions.coordinate_resource",
}

#: Part 02 §8.2: the core registry's name columns naming a kind of thing rather than one assigned
#: identifier's value, and so expected to repeat. Declared for the reason the naming exceptions
#: are: a set absorbing whatever has no `*_id` sibling would absorb the next one added without it.
NAMES_A_KIND = {
    "core.array_dimensions.dimension_name": "an axis's name, repeated across every array",
    "analysis.array_dimensions.dimension_name": "as core.array_dimensions.dimension_name",
    "core.probes.insertion_name": "the trajectory the probe was inserted along, not the probe",
    "core.processing_runs.software_name": "what ran, so every run of one tool repeats it",
    "core.sessions.task_name": "which task, so every session running it repeats the name",
    "core.sorting_runs.sorter_name": "as software_name, per sorting",
    "core.coordinate_frame_axes.axis_name": "what the source called the field, repeated across "
    "every frame that read the same one (Part 01 §3.24)",
}
