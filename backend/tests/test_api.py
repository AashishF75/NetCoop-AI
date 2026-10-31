"""
API Integration Tests for FastAPI Application.
Verifies:
- GET /api/health
- GET /api/topology
- GET /api/scenarios
- GET /api/scenarios/{id}/telemetry
- GET /api/scenarios/{id}/export (JSON and CSV)
- POST /api/protocol/validate-message
- POST /api/diagnose (Scenario execution, raw CSV upload, schema mismatch handling)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ONLINE"
    assert len(data["agents_registered"]) == 5


def test_api_topology():
    res = client.get("/api/topology")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) >= 6


def test_api_scenarios_list():
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) == 8


def test_api_scenario_telemetry():
    res = client.get("/api/scenarios/link_congestion/telemetry")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] > 0
    assert len(data["telemetry"]) > 0


def test_api_scenario_export_json_and_csv():
    # JSON export
    res_json = client.get("/api/scenarios/interface_fault/export?format=json")
    assert res_json.status_code == 200
    assert "application/json" in res_json.headers["content-type"]

    # CSV export
    res_csv = client.get("/api/scenarios/interface_fault/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "device_id" in res_csv.text


def test_api_protocol_validation():
    # Valid message
    valid_msg = {
        "agent_id": "perf-agent-01",
        "message_type": "TELEMETRY_ANOMALY",
        "schema_version": "1.0.0",
        "metric": "latency_ms",
        "value": 120.0,
        "confidence": 0.88,
        "findings": ["High latency"],
    }
    res = client.post("/api/protocol/validate-message", json={"message": valid_msg})
    assert res.status_code == 200
    assert res.json()["valid"] is True

    # Incompatible schema version
    bad_msg = {
        "agent_id": "perf-agent-01",
        "message_type": "TELEMETRY_ANOMALY",
        "schema_version": "0.7.0",
    }
    res = client.post("/api/protocol/validate-message", json={"message": bad_msg})
    assert res.status_code == 200
    assert res.json()["valid"] is False
    assert res.json()["error_type"] == "SCHEMA_VERSION_MISMATCH"


def test_api_diagnose_scenario_link_congestion():
    res = client.post("/api/diagnose", json={"scenario_id": "link_congestion"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["CONFIRMED", "SUSPECTED"]
    assert "Congestion" in data["suspected_root_cause"]
    assert len(data["message_bus"]) > 5
    assert len(data["agent_states"]) == 5
    assert "canonical_report" in data


def test_api_diagnose_incompatible_schema_scenario():
    res = client.post("/api/diagnose", json={"scenario_id": "incompatible_agent_messages"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "INCONCLUSIVE"
    assert "Protocol Interoperability Rejection" in data["suspected_root_cause"]
    assert any(m["message_type"] == "SCHEMA_VERSION_MISMATCH" for m in data["message_bus"])


def test_api_diagnose_raw_csv_ingestion():
    csv_raw = """device_id,latency_ms,packet_loss_pct,cpu_utilization_pct,queue_drops_per_sec
Core-Router-01,150.0,8.0,30.0,95.0
Agg-Switch-01,148.0,7.5,28.0,90.0
"""
    res = client.post("/api/diagnose", json={"raw_content": csv_raw, "data_format": "csv"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["CONFIRMED", "SUSPECTED"]
