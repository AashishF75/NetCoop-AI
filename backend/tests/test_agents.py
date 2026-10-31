"""
Automated Tests for Domain Agents.
Covers:
- Performance Agent anomaly detection and query handling
- Infrastructure Health Agent hardware detection and query handling
- Connectivity Analysis Agent RF/DNS detection and query handling
"""

import pytest
from app.protocol.schema import (
    TelemetryRecord,
    MessageType,
    CURRENT_SCHEMA_VERSION,
)
from app.agents.performance_agent import PerformanceAgent
from app.agents.infrastructure_agent import InfrastructureAgent
from app.agents.connectivity_agent import ConnectivityAgent


def test_performance_agent_detects_congestion():
    agent = PerformanceAgent()
    telemetry = [
        TelemetryRecord(
            device_id="Agg-Switch-01",
            latency_ms=130.0,
            packet_loss_pct=4.5,
            utilization_pct=96.0,
            queue_drops_per_sec=65.0,
        )
    ]
    anomalies = agent.analyze(telemetry)
    assert len(anomalies) >= 2  # latency, loss, and congestion
    metrics = [a.metric for a in anomalies]
    assert "latency_ms" in metrics
    assert "queue_drops_per_sec" in metrics

    # Test query response
    query_msg = agent.create_message(
        message_type=MessageType.QUERY_EVIDENCE,
        device_id="Agg-Switch-01",
        target_agent_id=agent.agent_id,
    )
    resp = agent.handle_query(query_msg, telemetry)
    assert resp.message_type == MessageType.QUERY_RESPONSE
    assert resp.value.get("is_buffer_congested") is True


def test_infrastructure_agent_detects_crc_errors():
    agent = InfrastructureAgent()
    telemetry = [
        TelemetryRecord(
            device_id="Edge-Switch-01",
            cpu_utilization_pct=25.0,
            interface_crc_errors=850,
            interface_flaps=4,
        )
    ]
    anomalies = agent.analyze(telemetry)
    crc_anomalies = [a for a in anomalies if a.metric == "interface_crc_errors"]
    assert len(crc_anomalies) == 1
    assert crc_anomalies[0].evidence["severity"] == "CRITICAL"

    # Query response
    query_msg = agent.create_message(
        message_type=MessageType.QUERY_EVIDENCE,
        device_id="Edge-Switch-01",
        target_agent_id=agent.agent_id,
    )
    resp = agent.handle_query(query_msg, telemetry)
    assert resp.value.get("has_physical_fault") is True
    assert resp.value.get("crc_errors") == 850


def test_connectivity_agent_detects_weak_wifi():
    agent = ConnectivityAgent()
    telemetry = [
        TelemetryRecord(
            device_id="AP-02",
            wifi_rssi_dbm=-87.0,
            wifi_snr_db=8.0,
            wifi_retry_pct=45.0,
        )
    ]
    anomalies = agent.analyze(telemetry)
    wifi_anomalies = [a for a in anomalies if a.metric == "wifi_rssi_dbm"]
    assert len(wifi_anomalies) == 1
    assert wifi_anomalies[0].value == -87.0

    # Query response
    query_msg = agent.create_message(
        message_type=MessageType.QUERY_EVIDENCE,
        device_id="AP-02",
        target_agent_id=agent.agent_id,
    )
    resp = agent.handle_query(query_msg, telemetry)
    assert resp.value.get("has_rf_issue") is True
