"""A credential is not a recipe's to carry, and no run records one."""

from __future__ import annotations

from escapewheel_writer.errors import (
    RecipeFault,
)
from escapewheel_writer.recipe import Recipe
from tests.builders import problems_coded, write_recipe

# -- a credential is not a recipe's to carry ------------------------------------------------


SIGNED = """
[[source]]
kind = "sorter"
root = "s3://private/ecephys"
owns = []
storage_options = {{ {options} }}
"""


def test_a_storage_option_carrying_a_credential_is_refused(tmp_path, registry):
    """The recipe is recorded in the packet it builds, so a key written here travels with it."""
    recipe = Recipe.load(write_recipe(tmp_path, SIGNED.format(options='key = "AKIA...", secret = "xyz"')))
    refused = problems_coded(recipe.check(registry), RecipeFault.CREDENTIAL, "error")
    assert ["storage_options.key" in p.message for p in refused] == [True, False]


def test_a_reference_to_a_credential_is_not_one(tmp_path, registry):
    """A profile names where the secret is; the environment holds it and nothing crosses."""
    recipe = Recipe.load(write_recipe(tmp_path, SIGNED.format(options='profile = "aind", anon = false')))
    assert not problems_coded(recipe.check(registry), RecipeFault.CREDENTIAL)


def test_a_token_that_names_a_mode_is_not_a_credential(tmp_path, registry):
    """gcsfs reads a public bucket with `token = "anon"`, so the name alone does not decide."""
    mode = Recipe.load(write_recipe(tmp_path, SIGNED.format(options='token = "anon"')))
    assert not problems_coded(mode.check(registry), RecipeFault.CREDENTIAL)
    real = Recipe.load(write_recipe(tmp_path, SIGNED.format(options='token = "ya29.a0..."'), "signed.toml"))
    assert problems_coded(real.check(registry), RecipeFault.CREDENTIAL)


def test_what_a_run_records_carries_no_credential(tmp_path):
    """Applied wherever a recipe is written down, since one written before the refusal exists."""
    from escapewheel_writer.secrets import REDACTED, redacted

    document = {
        "source": [
            {"kind": "sorter", "storage_options": {"key": "AKIA...", "anon": False}},
            {"kind": "nwb", "root": "/data/session.nwb"},
        ],
        "session": {"session_id": "s001"},
    }
    clean = redacted(document)
    assert clean["source"][0]["storage_options"] == {"key": REDACTED, "anon": False}
    assert clean["source"][1] == document["source"][1], "everything else is recorded as written"
    assert document["source"][0]["storage_options"]["key"] == "AKIA...", "the original is untouched"
