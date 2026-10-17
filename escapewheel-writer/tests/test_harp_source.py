"""Harp devices, read from the `device.yml` beside each acquisition, and their registers as signals."""

import struct

import numpy as np
import pytest

from escapewheel_writer.errors import SourceDefect, SourceFault, UsageError, UsageFault
from escapewheel_writer.sources.harp import HarpSource

SCHEMA = (
    "device: SniffDetector\nwhoAmI: 1401\nfirmwareVersion: '0.2'\nhardwareTargets: '1.0'\n"
    "registers:\n  RawVoltage:\n    address: 32\n    type: U16\n    access: Event\n"
)

HARP = {"clock_id": "harp", "session_id": "s001", "tick_rate_num": 31250}

#: (message type, seconds, 32 µs ticks, value): three events 78 and 79 ticks apart, and the write
#: that configured the register, which is no sample.
MESSAGES = [(3, 10, 0, 900), (2, 10, 40, 7), (3, 10, 78, 910), (3, 10, 157, 905)]


def message(kind, seconds, ticks, value, address=32):
    """One timestamped U16 Harp message: header, seconds, ticks, payload, checksum."""
    body = struct.pack("<BBBBBIHH", kind, 12, address, 255, 0x12, seconds, ticks, value)
    return body + bytes([sum(body) & 0xFF])


def acquisition(tmp_path, name="SniffDetector.harp", messages=MESSAGES):
    folder = tmp_path / name
    folder.mkdir()
    (folder / "device.yml").write_text(SCHEMA)
    (folder / "SniffDetector__32.bin").write_bytes(b"".join(message(*m) for m in messages))
    return folder


def harp(tmp_path, **options):
    return HarpSource(tmp_path, session_id="s001", reference_clock=HARP, **options)


def test_a_device_is_named_by_its_schema(tmp_path):
    acquisition(tmp_path)
    (row,) = harp(tmp_path).devices()
    assert (row["device_id"], row["device_name"], row["model"]) == ("SniffDetector", "SniffDetector", "Harp 1401")


def test_a_prefix_reaches_the_device_id_and_its_name(tmp_path):
    """Part 02 §8.2: the name is what the ID is minted from, prefix included."""
    acquisition(tmp_path)
    (row,) = harp(tmp_path, prefix="A_").devices()
    assert (row["device_id"], row["device_name"]) == ("A_SniffDetector", "A_SniffDetector")


def test_a_register_is_its_events_on_exact_ticks(tmp_path):
    """Seconds 10 is tick 312,500; the write between the first two events is dropped."""
    acquisition(tmp_path)
    (staged,) = harp(tmp_path, signals=["RawVoltage"]).staged_arrays()
    assert staged.array_asset_id == "sniff_detector_raw_voltage"
    assert staged.values.tolist() == [900, 910, 905]
    anchors = harp(tmp_path, signals=["RawVoltage"]).signal_anchors(every=2)
    assert [(a["t_tick"], a["parent_tick"]) for a in anchors] == [(0, 312_500), (2, 312_657)]


def test_a_signal_is_regular_on_its_dispatch_clock(tmp_path):
    """Two intervals over 157 ticks is 31250 * 2 / 157 Hz, parented to the reference clock."""
    acquisition(tmp_path)
    records = harp(tmp_path, signals=["RawVoltage"]).records()
    (clock,) = records["core.clocks"]
    assert clock["clock_id"] == "sniff_detector_raw_voltage.dispatch"
    assert clock["parent_clock_id"] == "harp"
    assert clock["tick_rate_hz"] == pytest.approx(31250 * 2 / 157, abs=1e-6)
    (asset,) = records["core.array_assets"]
    assert (asset["device_id"], asset["resource_id"]) == ("SniffDetector", "core.sniff_detector_raw_voltage")
    (axis,) = records["core.array_dimensions"]
    assert (axis["origin_tick"], axis["step_tick_num"]) == (0, 1)
    # Anchored, so it declares the window it counted: its three samples.
    (window,) = records["core.clock_observation_intervals"]
    assert (window["clock_id"], window["start_tick"], window["stop_tick"]) == (clock["clock_id"], 0, 2)


def test_no_signal_reads_no_register(tmp_path):
    acquisition(tmp_path)
    assert set(harp(tmp_path).records()) == {"core.devices"}


def test_an_empty_run_is_passed_over(tmp_path):
    """A run stopped before streaming leaves the register file empty, and the other run is read."""
    acquisition(tmp_path, "a.harp", messages=[])
    acquisition(tmp_path, "b.harp")
    (staged,) = harp(tmp_path, signals=["RawVoltage"]).staged_arrays()
    assert len(staged.values) == 3


def test_a_register_in_two_runs_is_refused(tmp_path):
    acquisition(tmp_path, "a.harp")
    acquisition(tmp_path, "b.harp")
    with pytest.raises(SourceDefect) as refused:
        harp(tmp_path, signals=["RawVoltage"]).staged_arrays()
    assert refused.value.code == SourceFault.SIGNAL_SPLIT


def test_an_undeclared_register_is_refused(tmp_path):
    acquisition(tmp_path)
    with pytest.raises(SourceDefect) as refused:
        harp(tmp_path, signals=["Thermistor"]).staged_arrays()
    assert refused.value.code == SourceFault.SIGNAL_ABSENT


def test_values_keep_the_registers_type(tmp_path):
    acquisition(tmp_path)
    (staged,) = harp(tmp_path, signals=["RawVoltage"]).staged_arrays()
    assert staged.values.dtype == np.uint16


def test_devices_need_no_clock_and_signals_do(tmp_path):
    acquisition(tmp_path)
    assert len(HarpSource(tmp_path, session_id="s001").devices()) == 1
    with pytest.raises(UsageError) as refused:
        HarpSource(tmp_path, session_id="s001", signals=["RawVoltage"])
    assert refused.value.code == UsageFault.SIGNALS_WITHOUT_CLOCK
