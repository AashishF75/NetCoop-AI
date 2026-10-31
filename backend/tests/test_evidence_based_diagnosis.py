"""
Phase 3 Test Suite: Evidence-Based Multi-Agent Diagnosis.
Validates:
1. High ping latency alone must not confirm congestion.
2. Congestion with corroborating utilization/drop evidence confirms congestion.
3. Interface-down diagnosis confirmed only with interface status evidence.
4. DNS failure diagnosed only with DNS evidence; DHCP failure only with DHCP evidence.
5. Conflicting evidence detection and resolution (e.g. latency vs utilization, loss vs CRC).
6. Missing and stale telemetry handling with explicit limitations.
7. Explicit INSUFFICIENT_EVIDENCE / INCONCLUSIVE outcomes without root-cause fabrication.
8. Grounded recommendations tied to supporting evidence and flagged for human approval.
9. End-to-end 5-agent collaboration preserving provenance tags (LIVE_DEVICE, LIVE_HOST, etc.).
"""

import pytest
from datetime import datetime, timezone

from app.protocol.schema import (
    TelemetryRecord,
    DiagnosticStatus,
    MessageType,
)
from app.agents.performance_agent import PerformanceAgent
from app.agents.infrastructure_agent import InfrastructureAgent
from app.agents.connectivity_agent import ConnectivityAgent
from app.agents.correlation_agent import FaultCorrelationAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.orchestrator.engine import MultiAgentOrchestrator


class TestLatencyVsCongestionGrounding:
    """Tests that high ping latency alone never confirms congestion without queue/utilization evidence."""

    def test_high_ping_latency_alone_does_not_assert_congestion(self):
        orch = MultiAgentOrchestrator()
        # Telemetry with high ping latency (185ms), but ZERO queue drops and low utilization (14%)
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Edge-Router-01",
                device_type="router",
                device_status="UP",
                latency_ms=185.0,
                packet_loss_pct=0.0,
                queue_drops_per_sec=0.0,
                interface_in_discards=0,
                interface_out_discards=0,
                utilization_pct=14.0,
                interface_crc_errors=0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-HIGH-LATENCY-ALONE")
        report = res["canonical_report"]

        # Status must NOT be CONFIRMED congestion
        assert report["status"] in (DiagnosticStatus.INSUFFICIENT_EVIDENCE, DiagnosticStatus.INCONCLUSIVE)
        assert "Egress Link Buffer Congestion" not in report["suspected_root_cause"]
        assert "Inconclusive" in report["suspected_root_cause"] or "Uncorroborated" in report["suspected_root_cause"]

        # Congestion hypothesis must be refuted or low probability
        congestion_hyp = next((h for h in report["alternative_causes"] if h["hypothesis_id"] == "HYP-CONGESTION"), None)
        assert congestion_hyp is not None
        assert congestion_hyp["probability"] <= 0.25
        assert any("refut" in str(e).lower() or "contradict" in str(e).lower() for e in congestion_hyp["contradicting_evidence"])

        # Next diagnostic checks must be populated
        assert len(report["next_diagnostic_checks"]) > 0
        assert any("traceroute" in str(c).lower() for c in report["next_diagnostic_checks"])

    def test_corroborated_congestion_diagnosis(self):
        orch = MultiAgentOrchestrator()
        # Telemetry with high latency (195ms) AND high utilization (97%) AND queue drops (48 pkts/s)
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Trunk-Switch-01",
                device_type="switch",
                device_status="DEGRADED",
                latency_ms=195.0,
                packet_loss_pct=14.0,
                queue_drops_per_sec=48.0,
                utilization_pct=97.0,
                interface_in_discards=32,
                telemetry_origin="LIVE_DEVICE",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-CORROBORATED-CONGESTION")
        report = res["canonical_report"]

        # Must be confirmed with high confidence
        assert report["status"] == DiagnosticStatus.CONFIRMED
        assert "Congestion" in report["suspected_root_cause"]
        assert report["confidence"] >= 0.85

        # Recommendations must include QoS or capacity remediation
        recs = report["recommended_actions"]
        assert any("qos" in r["action"].lower() or "queue" in r["action"].lower() for r in recs)


