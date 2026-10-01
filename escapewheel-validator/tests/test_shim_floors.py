"""What a validation reports it did not assess against the reader floor."""

from types import SimpleNamespace

from escapewheel_validator import Report
from escapewheel_validator.shim.floors import report_unassessed


def test_each_unassessed_external_is_its_own_registrys_finding():
    """Part 05 §5.3: one finding per resource, attributed as Part 05 §9.5 attributes a resource's."""
    resources = [
        SimpleNamespace(
            resource_id="core.lfp", declaration_id="core.array_asset_instances", is_external=True, interface="zarr"
        ),
        SimpleNamespace(resource_id="task.lfp", declaration_id="task.arrays", is_external=True, interface="zarr"),
        SimpleNamespace(resource_id="task.table", declaration_id="task.tables", is_external=True, interface="parquet"),
        SimpleNamespace(resource_id="core.video", declaration_id="core.media", is_external=True, interface=None),
        SimpleNamespace(resource_id="core.owned", declaration_id="core.media", is_external=False, interface="zarr"),
    ]
    report = Report(bound=("core", "task"))
    report.attribute(
        {"core.array_asset_instances": "core", "core.media": "core", "task.arrays": "task", "task.tables": "task"},
        resources,
    )
    report_unassessed(SimpleNamespace(resources=lambda: resources), {"task.table"}, report)
    assert [(f.level, f.check, f.registry, f.rows) for f in report.findings] == [
        ("info", "external.physical_unassessed", "core", (("core.lfp",),)),
        ("info", "external.physical_unassessed", "task", (("task.lfp",),)),
    ]
