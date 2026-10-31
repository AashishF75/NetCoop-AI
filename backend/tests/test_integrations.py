"""
Comprehensive Automated Tests for Live Network Integrations.
Validates security controls (redaction, IP validation, anti-scan),
probe adapters, syslog ingestion, and end-to-end live diagnosis execution.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient

from app.main import app
from app.integrations.models import (
    SourceType,
    AuthType,
    ConnectionStatus,
    NetworkSourceConfig,
    validate_target_host,
    SourceCreateRequest,
)
from app.integrations.manager import get_integration_manager
from app.integrations.adapters.ping_probe import PingProbeAdapter
from app.integrations.adapters.server_metrics import ServerMetricsAdapter
from app.integrations.adapters.syslog_adapter import SyslogAdapter
from app.integrations.adapters.csv_json_adapter import FileImportAdapter


client = TestClient(app)


def test_ip_validation_and_anti_scanning_rules():
    """Verifies that CIDR masks, subnets, and malicious shell chars are strictly rejected."""
    # Valid targets
    assert validate_target_host("192.168.1.1") == "192.168.1.1"
    assert validate_target_host("127.0.0.1") == "127.0.0.1"
    assert validate_target_host("router.core.netcoop.internal") == "router.core.netcoop.internal"

    # Rejection of CIDR subnet scanning
    with pytest.raises(ValueError, match="Subnet CIDR notation is rejected"):
        validate_target_host("192.168.1.0/24")

    with pytest.raises(ValueError, match="Subnet CIDR notation is rejected"):
        validate_target_host("10.0.0.0/8")

    # Rejection of wildcards and shell injection characters
    with pytest.raises(ValueError, match="illegal characters or wildcards"):
        validate_target_host("192.168.1.*")

    with pytest.raises(ValueError, match="illegal characters or wildcards"):
        validate_target_host("127.0.0.1; reboot")

    with pytest.raises(ValueError, match="Host cannot be empty"):
        validate_target_host("   ")


def test_credential_redaction():
    """Verifies write-only credentials are never exposed in public models."""
    cfg = NetworkSourceConfig(
        id="test-secure-source",
        name="Secure Cisco Gateway",
        source_type=SourceType.REST_API,
        host="10.10.10.1",
        port=443,
        auth_type=AuthType.BASIC_AUTH,
        username="netadmin",
        password="SuperSecretPassword!123",
        api_key="api-token-xyz-secret",
        community_string="snmp-private-string",
    )

    public_view = cfg.to_public()

    # Public projection must have credentials redacted
    assert not hasattr(public_view, "password")
    assert not hasattr(public_view, "api_key")
    assert not hasattr(public_view, "community_string")
    assert public_view.has_credentials is True
    assert public_view.host == "10.10.10.1"
    assert public_view.id == "test-secure-source"


@pytest.mark.asyncio
async def test_server_metrics_adapter_real_counters():
    """Tests that ServerMetricsAdapter reads real OS kernel counters."""
    cfg = NetworkSourceConfig(
        id="test-host-metric",
        name="Local Server",
        source_type=SourceType.SERVER_HOST,
        host="127.0.0.1",
        port=80,
    )
    adapter = ServerMetricsAdapter(cfg)
    test_res = await adapter.test_connection()
    assert test_res.success is True
    assert test_res.status in [ConnectionStatus.CONNECTED, ConnectionStatus.DEGRADED]

    records = await adapter.collect_telemetry()
    assert len(records) >= 1
    rec = records[0]
    assert rec.cpu_utilization_pct is not None
    assert 0.0 <= rec.cpu_utilization_pct <= 100.0
    assert rec.memory_utilization_pct is not None
    assert 0.0 <= rec.memory_utilization_pct <= 100.0
    assert rec.telemetry_origin == "LIVE"


@pytest.mark.asyncio
async def test_ping_probe_adapter_live_socket():
    """Tests active non-blocking socket reachability against localhost."""
    cfg = NetworkSourceConfig(
        id="test-ping-probe",
        name="Localhost Probe",
        source_type=SourceType.PING_PROBE,
        host="127.0.0.1",
        port=80,
        timeout_sec=0.5,
    )
    adapter = PingProbeAdapter(cfg)
    result = await adapter.test_connection()
    assert result.source_id == "test-ping-probe"
    assert result.status in [ConnectionStatus.CONNECTED, ConnectionStatus.DISCONNECTED, ConnectionStatus.DEGRADED]
    assert result.packet_loss_pct is not None


@pytest.mark.asyncio
async def test_syslog_ingestion_and_normalization():
    """Tests syslog event parsing into canonical TelemetryRecord items."""
    cfg = NetworkSourceConfig(
        id="test-syslog",
        name="Syslog Test",
        source_type=SourceType.SYSLOG,
        host="127.0.0.1",
    )
    adapter = SyslogAdapter(cfg)
    adapter.ingest_message("%LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down")
    adapter.ingest_message("%DUND-4-DUPLEX: Duplex mismatch detected on FastEthernet0/1")
    adapter.ingest_message("%SYS-1-CPURISINGTHRESHOLD: High CPU utilization detected: 94% in last 5 minutes")

    records = await adapter.collect_telemetry()
    assert len(records) >= 3
    assert any(r.packet_loss_pct == 100.0 for r in records)
    assert any(r.interface_crc_errors == 145 for r in records)
    assert any(r.cpu_utilization_pct == 94.0 for r in records)
    for r in records:
        assert r.telemetry_origin == "LIVE"


@pytest.mark.asyncio
async def test_custom_import_adapter():
    """Tests CSV / JSON manual import adapter tagging with CUSTOM_IMPORT."""
    cfg = NetworkSourceConfig(
        id="test-custom-import",
        name="Manual Import",
        source_type=SourceType.CSV_IMPORT,
        host="127.0.0.1",
    )
    csv_data = "device_id,latency_ms,packet_loss_pct\nRouter-X,42.5,3.1"
    adapter = FileImportAdapter(cfg, content=csv_data)
    records = await adapter.collect_telemetry()
    assert len(records) == 1
    assert records[0].telemetry_origin == "CUSTOM_IMPORT"
    assert records[0].device_id == "Router-X"
    assert records[0].latency_ms == 42.5
    assert records[0].packet_loss_pct == 3.1


def test_api_list_sources():
    """Tests GET /api/integrations/sources returns safe redacted list."""
    resp = client.get("/api/integrations/sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert isinstance(sources, list)
    assert len(sources) >= 1
    for s in sources:
        assert "password" not in s
        assert "community_string" not in s
        assert "has_credentials" in s


def test_api_create_and_delete_source():
    """Tests registering and removing a source via REST API."""
    payload = {
        "name": "Branch Office Ping Probe",
        "source_type": "PING_PROBE",
        "host": "127.0.0.1",
        "port": 8080,
        "polling_interval_sec": 20,
    }
    create_resp = client.post("/api/integrations/sources", json=payload)
    assert create_resp.status_code == 200
    created = create_resp.json()
    source_id = created["id"]
    assert created["name"] == "Branch Office Ping Probe"
    assert created["host"] == "127.0.0.1"

    # Delete source
    del_resp = client.delete(f"/api/integrations/sources/{source_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Confirm 404
    get_resp = client.get(f"/api/integrations/sources/{source_id}")
    assert get_resp.status_code == 404


def test_api_source_connection_test():
    """Tests live connection test endpoint."""
    resp = client.post("/api/integrations/sources/src-server-host/test")
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["success"] is True
    assert res_data["status"] in ["CONNECTED", "DEGRADED"]
    assert "Host metrics live" in res_data["message"]


def test_api_source_poll():
    """Tests live polling endpoint."""
    resp = client.post("/api/integrations/sources/src-server-host/poll")
    assert resp.status_code == 200
    poll_data = resp.json()
    assert poll_data["count"] >= 1
    assert any(r.get("cpu_utilization_pct") is not None for r in poll_data["records"])


def test_api_live_diagnosis_execution():
    """Tests end-to-end multi-agent diagnosis over live network sources."""
    resp = client.post(
        "/api/integrations/diagnose-live",
        json={"source_ids": ["src-server-host"], "timeout_sec": 3.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["telemetry_origin"] in ("LIVE", "LIVE_HOST", "LIVE_DEVICE")
    assert data["records_collected"] >= 1
    assert data["report"] is not None
    assert data["report"]["telemetry_origin"] in ("LIVE", "LIVE_HOST", "LIVE_DEVICE")
    assert "INC-LIVE-" in data["incident_id"]
