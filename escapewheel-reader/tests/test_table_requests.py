"""A remote table's footer is read once per handle, and its size asked of the store at most once."""

import json
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from pyarrow import fs as pafs

from escapewheel_reader import ResourceUnreadableError, open_packet, open_packets
from escapewheel_reader import location as location_module

BUCKET = "bench"
PACKET = f"s3://{BUCKET}/session_001"


@pytest.fixture
def store(packet_root, monkeypatch):
    """Serve the packet's directory over S3's HTTP API from a local server, recording each request."""
    requests: list[tuple[str, str]] = []

    class Objects(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def _object(self):
            bucket, _, key = self.path.split("?")[0].lstrip("/").partition("/")
            target = packet_root.parent / key
            return target.read_bytes() if bucket == BUCKET and key and target.is_file() else None

        def _head(self, status, length):
            self.send_response(status)
            self.send_header("Content-Length", str(length))
            self.send_header("Last-Modified", "Mon, 01 Jan 2024 00:00:00 GMT")

        def do_HEAD(self):
            requests.append(("HEAD", self.path))
            body = self._object()
            self._head(404 if body is None else 200, 0 if body is None else len(body))
            self.end_headers()

        def do_GET(self):
            requests.append(("GET", self.path))
            body = self._object()
            if body is None:
                self._head(404, 0)
                self.end_headers()
                return
            if ranged := self.headers.get("Range"):
                start, stop = ranged.removeprefix("bytes=").split("-")
                first = len(body) - int(stop) if start == "" else int(start)
                last = min(int(stop) if start and stop else len(body) - 1, len(body) - 1)
                self._head(206, last - first + 1)
                self.send_header("Content-Range", f"bytes {first}-{last}/{len(body)}")
                body = body[first : last + 1]
            else:
                self._head(200, len(body))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Objects)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    filesystem = pafs.S3FileSystem(
        endpoint_override=f"127.0.0.1:{server.server_port}", scheme="http", anonymous=True, region="us-east-1"
    )
    monkeypatch.setattr(location_module, "_filesystem", lambda where: (filesystem, ""))
    yield requests
    server.shutdown()


def _record_sizes(root):
    manifest = json.loads((root / "packet.json").read_text())
    for entry in manifest["resources"]:
        entry["size_bytes"] = (root / entry["uri"]).stat().st_size
    (root / "packet.json").write_text(json.dumps(manifest))


def _table_requests(requests, packet_root, resource_id="core.intervals"):
    uri = json.loads((packet_root / "packet.json").read_text())
    key = next(r["uri"] for r in uri["resources"] if r["resource_id"] == resource_id)
    return [method for method, path in requests if path.split("?")[0].endswith(f"session_001/{key}")]


def test_a_recorded_size_leaves_the_footer_and_the_data(packet_root, store):
    _record_sizes(packet_root)
    packet = open_packet(PACKET)
    store.clear()
    assert packet.table("core.intervals").num_rows == 2
    assert _table_requests(store, packet_root) == ["GET", "GET"]


def test_the_footer_is_read_once_per_handle(packet_root, store):
    _record_sizes(packet_root)
    packet = open_packet(PACKET)
    store.clear()
    _ = packet.table_resource("core.intervals").schema()
    _ = packet.table("core.intervals")
    _ = packet.table("core.intervals")
    assert _table_requests(store, packet_root) == ["GET", "GET", "GET"]


def test_without_a_recorded_size_the_store_is_asked_once(packet_root, store):
    packet = open_packet(PACKET)
    store.clear()
    _ = packet.table("core.intervals")
    _ = packet.table("core.intervals")
    assert _table_requests(store, packet_root) == ["HEAD", "GET", "GET", "GET"]


def test_a_wrong_recorded_size_names_it(packet_root, store):
    manifest = json.loads((packet_root / "packet.json").read_text())
    entry = next(r for r in manifest["resources"] if r["resource_id"] == "core.intervals")
    entry["size_bytes"] = (packet_root / entry["uri"]).stat().st_size - 1
    (packet_root / "packet.json").write_text(json.dumps(manifest))
    with pytest.raises(ResourceUnreadableError, match="size_bytes"):
        open_packet(PACKET).table("core.intervals")


def test_a_packet_set_reads_each_footer_once_and_asks_no_size(packet_root, tmp_path, store):
    _record_sizes(packet_root)
    second = tmp_path / "session_002"
    shutil.copytree(packet_root, second)
    manifest = json.loads((second / "packet.json").read_text())
    (second / "packet.json").write_text(json.dumps({**manifest, "packet_id": "session_002"}))
    pair = open_packets([PACKET, f"s3://{BUCKET}/session_002"])
    store.clear()
    for _ in range(2):
        assert pair.scan("core.spike_events").to_table().num_rows > 0
    spikes = [method for method, path in store if "spike_events" in path]
    # Per packet: one footer, then one data read per scan.
    assert spikes == ["GET"] * 6
