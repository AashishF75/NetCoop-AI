"""
Comprehensive Automated Tests for On-Premise Collector Subsystem.
Validates enrollment tokens, pairing handshakes, session token revocation,
anti-scan validation, telemetry ingestion, stale data handling, and live diagnosis.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.integrations.collector_hub import get_collector_hub, DeviceConnectionStatus, CollectorStatus
from app.protocol.schema import TelemetryRecord
from collector.config import LocalDeviceConfig, DeviceProtocol
from collector.adapters.reachability_probe import probe_tcp_reachability
from collector.adapters.syslog_receiver import SyslogServer
from collector.adapters.host_metrics import poll_host_metrics

client = TestClient(app)


def test_collector_enrollment_token_generation():
    """Tests generating an enrollment token and pairing commands."""
    resp = client.post("/api/collectors/enroll", json={"name": "Test-Site-Collector"})
    assert resp.status_code == 200
    data = resp.json()
    assert "enrollment_token" in data
    assert data["enrollment_token"].startswith("nc_coll_")
    assert "collector_id" in data
    assert "pairing_command_windows" in data
    assert "pairing_command_linux" in data
    assert data["name"] == "Test-Site-Collector"
    assert ":5173" not in data["pairing_command_windows"]
    assert ":5173" not in data["pairing_command_linux"]


def test_collector_pairing_command_backend_url_resolution():
    """
    Tests that pairing commands resolve to the correct backend API base URL:
    1. If a frontend passes port 5173, the backend replaces it with port 8000.
    2. If cloud Render backend is configured, it is preserved.
    """
    # Test 1: Vite dev port 5173 is corrected to port 8000
    resp_local = client.post(
        "/api/collectors/enroll",
        json={"name": "Local-Dev-Collector", "backend_url": "http://localhost:5173"},
    )
    assert resp_local.status_code == 200
    data_local = resp_local.json()
    assert ":5173" not in data_local["pairing_command_windows"]
    assert "--backend http://localhost:8000" in data_local["pairing_command_windows"]
    assert "--backend http://localhost:8000" in data_local["pairing_command_linux"]

    # Test 2: Production Render cloud deployment URL is preserved
    resp_render = client.post(
        "/api/collectors/enroll",
        json={"name": "Cloud-Collector", "backend_url": "https://netcoop-ai-backend.onrender.com"},
    )
    assert resp_render.status_code == 200
    data_render = resp_render.json()
    assert "--backend https://netcoop-ai-backend.onrender.com" in data_render["pairing_command_windows"]


def test_collector_pairing_handshake_and_authentication():
    """Tests collector registration handshake using enrollment token."""
    # 1. Enroll
    enroll_resp = client.post("/api/collectors/enroll", json={"name": "Handshake-Collector"})
    enroll_data = enroll_resp.json()
    col_id = enroll_data["collector_id"]
    token = enroll_data["enrollment_token"]

    # 2. Handshake with wrong token -> 403
    bad_resp = client.post(
        "/api/collectors/register",
        json={
            "collector_id": col_id,
            "enrollment_token": "nc_coll_invalid_token",
            "hostname": "local-box",
            "local_ip": "192.168.1.50",
            "os_type": "Windows 11",
        },
    )
    assert bad_resp.status_code == 403

    # 3. Handshake with valid token -> 200 and session token
    ok_resp = client.post(
        "/api/collectors/register",
        json={
            "collector_id": col_id,
            "enrollment_token": token,
            "hostname": "local-box",
            "local_ip": "192.168.1.50",
            "os_type": "Windows 11",
        },
    )
    assert ok_resp.status_code == 200
    reg_data = ok_resp.json()
    assert "session_token" in reg_data
    assert reg_data["session_token"].startswith("nc_sess_")

    # 4. Heartbeat with session token
    sess_token = reg_data["session_token"]
    hb_resp = client.post(
        "/api/collectors/heartbeat",
        json={"collector_id": col_id, "session_token": sess_token, "active_device_count": 2},
    )
    assert hb_resp.status_code == 200
    assert hb_resp.json()["status"] == "ACK"

    # 5. Heartbeat with bad session token -> 401
    bad_hb = client.post(
        "/api/collectors/heartbeat",
        json={"collector_id": col_id, "session_token": "nc_sess_invalid", "active_device_count": 0},
    )
    assert bad_hb.status_code == 401


def test_collector_registration_with_stale_config_or_generic_id():
    """
    Regression Test:
    When a user executes the collector from a terminal where a previous collector config
    exists (or where --collector-id was omitted and defaulted to a generic ID), the client
    sends a stale collector_id along with the fresh enrollment_token.
    Verifies that:
    1. The backend matches the unique enrollment token without 403 failure.
    2. The backend responds with HTTP 200 and the canonical collector_id.
    3. Session credentials are created and subsequent heartbeats succeed.
    4. An invalid enrollment token is properly rejected with HTTP 403.
    """
    # 1. Create an existing collector record that simulates an older pairing
    old_enroll = client.post("/api/collectors/enroll", json={"name": "Pre-Existing-Collector"}).json()
    old_id = old_enroll["collector_id"]

    # 2. Enroll a fresh collector
    fresh_enroll = client.post("/api/collectors/enroll", json={"name": "New-Edge-Probe"}).json()
    fresh_id = fresh_enroll["collector_id"]
    fresh_token = fresh_enroll["enrollment_token"]

    # Both pairing commands must contain the exact collector ID
    assert f"--collector-id {fresh_id}" in fresh_enroll["pairing_command_windows"]
    assert f"--collector-id {fresh_id}" in fresh_enroll["pairing_command_linux"]

    # 3. Simulate client sending the OLD/STALE collector_id with the FRESH token
    stale_id_resp = client.post(
        "/api/collectors/register",
        json={
            "collector_id": old_id,  # Stale ID from prior run
            "enrollment_token": fresh_token,  # Fresh token
            "hostname": "field-laptop",
            "local_ip": "10.0.0.99",
            "os_type": "Windows 11",
        },
    )
    assert stale_id_resp.status_code == 200
    stale_id_data = stale_id_resp.json()
    assert stale_id_data["success"] is True
    # Canonical collector_id returned must match the fresh enrolled collector
    assert stale_id_data["collector_id"] == fresh_id
    assert stale_id_data["session_token"].startswith("nc_sess_")

    # 4. Heartbeat using the canonical ID and session token must succeed
    hb_resp = client.post(
        "/api/collectors/heartbeat",
        json={
            "collector_id": fresh_id,
            "session_token": stale_id_data["session_token"],
            "active_device_count": 1,
        },
    )
    assert hb_resp.status_code == 200
    assert hb_resp.json()["status"] == "ACK"

    # 5. Invalid token must be rejected with 403 Forbidden
    invalid_resp = client.post(
        "/api/collectors/register",
        json={
            "collector_id": "col-arbitrary",
            "enrollment_token": "nc_coll_invalid_random_token_999",
            "hostname": "field-laptop",
            "local_ip": "10.0.0.99",
            "os_type": "Windows 11",
        },
    )
    assert invalid_resp.status_code == 403
    assert "Invalid enrollment token" in invalid_resp.json()["detail"]


def test_collector_token_expiration():
    """
    Verifies that an expired enrollment token is rejected with HTTP 403.
    """
    hub = get_collector_hub()
    enroll = client.post("/api/collectors/enroll", json={"name": "Expiring-Collector"}).json()
    cid = enroll["collector_id"]
    token = enroll["enrollment_token"]

    # Artificially expire the token in the hub
    col = hub.get_collector(cid)
    assert col is not None
    col.expires_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    hub._save_state()

    # Registration must now fail with 403
    expired_resp = client.post(
        "/api/collectors/register",
        json={
            "collector_id": cid,
            "enrollment_token": token,
            "hostname": "field-laptop",
            "local_ip": "10.0.0.99",
            "os_type": "Windows 11",
        },
    )
    assert expired_resp.status_code == 403
    assert "expired" in expired_resp.json()["detail"].lower()


def test_collector_revocation_lifecycle():
    """Tests revoking a collector and ensuring subsequent requests are blocked."""
    enroll_resp = client.post("/api/collectors/enroll", json={"name": "Revocable-Collector"})
    enroll_data = enroll_resp.json()
    col_id = enroll_data["collector_id"]
    token = enroll_data["enrollment_token"]

    reg_resp = client.post(
        "/api/collectors/register",
        json={
            "collector_id": col_id,
            "enrollment_token": token,
            "hostname": "host",
            "local_ip": "10.0.0.5",
            "os_type": "Linux",
        },
    )
    sess_token = reg_resp.json()["session_token"]

    # Revoke collector
    rev_resp = client.post(f"/api/collectors/{col_id}/revoke")
    assert rev_resp.status_code == 200

    # Heartbeat must now be rejected
    hb_resp = client.post(
        "/api/collectors/heartbeat",
        json={"collector_id": col_id, "session_token": sess_token, "active_device_count": 0},
    )
    assert hb_resp.status_code == 401

    # Telemetry push must be rejected
    telem_resp = client.post(
        "/api/collectors/telemetry",
        json={
            "collector_id": col_id,
            "session_token": sess_token,
            "device_id": "Router-X",
            "records": [],
        },
    )
    assert telem_resp.status_code == 401


def test_anti_scanning_validation_on_device_registration():
    """Tests that registering devices on collectors strictly rejects CIDR masks and scan ranges."""
    enroll_resp = client.post("/api/collectors/enroll", json={"name": "AntiScan-Collector"})
    col_id = enroll_resp.json()["collector_id"]

    # Valid IP
    ok_dev = client.post(
        f"/api/collectors/{col_id}/devices",
        json={
            "device_id": "Core-Router",
            "name": "Core Router",
            "device_type": "router",
            "ip": "192.168.1.1",
            "port": 80,
            "protocol": "TCP_PROBE",
        },
    )
    assert ok_dev.status_code == 200

    # CIDR mask notation must be rejected
    cidr_dev = client.post(
        f"/api/collectors/{col_id}/devices",
        json={
            "device_id": "Subnet-Scan",
            "name": "Scan",
            "device_type": "router",
            "ip": "192.168.1.0/24",
            "port": 80,
            "protocol": "TCP_PROBE",
        },
    )
    assert cidr_dev.status_code == 400
    assert "Subnet CIDR notation is rejected" in cidr_dev.json()["detail"]


def test_telemetry_push_and_provenance_tagging():
    """Tests pushing live telemetry from collector and verifying LIVE_DEVICE origin."""
    enroll_resp = client.post("/api/collectors/enroll", json={"name": "Telemetry-Collector"})
    col_id = enroll_resp.json()["collector_id"]
    token = enroll_resp.json()["enrollment_token"]

    reg_resp = client.post(
        "/api/collectors/register",
        json={
            "collector_id": col_id,
            "enrollment_token": token,
            "hostname": "collector-box",
            "local_ip": "192.168.1.100",
            "os_type": "Linux",
        },
    )
    sess_token = reg_resp.json()["session_token"]

    telemetry_records = [
        {
            "device_id": "LAN-Router-01",
            "device_type": "router",
            "device_status": "UP",
            "latency_ms": 1.45,
            "packet_loss_pct": 0.0,
            "interface_crc_errors": 0,
            "cpu_utilization_pct": 42.0,
        }
    ]

    push_resp = client.post(
        "/api/collectors/telemetry",
        json={
            "collector_id": col_id,
            "session_token": sess_token,
            "device_id": "LAN-Router-01",
            "records": telemetry_records,
            "metrics_available": ["latency_ms", "packet_loss_pct", "cpu_utilization_pct"],
            "metrics_unsupported": ["wifi_rssi_dbm"],
        },
    )
    assert push_resp.status_code == 200
    assert push_resp.json()["ingested_records"] == 1

    # Verify inventory reflects live status
    inv_resp = client.get("/api/collectors/inventory")
    assert inv_resp.status_code == 200
    inv = inv_resp.json()
    device = next((d for d in inv["devices"] if d["device_id"] == "LAN-Router-01"), None)
    assert device is not None
    assert device["status"] == "STREAMING_LIVE"
    assert "cpu_utilization_pct" in device["metrics_available"]
    assert "wifi_rssi_dbm" in device["metrics_unsupported"]


def test_live_diagnosis_with_collector_telemetry_no_synthetic_fallback():
    """Tests that live diagnosis consumes real collector records with LIVE_DEVICE provenance."""
    hub = get_collector_hub()
    hub._telemetry_cache.clear()

    # When no telemetry is available, diagnose-live must return error or fallback to host probe, NOT synthetic data
    resp_empty = client.post("/api/integrations/diagnose-live", json={})
    # Must succeed with host probe or return error, but NEVER claim LIVE_DEVICE
    if resp_empty.status_code == 200:
        data = resp_empty.json()
        assert data["telemetry_origin"] in ["LIVE_HOST", "LIVE"]
        assert data["telemetry_origin"] != "LIVE_DEVICE"

    # Inject real collector telemetry
    enroll_resp = client.post("/api/collectors/enroll", json={"name": "Diagnosis-Collector"})
    col_id = enroll_resp.json()["collector_id"]
    token = enroll_resp.json()["enrollment_token"]

    reg_resp = client.post(
        "/api/collectors/register",
        json={
            "collector_id": col_id,
            "enrollment_token": token,
            "hostname": "lan-box",
            "local_ip": "10.0.0.1",
            "os_type": "Windows",
        },
    )
    sess_token = reg_resp.json()["session_token"]

    client.post(
        "/api/collectors/telemetry",
        json={
            "collector_id": col_id,
            "session_token": sess_token,
            "device_id": "LAN-Core-Router",
            "records": [
                {
                    "device_id": "LAN-Core-Router",
                    "device_type": "router",
                    "device_status": "UP",
                    "latency_ms": 2.1,
                    "packet_loss_pct": 0.0,
                    "cpu_utilization_pct": 28.0,
                }
            ],
        },
    )

    # Now diagnose-live must prioritize the live collector device
    diag_resp = client.post("/api/integrations/diagnose-live", json={})
    assert diag_resp.status_code == 200
    diag_data = diag_resp.json()
    assert diag_data["success"] is True
    assert diag_data["telemetry_origin"] == "LIVE_DEVICE"
    assert "LAN-Core-Router" in diag_data["devices_polled"]
    assert "INC-LIVE-" in diag_data["incident_id"]


@pytest.mark.asyncio
async def test_reachability_probe_adapter():
    """Tests collector's TCP reachability probe adapter."""
    dev = LocalDeviceConfig(
        device_id="Test-Probe-Target",
        name="Test Target",
        host="127.0.0.1",
        port=80,
        protocol=DeviceProtocol.TCP_PROBE,
        timeout_sec=0.5,
    )
    records, avail, unsupp = await probe_tcp_reachability(dev)
    assert len(records) == 1
    assert records[0].telemetry_origin == "LIVE_DEVICE"
    assert "latency_ms" in avail
    assert "cpu_utilization_pct" in unsupp
    assert records[0].custom_metrics["probe_type"] == "TCP_SOCKET_CONNECT"


