"""Source adapters for the Allen Institute for Neural Dynamics' own formats.

Each adapter registers a source kind through the ``escapewheel.sources`` entry-point group, so a
recipe names it as it names a built-in kind. Nothing is imported from this package directly.

Its modules:

session
    ``session.json`` and ``subject.json``: each stream's observation window, and where tick zero
    sits.
calibrations
    The calibration tables, from ``rig.json`` and a session's probe modules.
video
    A behaviour video's frame times, reconstructed from the camera's own counter.
nwb
    The columns and conventions an AIND pipeline adds to an otherwise ordinary NWB.
unit_qc
    The unit quality metrics a sorting analyzer computes, as the ``aind_unit_qc`` extension.
compensations
    The upstream faults these adapters work around, recorded in the packet.
errors
    The codes a defect from these adapters carries.
resource_ids
    The extension resource IDs these adapters name.
recipe
    ``escapewheel-aind-recipe``, which drafts a session's recipe from its public assets.

Notes
-----
    The codes a note from these adapters carries.

The package depends on `escapewheel-writer` and nothing in the writer imports it. A build refuses a
kind it neither ships nor is told how to reach, so a recipe naming one of these sets
``in_process = true`` or gives a ``[source.delivery]`` command (Part 05 §3.9).
"""

__all__: list[str] = []
