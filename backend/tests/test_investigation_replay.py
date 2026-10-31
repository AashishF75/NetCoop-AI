"""
Automated Tests for Autonomous Investigation Replay & Enhanced Multi-Agent Workflow.
Verifies timeline event emission, hypothesis lifecycle status tracking,
remediation expected outcomes, and investigation store persistence.
"""

import pytest
from app.orchestrator.engine import MultiAgentOrchestrator
from app.orchestrator.store import investigation_store
from app.scenarios.generator import ScenarioCatalog
from app.protocol.schema import (
    DiagnosticStatus,
    InvestigationEventType,
    CURRENT_SCHEMA_VERSION,
)


@pytest.fixture
def orchestrator():
    return MultiAgentOrchestrator()


def test_timeline_events_generated(orchestrator):
    """Verifies that diagnosis pipeline emits structured InvestigationEvent timeline stream."""
    telemetry = ScenarioCatalog.generate_telemetry("conflicting_evidence")
    result = orchestrator.run_diagnosis(telemetry, incident_id="INC-REPLAY-TEST", scenario_id="conflicting_evidence")

    assert "timeline_events" in result
    events = result["timeline_events"]
    assert len(events) >= 10, f"Expected >= 10 timeline events, got {len(events)}"

    # Check required phases and event types
    event_types = [e["event_type"] for e in events]
    assert "INCIDENT_DETECTED" in event_types
    assert "AGENT_ACTIVATED" in event_types
    assert "EVIDENCE_COLLECTED" in event_types
    assert "CROSS_AGENT_QUERY" in event_types
    assert "CROSS_AGENT_RESPONSE" in event_types
    assert "CONFLICT_DETECTED" in event_types
    assert "HYPOTHESIS_CHALLENGED" in event_types
    assert "HYPOTHESIS_CONFIRMED" in event_types
    assert "ROOT_CAUSE_RESOLVED" in event_types
    assert "REMEDIATION_GENERATED" in event_types
    assert "INVESTIGATION_COMPLETE" in event_types

    # Verify event structure
    for evt in events:
        assert "event_id" in evt
        assert "step_number" in evt
        assert "phase" in evt
        assert "title" in evt
        assert "description" in evt
        assert "elapsed_ms" in evt


def test_investigation_store_persistence(orchestrator):
    """Verifies that completed investigations are saved and retrievable via InvestigationStore."""
    telemetry = ScenarioCatalog.generate_telemetry("link_congestion")
    inc_id = "INC-STORE-TEST-01"
    result = orchestrator.run_diagnosis(telemetry, incident_id=inc_id, scenario_id="link_congestion")

    # Retrieve from store
    stored = investigation_store.get_investigation(inc_id)
    assert stored is not None
    assert stored["incident_id"] == inc_id
    assert stored["status"] == "CONFIRMED"
    assert len(stored["timeline_events"]) > 0

    # Verify list summaries
    summaries = investigation_store.list_investigations()
    assert any(s["incident_id"] == inc_id for s in summaries)


def test_hypothesis_status_and_reasoning(orchestrator):
    """Verifies that competing hypotheses track status (CONFIRMED/REJECTED/CHALLENGED) and reasoning."""
    telemetry = ScenarioCatalog.generate_telemetry("conflicting_evidence")
    result = orchestrator.run_diagnosis(telemetry, incident_id="INC-HYP-TEST")

    hypotheses = result["canonical_report"]["alternative_causes"]
    assert len(hypotheses) >= 2

    cpu_hyp = next((h for h in hypotheses if "CPU" in h["name"] or "Processor" in h["name"]), None)
    cong_hyp = next((h for h in hypotheses if "Congestion" in h["name"]), None)

    assert cpu_hyp is not None
    assert cpu_hyp["status"] in ["CONFIRMED", "VALIDATED"]
    assert cpu_hyp["reasoning"] is not None
    assert "CPU" in cpu_hyp["reasoning"]

    assert cong_hyp is not None
    assert cong_hyp["status"] in ["REJECTED", "REFUTED", "CHALLENGED"]
    assert cong_hyp["reasoning"] is not None


def test_remediation_expected_outcomes(orchestrator):
    """Verifies that all remediation actions include expected outcomes and rollback plans."""
    telemetry = ScenarioCatalog.generate_telemetry("link_congestion")
    result = orchestrator.run_diagnosis(telemetry)

    actions = result["canonical_report"]["recommended_actions"]
    assert len(actions) >= 2

    for act in actions:
        assert "expected_outcome" in act
        assert act["expected_outcome"] is not None
        assert len(act["expected_outcome"]) > 10
        assert "rollback_plan" in act
        assert "risk_level" in act
        assert act["risk_level"] in ["LOW", "MEDIUM", "HIGH"]


def test_fault_propagation_paths(orchestrator):
    """Verifies that fault propagation paths are calculated for network topology visualization."""
    telemetry = ScenarioCatalog.generate_telemetry("link_congestion")
    result = orchestrator.run_diagnosis(telemetry)

    paths = result["fault_propagation_paths"]
    assert len(paths) > 0
    assert "Core-Router-01" in paths[0]
    assert "Agg-Switch-01" in paths[0]

