import escapewheel_dev as ew


def test_every_registry_satisfies_the_registry_schema():
    for registry in ew.registries().values():
        assert ew.schema_errors("registry", registry.document) == [], registry.registry_id


def test_an_error_names_where_it_is():
    document = dict(ew.registry().document)
    document["registry_id"] = 7
    assert any(error.startswith("/registry_id: ") for error in ew.schema_errors("registry", document))


def test_schemas_are_named_by_file_stem():
    assert {"manifest", "registry", "recipe"} <= set(ew.schemas())
