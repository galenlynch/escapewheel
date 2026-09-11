"""The acquisition chain `settings.xml` records, and where each link was plugged in."""

import pytest

from escapewheel_writer.sources.openephys import OpenEphysSource

#: Two probes on one basestation and a quad-base on another, which is the shape both packaged
#: sessions have: `slot 7 port 1 dock 1` four times over, one physical probe.
SETTINGS = """<?xml version="1.0"?>
<SETTINGS>
  <SIGNALCHAIN>
    <PROCESSOR name="Neuropix-PXI">
      <EDITOR>
        <NP_PROBE slot="3" port="2" dock="1" custom_probe_name="50198"
                  probe_serial_number="20403319544" probe_part_number="NP1010"
                  bs_part_number="NP2_QBSC" bs_serial_number="0"
                  bs_firmware_version="2.0169" bs_hardware_version="1.0"
                  bsc_part_number="NP2_CONN" bsc_serial_number="0"
                  bsc_firmware_version="3.2189" bsc_hardware_version="2.1"
                  headstage_part_number="NPM_HS_30" headstage_serial_number="0"
                  flex_version="1.8"/>
        <NP_PROBE slot="3" port="4" dock="2" custom_probe_name="50197"
                  probe_serial_number="23176523281" probe_part_number="NP1010"
                  bs_part_number="NP2_QBSC" bs_serial_number="0"
                  bs_firmware_version="2.0169" bs_hardware_version="1.0"
                  bsc_part_number="NP2_CONN" bsc_serial_number="0"
                  bsc_firmware_version="3.2189" bsc_hardware_version="2.1"
                  headstage_part_number="NPM_HS_31" headstage_serial_number="0"
                  flex_version="0.1"/>
        <NP_PROBE slot="7" port="1" dock="1" custom_probe_name="50213-1"
                  probe_serial_number="23207205101" probe_part_number="NP2020"
                  bs_part_number="NP2_QBSC" bs_serial_number="0"
                  bs_firmware_version="2.0169" bs_hardware_version="1.0"
                  bsc_part_number="NP2_CONN" bsc_serial_number="0"
                  bsc_firmware_version="3.2189" bsc_hardware_version="2.1"
                  headstage_part_number="NPM_HS_32" headstage_serial_number="0"
                  flex_version="UNKNOWN"/>
        <NP_PROBE slot="7" port="1" dock="1" custom_probe_name="50213-2"
                  probe_serial_number="23207205101" probe_part_number="NP2020"
                  bs_part_number="NP2_QBSC" bs_serial_number="0"
                  bs_firmware_version="2.0169" bs_hardware_version="1.0"
                  bsc_part_number="NP2_CONN" bsc_serial_number="0"
                  bsc_firmware_version="3.2189" bsc_hardware_version="2.1"
                  headstage_part_number="NPM_HS_32" headstage_serial_number="0"
                  flex_version="UNKNOWN"/>
      </EDITOR>
    </PROCESSOR>
  </SIGNALCHAIN>
</SETTINGS>
"""


@pytest.fixture
def source(tmp_path):
    node = tmp_path / "Record Node 109"
    node.mkdir()
    (node / "settings.xml").write_text(SETTINGS)
    return OpenEphysSource(tmp_path, session_id="s001")


def by_name(rows):
    return {row["device_name"]: row for row in rows}


def test_each_chain_element_that_reports_a_version_is_a_device(source):
    """Part 01 §3.5. Two slots give two basestations and two connect boards; three headstages."""
    rows = by_name(source.devices())
    assert sorted(rows) == [
        "basestation.slot3",
        "basestation.slot7",
        "connect_board.slot3",
        "connect_board.slot7",
        "headstage.slot3.port2",
        "headstage.slot3.port4",
        "headstage.slot7.port1",
    ]


def test_a_headstage_declares_the_port_it_attached_to(source):
    """R85 §2.1. The coordinate the name carries, in a column a consumer may read."""
    rows = by_name(source.devices())
    assert rows["headstage.slot3.port2"]["parent_port"] == "2"
    assert rows["headstage.slot3.port4"]["parent_port"] == "4"
    assert rows["headstage.slot7.port1"]["parent_port"] == "1"


def test_a_link_the_file_gives_no_coordinate_for_leaves_the_port_null(source):
    """R85 §2.1. A connect board has a parent and no stated place on it; a basestation has neither."""
    rows = by_name(source.devices())
    assert rows["connect_board.slot3"]["parent_device_id"] == "basestation.slot3"
    assert rows["connect_board.slot3"]["parent_port"] is None
    assert rows["basestation.slot3"]["parent_device_id"] is None
    assert rows["basestation.slot3"]["parent_port"] is None


def test_a_probe_is_attached_by_the_name_the_nwb_gives_its_device(source):
    """R67 §1.2. `custom_probe_name` joins to the NWB without going through a serial."""
    attached = source.attachments()
    assert attached["50198"] == {"parent_device_id": "headstage.slot3.port2", "parent_port": "1"}
    assert attached["50197"] == {"parent_device_id": "headstage.slot3.port4", "parent_port": "2"}


def test_the_four_bases_of_one_probe_report_one_dock(source):
    """Part 01 §3.5. A port is where something was plugged in, so it cannot tell the four apart."""
    attached = source.attachments()
    assert [attached[f"50213-{base}"] for base in (1, 2)] == [
        {"parent_device_id": "headstage.slot7.port1", "parent_port": "1"}
    ] * 2


def test_a_serial_of_zero_is_a_blank_field_rather_than_a_serial(source):
    """Part 01 §3.5. `UNKNOWN` is a statement and `0` is Open Ephys leaving the field empty."""
    rows = by_name(source.devices())
    assert rows["basestation.slot3"]["serial_number"] is None
    assert rows["headstage.slot7.port1"]["hardware_version"] == "UNKNOWN"
    assert rows["headstage.slot3.port2"]["hardware_version"] == "1.8"


def test_unparseable_settings_are_noted_rather_than_raised(tmp_path):
    """A build reports what it could not read; one bad record node does not lose the others."""
    node = tmp_path / "Record Node 109"
    node.mkdir()
    (node / "settings.xml").write_text("<SETTINGS>")
    source = OpenEphysSource(tmp_path, session_id="s001")
    assert source.devices() == []
    assert "not parseable as XML" in source.notes[0]


def test_the_metadata_bag_does_not_restate_the_port(source):
    """Part 02 §8.6. `parent_port` holds the port, so the bag carrying it too would restate a column."""
    rows = by_name(source.devices())
    assert rows["headstage.slot3.port2"]["metadata"] == {"slot": "3"}
    assert rows["connect_board.slot3"]["metadata"] == {"slot": "3"}
