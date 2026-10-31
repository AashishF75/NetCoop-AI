"""
Automated Tests for All 8 Benchmark Diagnostic Scenarios.
Ensures diagnostic correctness, accurate root-cause identification, and structured report adherence.
"""

import pytest
from app.orchestrator.engine import MultiAgentOrchestrator
from app.scenarios.generator import ScenarioCatalog
from app.protocol.schema import DiagnosticStatus


@pytest.fixture
def orchestrator():
    return MultiAgentOrchestrator()


def test_scenario_normal_network(orchestrator):
    telemetry = ScenarioCatalog.generate_telemetry("normal_network")
    result = orchestrator.run_diagnosis(telemetry)
    assert result["status"] == "HEALTHY"
    assert "Normal Network Operation" in result["suspected_root_cause"]
    assert result["confidence"] >= 0.90
    assert len(result["canonical_report"]["recommended_actions"]) >= 1


def test_scenario_link_congestion(orchestrator):
    telemetry = ScenarioCatalog.generate_telemetry("link_congestion")
    result = orchestrator.run_diagnosis(telemetry)
    assert result["status"] in ["CONFIRMED", "SUSPECTED"]
    assert "Congestion" in result["suspected_root_cause"]
    assert result["confidence"] >= 0.85
    assert "Core-Router-01" in result["affected_devices"] or "Agg-Switch-01" in result["affected_devices"]
    
    # Check that recommendation includes queue tuning or QoS
    actions = result["canonical_report"]["recommended_actions"]
    assert any("QoS" in a["action"] or "Queue" in a["action"] or "LACP" in a["action"] for a in actions)


def test_scenario_weak_wifi_signal(orchestrator):
    telemetry = ScenarioCatalog.generate_telemetry("weak_wifi_signal")
    result = orchestrator.run_diagnosis(telemetry)
    assert result["status"] in ["CONFIRMED", "SUSPECTED"]
    assert ("Wireless" in result["suspected_root_cause"] or "RF" in result["suspected_root_cause"])
    assert "AP-02" in result["affected_devices"]
    
    actions = result["canonical_report"]["recommended_actions"]
    assert any("Radio" in a["action"] or "Steer" in a["action"] or "AP" in a["action"] for a in actions)


def test_scenario_interface_fault(orchestrator):
    telemetry = ScenarioCatalog.generate_telemetry("interface_fault")
    result = orchestrator.run_diagnosis(telemetry)
    assert result["status"] in ["CONFIRMED", "SUSPECTED"]
    assert ("Physical" in result["suspected_root_cause"] or "Interface" in result["suspected_root_cause"])
    assert "Edge-Switch-01" in result["affected_devices"]
    
    actions = result["canonical_report"]["recommended_actions"]
    assert any("Transceiver" in a["action"] or "DOM" in a["action"] or "Standby" in a["action"] for a in actions)


def test_scenario_dns_dhcp_failure(orchestrator):
    telemetry = ScenarioCatalog.generate_telemetry("dns_dhcp_failure")
    result = orchestrator.run_diagnosis(telemetry)
    assert result["status"] in ["CONFIRMED", "SUSPECTED"]
    assert ("DNS" in result["suspected_root_cause"] or "Services" in result["suspected_root_cause"])
    assert "DNS-Server-01" in result["affected_devices"]


def test_scenario_missing_telemetry(orchestrator):
    telemetry = ScenarioCatalog.generate_telemetry("missing_telemetry")
    result = orchestrator.run_diagnosis(telemetry)
    # Must flag insufficient evidence and limitations!
    assert result["status"] in ["INCONCLUSIVE", "SUSPECTED"]
    assert len(result["canonical_report"]["limitations"]) > 0
    assert any("missing critical telemetry" in lim.lower() for lim in result["canonical_report"]["limitations"])
    assert result["confidence"] <= 0.60


def test_scenario_conflicting_evidence(orchestrator):
    telemetry = ScenarioCatalog.generate_telemetry("conflicting_evidence")
    result = orchestrator.run_diagnosis(telemetry)
    
    # Must identify CPU saturation despite high latency
    assert "CPU" in result["suspected_root_cause"] or "Processor" in result["suspected_root_cause"]
    
    # Check that message bus contains CONFLICT_DETECTED
    message_types = [m["message_type"] for m in result["message_bus"]]
    assert "CONFLICT_DETECTED" in message_types
