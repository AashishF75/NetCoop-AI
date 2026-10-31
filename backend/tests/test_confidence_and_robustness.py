"""
Phase 4 Test Suite: Confidence Calibration & Robustness.

Validates:
1. Strong corroborating evidence vs weak single-signal evidence
2. Missing and stale telemetry reducing confidence
3. Contradictory findings reducing confidence
4. INCONCLUSIVE and INSUFFICIENT_EVIDENCE reports not receiving misleadingly high confidence
5. Agent timeout/failure handled gracefully
6. Malformed or incompatible telemetry handled safely
7. Existing Phase 3 evidence-grounding and human-approval protections preserved
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.protocol.schema import (
    TelemetryRecord,
    DiagnosticStatus,
    MessageType,
    InvestigationEventType,
    CanonicalDiagnosticReport,
)
from app.orchestrator.engine import MultiAgentOrchestrator


class TestConfidenceCalibrationCorroboration:
    """Tests that confidence reflects multi-signal corroboration vs weak single-signal evidence."""

    def test_strong_corroborating_evidence_vs_weak_single_signal(self):
        orch = MultiAgentOrchestrator()

        # Case A: Strong multi-signal corroborated link congestion
        # Signals: Bandwidth saturation (98%) + Egress queue drops (82 pkts/s) + High RTT latency (160ms)
        corroborated_telem = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Core-Router-01",
                device_type="router",
                device_status="DEGRADED",
                latency_ms=160.0,
                packet_loss_pct=8.5,
                utilization_pct=98.0,
                queue_drops_per_sec=82.0,
                interface_in_discards=24,
                cpu_utilization_pct=25.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]
        res_corrob = orch.run_diagnosis(corroborated_telem, incident_id="INC-CORROB-TEST")
        rep_corrob = res_corrob["canonical_report"]

        assert rep_corrob["status"] == DiagnosticStatus.CONFIRMED
        assert "Congestion" in rep_corrob["suspected_root_cause"]
        assert rep_corrob["confidence"] >= 0.85, f"Expected high confidence, got {rep_corrob['confidence']}"

        # Case B: Weak single-signal evidence (Elevated latency alone without drops or utilization)
        single_signal_telem = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Core-Router-01",
                device_type="router",
                device_status="UP",
                latency_ms=160.0,
                packet_loss_pct=0.0,
                utilization_pct=15.0,
                queue_drops_per_sec=0.0,
                interface_in_discards=0,
                cpu_utilization_pct=25.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]
        res_single = orch.run_diagnosis(single_signal_telem, incident_id="INC-SINGLE-SIGNAL-TEST")
        rep_single = res_single["canonical_report"]

        # Status must NOT be CONFIRMED, and confidence must be strictly lower
        assert rep_single["status"] in (DiagnosticStatus.INCONCLUSIVE, DiagnosticStatus.INSUFFICIENT_EVIDENCE)
        assert rep_single["confidence"] <= 0.48, f"Single signal confidence too high: {rep_single['confidence']}"
        assert rep_corrob["confidence"] - rep_single["confidence"] >= 0.35, "Corroborated confidence should substantially exceed single signal"


class TestMissingAndStaleTelemetryPenalty:
    """Tests that missing and stale telemetry measurably penalize confidence."""

    def test_missing_telemetry_dimensions_reduce_confidence(self):
        orch = MultiAgentOrchestrator()

        # Telemetry with anomalous latency, but missing all queue drops, CPU, CRC, and oper status
        sparse_telem = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Switch-A",
                device_type="switch",
                device_status="DEGRADED",
                latency_ms=75.0,
                packet_loss_pct=2.0,
                queue_drops_per_sec=None,  # Missing
                cpu_utilization_pct=None,   # Missing
                interface_crc_errors=None,  # Missing
                interface_oper_status=None, # Missing
                telemetry_origin="LIVE_DEVICE",
            )
        ]
        res = orch.run_diagnosis(sparse_telem, incident_id="INC-MISSING-TEST")
        rep = res["canonical_report"]

        assert rep["status"] in (DiagnosticStatus.INCONCLUSIVE, DiagnosticStatus.INSUFFICIENT_EVIDENCE)
        assert rep["confidence"] <= 0.45
        assert len(rep["limitations"]) > 0
        assert any("missing critical telemetry" in lim.lower() for lim in rep["limitations"])

    def test_stale_telemetry_penalizes_confidence(self):
        orch = MultiAgentOrchestrator()

        # Stale telemetry explicitly flagged as STALE_TELEMETRY
        stale_telem = [
            TelemetryRecord(
                timestamp=(datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat(),
                device_id="Border-Router-01",
                device_type="router",
                device_status="STALE_TELEMETRY",
                latency_ms=150.0,
                packet_loss_pct=10.0,
                utilization_pct=95.0,
                queue_drops_per_sec=50.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]
        res_stale = orch.run_diagnosis(stale_telem, incident_id="INC-STALE-TEST")
        rep_stale = res_stale["canonical_report"]

        # Confirmed status must be demoted to SUSPECTED due to staleness
        assert rep_stale["status"] == DiagnosticStatus.SUSPECTED
        assert rep_stale["confidence"] <= 0.74, f"Stale confidence must be discounted, got {rep_stale['confidence']}"
        assert any("stale" in lim.lower() for lim in rep_stale["limitations"])


class TestContradictionConfidencePenalty:
    """Tests that contradictory signals reduce confidence and trigger CONFLICT_DETECTED."""

    def test_packet_loss_without_crc_contradiction_penalizes_confidence(self):
        orch = MultiAgentOrchestrator()

        # High packet loss (15%) suggesting link failure, but ZERO CRC errors and ZERO queue drops
        contradictory_telem = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Edge-Switch-01",
                device_type="switch",
                device_status="UP",
                latency_ms=30.0,
                packet_loss_pct=15.0,
                queue_drops_per_sec=0.0,
                interface_crc_errors=0,
                interface_flaps=0,
                utilization_pct=20.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]
        res = orch.run_diagnosis(contradictory_telem, incident_id="INC-CONTRADICTION-TEST")
        rep = res["canonical_report"]

        # Conflict must be detected on the bus
        conflicts = [m for m in res["message_bus"] if m.get("message_type") == MessageType.CONFLICT_DETECTED.value]
        assert len(conflicts) > 0
        assert "PHYSICAL_FAULT_REFUTED" in conflicts[0]["evidence"]["resolution"]

        # Physical link defect hypothesis must be refuted
        phys_hyp = next((h for h in rep["alternative_causes"] if h["hypothesis_id"] == "HYP-INTERFACE-FAULT"), None)
        assert phys_hyp is not None
        assert phys_hyp["probability"] <= 0.20

        # Overall diagnosis must be inconclusive and confidence discounted
        assert rep["status"] in (DiagnosticStatus.INCONCLUSIVE, DiagnosticStatus.INSUFFICIENT_EVIDENCE)
        assert rep["confidence"] <= 0.48


class TestInconclusiveConfidenceBounds:
    """Tests that INCONCLUSIVE / INSUFFICIENT_EVIDENCE diagnoses never receive high confidence."""

    def test_inconclusive_confidence_strictly_capped(self):
        orch = MultiAgentOrchestrator()

        test_cases = [
            [],  # Empty telemetry
            [TelemetryRecord(device_id="Dev-1", latency_ms=120.0, queue_drops_per_sec=0.0, utilization_pct=10.0)], # Uncorroborated latency
            [TelemetryRecord(device_id="Dev-2", packet_loss_pct=3.0)], # Missing dimensions
        ]

        for idx, telem in enumerate(test_cases):
            res = orch.run_diagnosis(telem, incident_id=f"INC-BOUND-TEST-{idx}")
            rep = res["canonical_report"]

            assert rep["status"] in (DiagnosticStatus.INCONCLUSIVE, DiagnosticStatus.INSUFFICIENT_EVIDENCE)
            assert rep["confidence"] <= 0.48, f"Inconclusive run #{idx} received high confidence: {rep['confidence']}"
            assert res["confidence"] <= 0.48


class TestAgentFailureRobustness:
    """Tests graceful handling when domain agents fail or time out."""

    def test_agent_timeout_handled_gracefully(self):
        orch = MultiAgentOrchestrator()

        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Core-Router-01",
                device_type="router",
                device_status="DEGRADED",
                latency_ms=160.0,
                queue_drops_per_sec=70.0,
                utilization_pct=95.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]

        # Simulate timeout in performance agent
        with patch.object(orch.perf_agent, "analyze", side_effect=TimeoutError("PerformanceAgent query timeout")):
            res = orch.run_diagnosis(telemetry, incident_id="INC-TIMEOUT-TEST")
            rep = res["canonical_report"]

            # Orchestrator must not crash and must produce report
            assert rep is not None
            assert res["incident_id"] == "INC-TIMEOUT-TEST"

            # Failure must be logged in limitations
            assert any("performance agent" in lim.lower() for lim in rep["limitations"])

            # An AGENT_DEACTIVATED event must be recorded
            deactivated_events = [e for e in res["timeline_events"] if e.get("event_type") == InvestigationEventType.AGENT_DEACTIVATED.value]
            assert len(deactivated_events) > 0

    def test_all_domain_agents_failing_yields_safe_inconclusive(self):
        orch = MultiAgentOrchestrator()
        telemetry = [TelemetryRecord(device_id="R1", latency_ms=100.0)]

        with patch.object(orch.perf_agent, "analyze", side_effect=RuntimeError("Crash Perf")), \
             patch.object(orch.infra_agent, "analyze", side_effect=RuntimeError("Crash Infra")), \
             patch.object(orch.conn_agent, "analyze", side_effect=RuntimeError("Crash Conn")):
            res = orch.run_diagnosis(telemetry, incident_id="INC-ALL-CRASH")
            rep = res["canonical_report"]

            assert rep["status"] in (DiagnosticStatus.INCONCLUSIVE, DiagnosticStatus.INSUFFICIENT_EVIDENCE)
            assert rep["confidence"] <= 0.48
            assert len(rep["recommended_actions"]) > 0
            # Recommendations must remain safe read-only diagnostics
            assert all(a["risk_level"] == "LOW" for a in rep["recommended_actions"])


class TestMalformedAndIncompatibleTelemetryHandling:
    """Tests safe processing of malformed, unknown, or incompatible telemetry inputs."""

    def test_none_and_empty_telemetry(self):
        orch = MultiAgentOrchestrator()
        res_none = orch.run_diagnosis(None, incident_id="INC-NONE")
        assert res_none["status"] == "INCONCLUSIVE"
        assert res_none["confidence"] <= 0.45

        res_empty = orch.run_diagnosis([], incident_id="INC-EMPTY")
        assert res_empty["status"] == "INCONCLUSIVE"
        assert res_empty["confidence"] <= 0.45

    def test_mixed_dictionaries_and_invalid_objects(self):
        orch = MultiAgentOrchestrator()

        # Input containing a mix of valid dicts, string numbers, missing device_id, and incompatible items
        mixed_input = [
            {"device_id": "Switch-01", "latency": "45.5 ms", "loss": "0%"},
            {"device_id": "", "latency": "30ms"},  # Empty device_id
            "completely_invalid_string_item",       # Incompatible type
            42,                                     # Incompatible type
            {"device_id": "Router-02", "latency": "invalid_number_abc"}, # Malformed numeric
            TelemetryRecord(device_id="Switch-02", latency_ms=15.0),      # Valid record
        ]

        res = orch.run_diagnosis(mixed_input, incident_id="INC-MIXED-INPUT")
        rep = res["canonical_report"]

        # Must not raise exception, must output report
        assert rep is not None
        assert len(rep["limitations"]) > 0
        assert any("skipped" in lim.lower() or "normalized" in lim.lower() for lim in rep["limitations"])


class TestPhase3ProtectionsPreserved:
    """Verifies that Phase 3 evidence grounding and human-approval protections remain intact."""

    def test_human_approval_required_for_risky_changes(self):
        orch = MultiAgentOrchestrator()
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Trunk-Switch-01",
                device_type="switch",
                device_status="DEGRADED",
                latency_ms=180.0,
                queue_drops_per_sec=65.0,
                utilization_pct=98.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-APPROVAL-TEST")
        actions = res["canonical_report"]["recommended_actions"]

        for a in actions:
            assert len(a["supporting_evidence"]) > 0
            if a["risk_level"] in ("MEDIUM", "HIGH"):
                assert a["requires_human_approval"] is True
            elif a["risk_level"] == "LOW":
                assert a["requires_human_approval"] is False

    def test_observed_facts_and_next_checks_populated(self):
        orch = MultiAgentOrchestrator()
        telemetry = [
            TelemetryRecord(
                device_id="Test-Router",
                latency_ms=150.0,
                queue_drops_per_sec=0.0,
                utilization_pct=12.0,
            )
        ]
        res = orch.run_diagnosis(telemetry)
        rep = res["canonical_report"]

        assert "observed_facts" in rep
        assert len(rep["observed_facts"]) > 0
        assert "next_diagnostic_checks" in rep
        assert len(rep["next_diagnostic_checks"]) > 0
