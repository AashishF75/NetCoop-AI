"""
Automated Tests for Inter-Agent Communication & Conflict Resolution.
Verifies:
- Genuine inter-agent query/response exchange
- Competing hypotheses generation and ranking
- Conflict resolution between performance and infrastructure evidence
- Insufficient evidence handling
"""

import pytest
from app.orchestrator.engine import MultiAgentOrchestrator
from app.scenarios.generator import ScenarioCatalog
from app.protocol.schema import MessageType, DiagnosticStatus


def test_genuine_agent_communication_exchange():
    """
    Validates that at least two agents genuinely exchange structured findings
    via QUERY_EVIDENCE and QUERY_RESPONSE messages with matching correlation IDs.
    """
    orchestrator = MultiAgentOrchestrator()
    telemetry = ScenarioCatalog.generate_telemetry("link_congestion")
    result = orchestrator.run_diagnosis(telemetry)

    message_bus = result["message_bus"]
    queries = [m for m in message_bus if m["message_type"] == "QUERY_EVIDENCE"]
    responses = [m for m in message_bus if m["message_type"] == "QUERY_RESPONSE"]

    assert len(queries) >= 2, "Fault Correlation Agent must query peer agents"
    assert len(responses) >= 2, "Peer agents must respond with structured evidence"

    # Verify correlation IDs link queries and responses
    query_corr_ids = {q["correlation_id"] for q in queries if q.get("correlation_id")}
    resp_corr_ids = {r["correlation_id"] for r in responses if r.get("correlation_id")}
    shared_corr_ids = query_corr_ids.intersection(resp_corr_ids)
    assert len(shared_corr_ids) > 0, "Queries and responses must share correlation IDs"


def test_competing_hypotheses_ranking():
    """
    Validates that multiple competing hypotheses are formulated and probabilities assigned.
    """
    orchestrator = MultiAgentOrchestrator()
    telemetry = ScenarioCatalog.generate_telemetry("interface_fault")
    result = orchestrator.run_diagnosis(telemetry)

    hypotheses = result["canonical_report"]["alternative_causes"]
    assert len(hypotheses) >= 3, "Must generate at least 3 competing hypotheses"

    # Sorted by probability descending
    probs = [h["probability"] for h in hypotheses]
    assert probs == sorted(probs, reverse=True), "Hypotheses must be ranked by probability descending"

    # Top hypothesis should be Interface Fault
    top_hyp = hypotheses[0]
    assert "Interface" in top_hyp["name"] or "Physical" in top_hyp["name"]
    assert top_hyp["probability"] >= 0.80
    assert len(top_hyp["supporting_evidence"]) > 0


def test_conflict_resolution_behavior():
    """
    Tests scenario where latency mimics congestion but CPU saturation is the root cause.
    Correlation Agent must catch conflict and emit CONFLICT_DETECTED.
    """
    orchestrator = MultiAgentOrchestrator()
    telemetry = ScenarioCatalog.generate_telemetry("conflicting_evidence")
    result = orchestrator.run_diagnosis(telemetry)

    # Find the CONFLICT_DETECTED message
    conflict_msgs = [m for m in result["message_bus"] if m["message_type"] == "CONFLICT_DETECTED"]
    assert len(conflict_msgs) == 1, "Must issue exactly one CONFLICT_DETECTED resolution message"

    c_msg = conflict_msgs[0]
    assert "conflicting_metrics" in c_msg["evidence"]
    assert "CONTROL_PLANE_CPU_OVERLOAD_PREVAILS" in c_msg["evidence"]["resolution"]


def test_insufficient_evidence_handling():
    """
    Tests that missing telemetry correctly yields INCONCLUSIVE / SUSPECTED
    and does not pretend to have a confident diagnosis.
    """
    orchestrator = MultiAgentOrchestrator()
    telemetry = ScenarioCatalog.generate_telemetry("missing_telemetry")
    result = orchestrator.run_diagnosis(telemetry)

    assert result["status"] in ["INCONCLUSIVE", "SUSPECTED"]
    assert result["confidence"] < 0.65
    assert len(result["canonical_report"]["limitations"]) > 0