class TestInterfaceDownDiagnosis:
    """Tests detection of interface operational down state."""

    def test_interface_down_confirmed_with_oper_status(self):
        orch = MultiAgentOrchestrator()
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Access-Switch-01",
                device_type="switch",
                device_status="DOWN",
                interface_id="GigabitEthernet0/0/2",
                interface_oper_status="DOWN",
                interface_admin_status="UP",
                packet_loss_pct=100.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-IF-DOWN")
        report = res["canonical_report"]

        assert report["status"] == DiagnosticStatus.CONFIRMED
        assert "Down" in report["suspected_root_cause"] or "Interface" in report["suspected_root_cause"]

        # Recommendations must include physical port inspection
        recs = report["recommended_actions"]
        assert any("physical" in r["action"].lower() or "port" in r["action"].lower() or "cable" in r["action"].lower() for r in recs)


class TestServiceLayerEvidenceBoundary:
    """Tests that DNS and DHCP failures are claimed ONLY when explicit service evidence exists."""

    def test_cannot_claim_dns_failure_without_dns_evidence(self):
        orch = MultiAgentOrchestrator()
        # High latency on host, but dns_response_ms is None (unmonitored)
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Host-Client-01",
                device_type="client",
                device_status="UP",
                latency_ms=250.0,
                packet_loss_pct=5.0,
                dns_response_ms=None,  # DNS NOT TESTED
                dhcp_pool_utilization_pct=None,  # DHCP NOT TESTED
                telemetry_origin="LIVE_HOST",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-NO-DNS-EVIDENCE")
        report = res["canonical_report"]

        # Must NOT conclude DNS or DHCP failure
        assert "DNS" not in report["suspected_root_cause"]
        assert "DHCP" not in report["suspected_root_cause"]

    def test_dns_failure_confirmed_with_real_dns_evidence(self):
        orch = MultiAgentOrchestrator()
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Core-DNS-01",
                device_type="dns_server",
                device_status="DEGRADED",
                latency_ms=12.0,
                dns_response_ms=3500.0,  # Explicit timeout
                dhcp_pool_utilization_pct=40.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-CONFIRMED-DNS")
        report = res["canonical_report"]

        assert report["status"] == DiagnosticStatus.CONFIRMED
        assert "DNS" in report["suspected_root_cause"] or "Services" in report["suspected_root_cause"]


class TestConflictingEvidenceResolution:
    """Tests conflict detection and resolution across contradicting signals."""

    def test_cpu_exhaustion_prevails_over_congestion_when_drops_zero(self):
        orch = MultiAgentOrchestrator()
        # High CPU (98.5%) + High Latency (180ms), but link utilization is only 15% and drops are 0
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Core-Router-01",
                device_type="router",
                device_status="DEGRADED",
                latency_ms=180.0,
                cpu_utilization_pct=98.5,
                utilization_pct=15.0,
                queue_drops_per_sec=0.0,
                interface_crc_errors=0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-CONFLICT-CPU-VS-CONGESTION")
        report = res["canonical_report"]

        # CPU starvation must be confirmed; congestion refuted
        assert report["status"] == DiagnosticStatus.CONFIRMED
        assert "CPU" in report["suspected_root_cause"] or "Processor" in report["suspected_root_cause"]

        # A conflict event should have been logged in the investigation message bus
        conflicts = [m for m in res["message_bus"] if m.get("message_type") == MessageType.CONFLICT_DETECTED.value]
        assert len(conflicts) > 0


class TestMissingAndStaleTelemetryHandling:
    """Tests graceful handling and transparent limitation reporting for missing/stale telemetry."""

    def test_empty_telemetry_returns_insufficient_evidence(self):
        orch = MultiAgentOrchestrator()
        res = orch.run_diagnosis([], incident_id="INC-EMPTY-STREAM")
        report = res["canonical_report"]

        assert report["status"] in (DiagnosticStatus.INSUFFICIENT_EVIDENCE, DiagnosticStatus.INCONCLUSIVE)
        assert report["confidence"] <= 0.40
        assert len(report["limitations"]) > 0

    def test_stale_telemetry_reported_in_limitations(self):
        orch = MultiAgentOrchestrator()
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Stale-Device-01",
                device_type="switch",
                device_status="STALE_TELEMETRY",
                latency_ms=4.0,
                packet_loss_pct=0.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-STALE-TELEMETRY")
        report = res["canonical_report"]

        assert any("stale" in lim.lower() for lim in report["limitations"])


