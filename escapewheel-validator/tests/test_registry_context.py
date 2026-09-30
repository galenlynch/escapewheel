"""The validator's use of a checked registry context; the checker's own tests lie in the specification's tree."""

import pytest

from escapewheel_validator import RegistryRejected, generate
from escapewheel_validator.registry_document import check_registry_context


def test_generator_rejects_a_nonvalid_checked_context():
    context = check_registry_context({"$schema": "https://example.org/unknown"})
    with pytest.raises(RegistryRejected) as caught:
        generate(context)
    assert caught.value.result is context.result
