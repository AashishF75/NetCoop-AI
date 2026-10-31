"""
Unit tests for the three targeted Phase 5 fixes:
1. Confidence terminology: Evidence-based calibrated confidence (no unvalidated Bayesian claims).
2. Interoperability scenario: Distinguishes protocol rejection confidence (1.0) from inconclusive network diagnosis (<= 0.45).
3. Conflicting evidence: Explicitly marks conflict as RESOLVED, shows initial hypothesis, refuting evidence, selected diagnosis, and zero lingering penalty.
"""

import pytest
from app.orchestrator.engine import MultiAgentOrchestrator
from app.scenarios.generator import ScenarioCatalog
from app.protocol.schema import DiagnosticStatus, CURRENT_SCHEMA_VERSION


def test_confidence_terminology_no_bayesian_claims():
    """Verify confidence calculation method and traces do not assert uncalibrated Bayesian claims."""
    orchestrator = MultiAgentOrchestrator()
    telem = ScenarioCatalog.generate_telemetry("normal_network")
    res = orchestrator.run_diagnosis(telem)
    cr = res["canonical_report"]

    calc_method = cr.get("confidence_calculation_method", "")
    assert "bayesian" not in calc_method.lower(), f"Unexpected 'Bayesian' claim in method: {calc_method}"
    assert "evidence-based" in calc_method.lower() or "calibrated" in calc_method.lower()

    # Verify explanation assumptions
    exp = cr.get("investigation_explanation", {})
    for assump in exp.get("assumptions_and_limitations", []):
        assert "bayesian" not in assump.lower(), f"Unexpected 'Bayesian' claim in assumption: {assump}"


def test_interoperability_scenario_distinguishes_protocol_from_diagnostic_confidence():
    """
    Verify Scenario 7 (incompatible_agent_messages) distinguishes:
    - Protocol rejection certainty: 1.0 (100%)
    - Network diagnostic confidence: <= 0.40 (INCONCLUSIVE due to discarded telemetry)
    Preserves Phase 4 status/confidence invariants.
    """
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.post("/api/diagnose", json={"scenario_id": "incompatible_agent_messages"})
    assert response.status_code == 200
    data = response.json()
    cr = data["canonical_report"]

    # 1. Network status must be INCONCLUSIVE
    assert data["status"] == "INCONCLUSIVE"
    assert cr["status"] == "INCONCLUSIVE"

    # 2. Network diagnostic confidence must NOT be artificially high (Phase 4 invariant: <= 0.45)
    assert data["confidence"] <= 0.40, f"Diagnostic confidence too high for INCONCLUSIVE: {data['confidence']}"
    assert cr["confidence"] <= 0.40

    # 3. Protocol rejection confidence must be 1.0 (100% deterministic rejection)
    assert data.get("protocol_rejection_confidence") == 1.0
    assert cr.get("protocol_rejection_confidence") == 1.0

    # 4. Calculation method clearly explains the distinction
    method_str = cr.get("confidence_calculation_method", "")
    assert "100.0% rejection certainty" in method_str or "protocol" in method_str.lower()
    assert "inconclusive" in method_str.lower()


def test_conflicting_evidence_resolves_conflict_explicitly():
    """
    Verify Scenario 8 (conflicting_evidence):
    - Initial hypothesis is clearly presented (Egress Link Buffer Congestion)
    - Specific refuting evidence is documented (99.4% CPU vs 14% link util, 0 drops)
    - Conflict status is explicitly marked RESOLVED (not unresolved)
    - Final diagnosis is Control Plane Processor Saturation
    - Conflict penalty is 0.00 when resolved (no lingering contradiction penalty)
    """
    orchestrator = MultiAgentOrchestrator()
    telem = ScenarioCatalog.generate_telemetry("conflicting_evidence")
    res = orchestrator.run_diagnosis(telem)
    cr = res["canonical_report"]

    # 1. Final diagnosis
    assert cr["status"] == DiagnosticStatus.CONFIRMED
    assert "Control Plane Processor Saturation" in cr["suspected_root_cause"]
    assert cr["confidence"] >= 0.85

    # 2. Conflict status
    assert cr.get("conflict_status") == "RESOLVED"
    details = cr.get("resolved_conflict_details")
    assert details is not None, "Missing resolved_conflict_details in report"
    assert details.get("conflict_status") == "RESOLVED"
    assert "Egress Link Buffer Congestion" in details.get("initial_hypothesis")
    assert "99.4%" in details.get("refuting_evidence")
    assert "Control Plane Processor Saturation" in details.get("selected_diagnosis")
    assert len(details.get("resolution_reasoning", "")) > 10

    # 3. Investigation explanation checks
    exp = cr.get("investigation_explanation", {})
    init_hyps = exp.get("initial_hypotheses", [])
    assert init_hyps[0] == "Egress Link Buffer Congestion", f"Expected initial challenged hypothesis first, got {init_hyps}"
    assert "explicitly marked RESOLVED" in exp.get("final_resolution", "")

    # 4. Confidence calculation method marks conflict as resolved with 0.00 penalty
    calc_str = cr.get("confidence_calculation_method", "")
    assert "Conflict: Resolved (0.00 penalty)" in calc_str, f"Unexpected conflict representation: {calc_str}"
    assert "bayesian" not in calc_str.lower()