def test_syslog_server_parser():
    """Tests collector's local syslog parser handling router messages."""
    server = SyslogServer(port=5140)
    server.handle_syslog_line(
        "<189>120: Core-Router-HQ: %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down",
        "192.168.1.1",
    )
    server.handle_syslog_line(
        "<189>121: Core-Router-HQ: %SYS-1-CPURISINGTHRESHOLD: High CPU utilization detected: 96% in last 5 minutes",
        "192.168.1.1",
    )

    recs = server.drain_records()
    assert len(recs) == 2
    assert any(r.packet_loss_pct == 100.0 for r in recs)
    assert any(r.cpu_utilization_pct == 96.0 for r in recs)
    for r in recs:
        assert r.telemetry_origin == "LIVE_DEVICE"


@pytest.mark.asyncio
async def test_host_metrics_adapter():
    """Tests collector's native host OS metrics adapter for authentic CPU and memory counters."""
    dev = LocalDeviceConfig(
        device_id="HOST-TEST-01",
        name="Host Appliance Test",
        host="127.0.0.1",
        port=8000,
        protocol=DeviceProtocol.HOST_METRICS,
        timeout_sec=1.0,
    )
    records, avail, unsupp = await poll_host_metrics(dev)
    assert len(records) == 1
    rec = records[0]
    assert rec.telemetry_origin == "LIVE_HOST"
    assert rec.device_type == "server"
    assert 0.0 <= rec.cpu_utilization_pct <= 100.0
    assert 0.0 <= rec.memory_utilization_pct <= 100.0
    assert "cpu_utilization_pct" in avail
    assert "memory_utilization_pct" in avail
    assert "wifi_rssi_dbm" in unsupp