class TestRecommendationGroundingAndApproval:
    """Tests that all recommendations are tied to evidence and risky changes require human approval."""

    def test_recommendations_tied_to_evidence(self):
        orch = MultiAgentOrchestrator()
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Trunk-Switch-01",
                device_type="switch",
                device_status="DEGRADED",
                latency_ms=190.0,
                queue_drops_per_sec=42.0,
                utilization_pct=96.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-RECOM-GROUNDING")
        report = res["canonical_report"]

        for action in report["recommended_actions"]:
            # Every action must have supporting evidence
            assert len(action["supporting_evidence"]) > 0

            # Risky changes (MEDIUM or HIGH) must require human approval
            if action["risk_level"] in ("MEDIUM", "HIGH"):
                assert action["requires_human_approval"] is True
            elif action["risk_level"] == "LOW":
                assert action["requires_human_approval"] is False

    def test_inconclusive_status_recommends_safe_diagnostics_only(self):
        orch = MultiAgentOrchestrator()
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Edge-Router-01",
                device_type="router",
                device_status="UP",
                latency_ms=180.0,
                queue_drops_per_sec=0.0,
                utilization_pct=10.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-INCONCLUSIVE-RECOMS")
        report = res["canonical_report"]

        assert report["status"] in (DiagnosticStatus.INSUFFICIENT_EVIDENCE, DiagnosticStatus.INCONCLUSIVE)
        for action in report["recommended_actions"]:
            # All actions for inconclusive cause must be safe read-only diagnostics
            assert action["risk_level"] == "LOW"
            assert action["requires_human_approval"] is False


class TestProvenancePreservation:
    """Tests that provenance tags are strictly preserved and synthetic data is never labeled live."""

    def test_live_device_provenance_preserved(self):
        orch = MultiAgentOrchestrator()
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Router-Live-01",
                device_type="router",
                device_status="UP",
                latency_ms=3.2,
                packet_loss_pct=0.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-PROVENANCE-LIVE")
        report = res["canonical_report"]

        assert report["telemetry_origin"] == "LIVE_DEVICE"
        assert res["telemetry"][0]["telemetry_origin"] == "LIVE_DEVICE"

    def test_simulated_scenario_provenance_not_masqueraded_as_live(self):
        orch = MultiAgentOrchestrator()
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Sim-Router-01",
                device_type="router",
                device_status="UP",
                latency_ms=2.5,
                packet_loss_pct=0.0,
                telemetry_origin="SIMULATED_SCENARIO",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-PROVENANCE-SIM")
        report = res["canonical_report"]

        assert report["telemetry_origin"] == "SIMULATED_SCENARIO"
        assert report["telemetry_origin"] != "LIVE_DEVICE"
        assert report["telemetry_origin"] != "LIVE_HOST"


class TestFiveAgentSwarmCollaboration:
    """Tests that all five specialized agents actively participate in end-to-end diagnosis."""

    def test_all_five_agents_participate_in_diagnosis(self):
        orch = MultiAgentOrchestrator()
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Core-Router-01",
                device_type="router",
                device_status="DEGRADED",
                latency_ms=145.0,
                packet_loss_pct=12.0,
                queue_drops_per_sec=38.0,
                utilization_pct=94.0,
                telemetry_origin="LIVE_DEVICE",
            )
        ]

        res = orch.run_diagnosis(telemetry, incident_id="INC-5AGENTS-COLLAB")
        agent_states = res.get("agent_states", [])

        # All 5 specialized agents must be present in states
        agent_ids = {a["agent_id"] for a in agent_states}
        expected_ids = {
            "perf-agent-01",
            "infra-agent-01",
            "conn-agent-01",
            "corr-agent-01",
            "recom-agent-01",
        }
        assert agent_ids == expected_ids
        assert len(res.get("timeline_events", [])) > 0
        assert len(res.get("message_bus", [])) > 0
        assert "observed_facts" in res["canonical_report"]
        assert len(res["canonical_report"]["observed_facts"]) > 0
