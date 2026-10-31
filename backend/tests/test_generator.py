"""
Unit and Integration Tests for Official Problem-Statement Telemetry Generator.
Verifies:
1. Exact generator code, random metric ranges, statuses, and device IDs.
2. Validation rules against the official schema specifications.
3. Canonical record adapter and strict 'GENERATED_TEST' telemetry provenance.
4. Multi-agent diagnostic pipeline behavior across Normal, Latency Spike, and Hardware Failure modes.
5. Absolute isolation between generated test telemetry and live router telemetry.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.generator.telemetry_generator import (
    generate_telemetry,
    validate_generated_payload,
    adapt_to_canonical_record,
    VALID_FAULT_TYPES,
)
from app.protocol.normalizer import TelemetryNormalizer
from app.protocol.schema import TelemetryRecord, DiagnosticStatus
from app.integrations.collector_hub import get_collector_hub

client = TestClient(app)


# =============================================================================
# 1. GENERATOR SPECIFICATION & RANGE TESTS
# =============================================================================

def test_generate_telemetry_normal_spec():
    """Validates that 'normal' telemetry strictly adheres to official spec."""
    data = generate_telemetry("normal")
    
    assert data["device_id"].startswith("SW_CAMPUS_")
    dev_num = int(data["device_id"].split("_")[-1])
    assert 1 <= dev_num <= 10
    assert data["status"] == "Healthy"
    assert "timestamp" in data
    
    # ISO timestamp check
    parsed_ts = datetime.fromisoformat(data["timestamp"])
    assert parsed_ts is not None
    
    m = data["metrics"]
    assert 10.0 <= m["cpu_utilization"] <= 35.0
    assert 20.0 <= m["link_utilization_pct"] <= 50.0
    assert m["packet_loss_pct"] == 0.0
    assert 5.0 <= m["latency_ms"] <= 20.0
    assert 1.0 <= m["jitter_ms"] <= 5.0
    assert m["queue_drops"] == 0


def test_generate_telemetry_latency_spike_spec():
    """Validates that 'latency_spike' telemetry strictly adheres to official spec."""
    data = generate_telemetry("latency_spike")
    
    assert data["device_id"].startswith("SW_CAMPUS_")
    dev_num = int(data["device_id"].split("_")[-1])
    assert 1 <= dev_num <= 10
    assert data["status"] == "Warning"
    assert "timestamp" in data
    
    m = data["metrics"]
    assert 40.0 <= m["cpu_utilization"] <= 70.0
    assert 60.0 <= m["link_utilization_pct"] <= 85.0
    assert 0.1 <= m["packet_loss_pct"] <= 1.5
    assert 150.0 <= m["latency_ms"] <= 400.0
    assert 30.0 <= m["jitter_ms"] <= 80.0
    assert 0 <= m["queue_drops"] <= 50


def test_generate_telemetry_hardware_failure_spec():
    """Validates that 'hardware_failure' telemetry strictly adheres to official spec."""
    data = generate_telemetry("hardware_failure")
    
    assert data["device_id"].startswith("SW_CAMPUS_")
    dev_num = int(data["device_id"].split("_")[-1])
    assert 1 <= dev_num <= 10
    assert data["status"] == "Critical"
    assert "timestamp" in data
    
    m = data["metrics"]
    assert m["cpu_utilization"] == 99.9
    assert m["link_utilization_pct"] == 100
    assert 15.0 <= m["packet_loss_pct"] <= 30.0
    assert 500.0 <= m["latency_ms"] <= 1000.0
    assert 5000 <= m["queue_drops"] <= 15000
    assert 100 <= m["interface_errors"] <= 500


def test_generate_telemetry_default_behavior():
    """Ensures unrecognized fault types fall back safely to normal per the problem statement."""
    data = generate_telemetry("unspecified_mode")
    assert data["status"] == "Healthy"
    assert data["metrics"]["packet_loss_pct"] == 0.0


# =============================================================================
# 2. VALIDATION ENGINE TESTS
# =============================================================================

def test_validate_generated_payload_all_valid():
    """Ensures all generated outputs pass validation."""
    for fault in VALID_FAULT_TYPES:
        sample = generate_telemetry(fault)
        valid, err = validate_generated_payload(sample)
        assert valid is True, f"Failed for {fault}: {err}"
        assert err is None


def test_validate_generated_payload_missing_keys():
    """Ensures payloads with missing keys are rejected."""
    sample = generate_telemetry("normal")
    del sample["status"]
    valid, err = validate_generated_payload(sample)
    assert valid is False
    assert "Missing required root key 'status'" in err

    sample2 = generate_telemetry("normal")
    del sample2["metrics"]["cpu_utilization"]
    valid2, err2 = validate_generated_payload(sample2)
    assert valid2 is False
    assert "cpu_utilization" in err2


def test_validate_generated_payload_out_of_range():
    """Ensures out-of-range values are caught."""
    sample = generate_telemetry("normal")
    sample["metrics"]["cpu_utilization"] = 150.0  # Invalid > 100
    valid, err = validate_generated_payload(sample)
    assert valid is False
    assert "cpu_utilization out of bounds" in err


# =============================================================================
# 3. CANONICAL RECORD ADAPTER TESTS
# =============================================================================

def test_adapt_to_canonical_record():
    """Verifies proper mapping of problem-statement payload to TelemetryRecord."""
    sample = generate_telemetry("latency_spike")
    record = adapt_to_canonical_record(sample, fault_type="latency_spike")
    
    assert isinstance(record, TelemetryRecord)
    assert record.device_id == sample["device_id"]
    assert record.telemetry_origin == "GENERATED_TEST"
    assert record.cpu_utilization_pct == sample["metrics"]["cpu_utilization"]
    assert record.utilization_pct == sample["metrics"]["link_utilization_pct"]
    assert record.packet_loss_pct == sample["metrics"]["packet_loss_pct"]
    assert record.latency_ms == sample["metrics"]["latency_ms"]
    assert record.jitter_ms == sample["metrics"]["jitter_ms"]
    assert record.queue_drops_per_sec == float(sample["metrics"]["queue_drops"])
    assert record.interface_crc_errors == 0
    assert record.device_status == "DEGRADED"  # Warning -> DEGRADED
    assert record.custom_metrics["raw_payload"] == sample


def test_normalizer_auto_adapts_generated_format():
    """Verifies that the existing normalizer transparently adapts generated format."""
    sample = generate_telemetry("hardware_failure")
    rec = TelemetryNormalizer.validate_and_normalize_telemetry(sample)
    assert rec.device_id.startswith("SW_CAMPUS_")
    assert rec.telemetry_origin == "GENERATED_TEST"
    assert rec.device_status == "DOWN"  # Critical -> DOWN
    assert rec.cpu_utilization_pct == 99.9


# =============================================================================
# 4. API ENDPOINT TESTS
# =============================================================================

def test_api_generator_generate():
    """Tests /api/generator/generate endpoint."""
    resp = client.get("/api/generator/generate?fault_type=latency_spike")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["fault_type"] == "latency_spike"
    assert data["telemetry_origin"] == "GENERATED_TEST"
    assert "raw_telemetry" in data
    assert data["raw_telemetry"]["device_id"].startswith("SW_CAMPUS_")


def test_api_generator_generate_invalid():
    """Tests /api/generator/generate with invalid fault type returns 400."""
    resp = client.get("/api/generator/generate?fault_type=invalid_foo")
    assert resp.status_code == 400
    assert "Invalid fault_type" in resp.json()["detail"]


def test_api_generator_validate():
    """Tests /api/generator/validate endpoint."""
    raw = generate_telemetry("normal")
    resp = client.post("/api/generator/validate", json=raw)
    assert resp.status_code == 200
    assert resp.json()["valid"] is True

    # Bad payload
    bad_raw = dict(raw)
    bad_raw["metrics"] = {}
    bad_resp = client.post("/api/generator/validate", json=bad_raw)
    assert bad_resp.status_code == 400


# =============================================================================
# 5. MULTI-AGENT DIAGNOSIS PIPELINE TESTS (Test A, Test B, Test C)
# =============================================================================

def test_diagnosis_mode_normal_test_a():
    """
    Test A: Normal Mode -> Healthy network baseline.
    All agents evaluate healthy metrics, no hypothesis validated, status HEALTHY.
    """
    resp = client.post("/api/generator/diagnose", json={"fault_type": "normal"})
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["success"] is True
    assert data["telemetry_origin"] == "GENERATED_TEST"
    assert data["fault_type"] == "normal"
    assert data["status"] == "HEALTHY"
    assert any(term in data["suspected_root_cause"].lower() for term in ["normal", "healthy", "optimal", "baseline"])
    assert data["report"]["telemetry_origin"] == "GENERATED_TEST"
    assert len(data["timeline_events"]) > 0
    assert len(data["message_bus"]) > 0


def test_diagnosis_mode_latency_spike_test_b():
    """
    Test B: Latency Spike Mode -> Warning / Congestion.
    High latency and jitter trigger PerformanceAgent investigation.
    """
    resp = client.post("/api/generator/diagnose", json={"fault_type": "latency_spike"})
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["success"] is True
    assert data["telemetry_origin"] == "GENERATED_TEST"
    assert data["fault_type"] == "latency_spike"
    assert data["status"] in ("SUSPECTED", "CONFIRMED")
    assert len(data["affected_devices"]) > 0
    assert any(d.startswith("SW_CAMPUS_") for d in data["affected_devices"])
    
    # Verify PerformanceAgent participated in investigation
    agents_involved = {evt["agent_id"] for evt in data["timeline_events"]}
    assert any(a in agents_involved for a in ("perf-agent-01", "PerformanceAgent"))


def test_diagnosis_mode_hardware_failure_test_c():
    """
    Test C: Hardware Failure Mode -> Critical Failure.
    99.9% CPU, 100% link, queue drops, CRC errors trigger InfrastructureAgent and PerformanceAgent.
    """
    resp = client.post("/api/generator/diagnose", json={"fault_type": "hardware_failure"})
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["success"] is True
    assert data["telemetry_origin"] == "GENERATED_TEST"
    assert data["fault_type"] == "hardware_failure"
    assert data["status"] in ("SUSPECTED", "CONFIRMED")
    assert len(data["affected_devices"]) > 0
    assert any(d.startswith("SW_CAMPUS_") for d in data["affected_devices"])
    assert data["confidence"] >= 0.70
    
    # Remediation plan must be populated
    assert "report" in data
    rem_actions = data["report"].get("recommended_actions") or []
    assert len(rem_actions) > 0


# =============================================================================
# 6. DATA PROVENANCE SEPARATION TESTS
# =============================================================================

def test_provenance_separation_guarantee():
    """
    Verifies strict separation:
    1. Generated test data NEVER reports LIVE_DEVICE or LIVE_HOST.
    2. Generating or diagnosing benchmark data NEVER pollutes the live collector telemetry buffer.
    """
    hub = get_collector_hub()
    initial_live_count = len(hub.get_live_telemetry_snapshot()[0])
    
    # Run multiple generated diagnoses
    for ft in ["normal", "latency_spike", "hardware_failure"]:
        resp = client.post("/api/generator/diagnose", json={"fault_type": ft})
        assert resp.status_code == 200
        res = resp.json()
        assert res["telemetry_origin"] == "GENERATED_TEST"
        assert res["telemetry_origin"] != "LIVE_DEVICE"
        assert res["telemetry_origin"] != "LIVE_HOST"

    # Verify live collector telemetry snapshot count remains unchanged
    after_count = len(hub.get_live_telemetry_snapshot()[0])
    assert after_count == initial_live_count