def test_collector_host_telemetry_provenance_and_diagnosis():
    """
    Tests that host telemetry pushed by collector maintains LIVE_HOST provenance
    throughout the 5-agent diagnosis pipeline.
    """
    # 1. Enroll and pair collector
    enroll_resp = client.post("/api/collectors/enroll", json={"name": "Host-Collector"})
    col_id = enroll_resp.json()["collector_id"]
    token = enroll_resp.json()["enrollment_token"]

    reg_resp = client.post(
        "/api/collectors/register",
        json={
            "collector_id": col_id,
            "enrollment_token": token,
            "hostname": "collector-host-box",
            "local_ip": "127.0.0.1",
            "os_type": "Windows 11",
        },
    )
    sess_token = reg_resp.json()["session_token"]

    # 2. Push genuine host telemetry record
    hub = get_collector_hub()
    hub._telemetry_cache.clear()
    now_iso = datetime.now(timezone.utc).isoformat()
    host_record = TelemetryRecord(
        timestamp=now_iso,
        device_id="HOST-BOX-APP-01",
        device_type="server",
        device_status="UP",
        cpu_utilization_pct=42.5,
        memory_utilization_pct=65.2,
        latency_ms=0.8,
        packet_loss_pct=0.0,
        telemetry_origin="LIVE_HOST",
        custom_metrics={"os": "Windows 11"},
    )

    push_resp = client.post(
        "/api/collectors/telemetry",
        json={
            "collector_id": col_id,
            "session_token": sess_token,
            "device_id": "HOST-BOX-APP-01",
            "records": [host_record.model_dump()],
            "metrics_available": ["cpu_utilization_pct", "memory_utilization_pct"],
        },
    )
    assert push_resp.status_code == 200

    # 3. Execute live diagnosis
    diag_resp = client.post("/api/integrations/diagnose-live", json={})
    assert diag_resp.status_code == 200
    diag_data = diag_resp.json()
    assert diag_data["success"] is True
    assert diag_data["telemetry_origin"] == "LIVE_HOST"
    assert "HOST-BOX-APP-01" in diag_data["devices_polled"]


