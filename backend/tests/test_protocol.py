"""
Automated Tests for Canonical JSON Protocol, Normalizer, and Schema Validation.
Covers:
- Schema compatibility & version checking
- Malformed input detection
- Missing required fields
- Unit normalization
- CSV & JSON telemetry parsing
"""

import pytest
from app.protocol.schema import (
    AgentMessage,
    MessageType,
    TelemetryRecord,
    CURRENT_SCHEMA_VERSION,
)
from app.protocol.normalizer import (
    TelemetryNormalizer,
    InteroperabilityValidator,
    MalformedDataError,
    SchemaVersionMismatchError,
    MissingFieldError,
)


def test_valid_agent_message_creation():
    msg = AgentMessage(
        agent_id="perf-agent-01",
        message_type=MessageType.TELEMETRY_ANOMALY,
        device_id="Core-Router-01",
        metric="latency_ms",
        value=142.5,
        unit="ms",
        evidence={"observed": 142.5, "baseline": 5.0},
        confidence=0.92,
        findings=["Critical latency spike observed"],
    )
    assert msg.schema_version == CURRENT_SCHEMA_VERSION
    assert msg.confidence == 0.92
    assert msg.agent_id == "perf-agent-01"


def test_schema_version_mismatch():
    invalid_payload = {
        "agent_id": "legacy-agent-01",
        "message_type": "TELEMETRY_ANOMALY",
        "schema_version": "0.8.0",  # Outdated version
        "device_id": "Switch-01",
    }
    with pytest.raises(SchemaVersionMismatchError) as exc_info:
        InteroperabilityValidator.validate_message(invalid_payload)
    assert "Incompatible schema_version '0.8.0'" in str(exc_info.value)


def test_missing_required_fields():
    # Missing message_type
    payload_no_type = {
        "agent_id": "perf-agent-01",
        "schema_version": "1.0.0",
        "device_id": "Router-01",
    }
    with pytest.raises(MissingFieldError) as exc_info:
        InteroperabilityValidator.validate_message(payload_no_type)
    assert "message_type" in exc_info.value.missing_fields

    # Missing schema_version
    payload_no_version = {
        "agent_id": "perf-agent-01",
        "message_type": "TELEMETRY_ANOMALY",
    }
    with pytest.raises(MissingFieldError):
        InteroperabilityValidator.validate_message(payload_no_version)


def test_malformed_telemetry_ranges():
    # Negative latency
    with pytest.raises(MalformedDataError):
        TelemetryNormalizer.validate_and_normalize_telemetry({
            "device_id": "Router-01",
            "latency_ms": -10.0,
        })

    # Packet loss > 100%
    with pytest.raises(MalformedDataError):
        TelemetryNormalizer.validate_and_normalize_telemetry({
            "device_id": "Router-01",
            "packet_loss_pct": 105.0,
        })

    # CPU > 100%
    with pytest.raises(MalformedDataError):
        TelemetryNormalizer.validate_and_normalize_telemetry({
            "device_id": "Router-01",
            "cpu_utilization_pct": 140.0,
        })


def test_unit_normalization():
    # Seconds to ms
    val, unit = TelemetryNormalizer.normalize_unit_value(0.125, "s", "latency_ms")
    assert val == 125.0
    assert unit == "ms"

    # Microseconds to ms
    val, unit = TelemetryNormalizer.normalize_unit_value(5000, "us", "latency_ms")
    assert val == 5.0
    assert unit == "ms"

    # Gbps to Mbps
    val, unit = TelemetryNormalizer.normalize_unit_value(2.5, "Gbps", "throughput")
    assert val == 2500.0
    assert unit == "Mbps"

    # Ratio to percentage
    val, unit = TelemetryNormalizer.normalize_unit_value(0.08, "ratio", "packet_loss_pct")
    assert val == 8.0
    assert unit == "%"


def test_csv_telemetry_parsing():
    csv_data = """device_id,latency_ms,packet_loss_pct,cpu_utilization_pct
Core-Router-01,4.2,0.0,25.5
Agg-Switch-01,6.1,0.0,30.0
"""
    records = TelemetryNormalizer.parse_csv_telemetry(csv_data)
    assert len(records) == 2
    assert records[0].device_id == "Core-Router-01"
    assert records[0].latency_ms == 4.2
    assert records[1].device_id == "Agg-Switch-01"
    assert records[1].cpu_utilization_pct == 30.0


def test_json_telemetry_parsing():
    json_data = """[
        {"device_id": "Core-Router-01", "latency_ms": 3.0, "packet_loss_pct": 0.0},
        {"device_id": "Agg-Switch-01", "latency_ms": 5.5, "packet_loss_pct": 1.2}
    ]"""
    records = TelemetryNormalizer.parse_json_telemetry(json_data)
    assert len(records) == 2
    assert records[0].device_id == "Core-Router-01"
    assert records[1].packet_loss_pct == 1.2
