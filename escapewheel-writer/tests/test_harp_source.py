"""Harp devices, read from the `device.yml` beside each acquisition."""

from escapewheel_writer.sources.harp import HarpSource

SCHEMA = "device: SniffDetector\nwhoAmI: 1401\nfirmwareVersion: '0.2'\nhardwareTargets: '1.0'\n"


def harp(tmp_path, **options):
    acquisition = tmp_path / "SniffDetector.harp"
    acquisition.mkdir()
    (acquisition / "device.yml").write_text(SCHEMA)
    return HarpSource(tmp_path, session_id="s001", **options)


def test_a_device_is_named_by_its_schema(tmp_path):
    (row,) = harp(tmp_path).devices()
    assert (row["device_id"], row["device_name"], row["model"]) == ("SniffDetector", "SniffDetector", "Harp 1401")


def test_a_prefix_reaches_the_device_id_and_its_name(tmp_path):
    """Part 02 §8.2: the name is what the ID is minted from, prefix included."""
    (row,) = harp(tmp_path, prefix="A_").devices()
    assert (row["device_id"], row["device_name"]) == ("A_SniffDetector", "A_SniffDetector")
