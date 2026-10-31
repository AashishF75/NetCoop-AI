"""
Automated Unit Tests for Phase 4: Autonomous Network Intelligence.
Verifies:
1. Proactive Fault Prediction (Trend analysis, metric drift, time-to-breach, preventive warnings).
2. Insufficient History Handling (Safe fallback when historical series is sparse).
3. Cross-Incident Correlation (Grouping downstream incidents to shared upstream choke-point).
4. Explainable Health Scoring (Transparent point deductions mapped directly to SLA violations).
5. Agent Swarm Investigation Trace (Bounded rounds, termination condition, evidential consensus).
6. Scenario 9: Shared Upstream Fault (Reproducible benchmark execution).
"""

import pytest
from app.protocol.schema import (
    TelemetryRecord,
    InvestigationTerminationReason,
    IncidentPriority,
    IncidentPriorityItem,
)
from app.intelligence import (
    proactive_predictor,
    cross_incident_correlator,
    explainable_health_scorer,
)
from app.orchestrator.engine import MultiAgentOrchestrator
from app.scenarios.generator import ScenarioCatalog


def test_trend_analysis_proactive_prediction():
    """
    Verifies that multi-point telemetry time-series triggers deterministic drift calculation
    and estimates time-to-breach.
    """
    # 3-snapshot progression: CPU drifts from 55% -> 68% -> 78% (SLA is 80%)
    snap1 = [TelemetryRecord(device_id="Core-Router-01", device_type="router", cpu_utilization_pct=55.0)]
    snap2 = [TelemetryRecord(device_id="Core-Router-01", device_type="router", cpu_utilization_pct=68.0)]
    snap3 = [TelemetryRecord(device_id="Core-Router-01", device_type="router", cpu_utilization_pct=78.0)]

    warnings = proactive_predictor.analyze_trends([snap1, snap2, snap3], current_telemetry=snap3)
    assert len(warnings) > 0, "Expected proactive warning for creeping CPU"

    cpu_warn = next((w for w in warnings if w.metric == "cpu_utilization_pct"), None)
    assert cpu_warn is not None
    assert cpu_warn.device_id == "Core-Router-01"
    assert cpu_warn.drift_rate_per_min > 0
    assert cpu_warn.projected_value_10m > 78.0
    assert cpu_warn.time_to_breach_minutes > 0
    assert "CoPP" in cpu_warn.preventive_remediation or "affinity" in cpu_warn.preventive_remediation.lower() or "policing" in cpu_warn.preventive_remediation.lower()


def test_insufficient_history_handling():
    """
    Verifies that sparse historical telemetry does not generate false alarms when metrics are nominal.
    """
    # Single nominal snapshot
    snap = [TelemetryRecord(device_id="Core-Router-01", device_type="router", cpu_utilization_pct=20.0, latency_ms=2.0)]
    warnings = proactive_predictor.analyze_trends([snap], current_telemetry=snap)
    assert len(warnings) == 0, "Nominal single-snapshot should not trigger premature warnings"


def test_cross_incident_correlation_shared_upstream():
    """
    Verifies that multiple downstream degraded devices sharing an upstream aggregation switch
    are grouped into a single correlated cluster.
    """
    incidents = [
        IncidentPriorityItem(
            incident_id="INC-EDGE1",
            device_id="Edge-Switch-01",
            title="Downstream Access Latency",
            severity="WARNING",
            priority=IncidentPriority.P2,
            priority_score=68.0,
            sla_breached=True,
            affected_devices_count=1,
            affected_devices=["Edge-Switch-01"],
            service_impact="High hop delay",
            confidence=0.85,
            propagation_risk="LOW",
            suspected_root_cause="Downstream Latency",
            recommended_action="Hold action",
            status="OPEN",
        ),
        IncidentPriorityItem(
            incident_id="INC-EDGE2",
            device_id="Edge-Switch-02",
            title="Downstream Access Latency",
            severity="WARNING",
            priority=IncidentPriority.P2,
            priority_score=65.0,
            sla_breached=True,
            affected_devices_count=1,
            affected_devices=["Edge-Switch-02"],
            service_impact="Server farm link slow",
            confidence=0.85,
            propagation_risk="LOW",
            suspected_root_cause="Downstream Latency",
            recommended_action="Hold action",
            status="OPEN",
        ),
        IncidentPriorityItem(
            incident_id="INC-AGG",
            device_id="Agg-Switch-01",
            title="Transceiver CRC Corruptions",
            severity="CRITICAL",
            priority=IncidentPriority.P1,
            priority_score=92.0,
            sla_breached=True,
            affected_devices_count=4,
            affected_devices=["Agg-Switch-01", "Edge-Switch-01", "Edge-Switch-02", "AP-01"],
            service_impact="Severe CRC drops on trunk",
            confidence=0.95,
            propagation_risk="HIGH",
            suspected_root_cause="Physical Link / Transceiver Integrity Fault",
            recommended_action="Swap SFP+ optic",
            status="OPEN",
        ),
    ]

    clusters = cross_incident_correlator.correlate_incidents(incidents)
    assert len(clusters) == 1, "Expected downstream edge incidents to be clustered into 1 common upstream incident"
    cluster = clusters[0]
    assert cluster.primary_device == "Agg-Switch-01"
    assert "Edge-Switch-01" in cluster.implicated_devices
    assert "Edge-Switch-02" in cluster.implicated_devices
    assert cluster.prevented_redundant_actions >= 2


def test_explainable_health_scorer_penalties():
    """
    Verifies that health scores are 100% explainable with transparent point deduction itemization.
    """
    # 1. Test nominal network -> 100% score
    nominal_telemetry = ScenarioCatalog.generate_telemetry("normal_network")
    nom_report = explainable_health_scorer.compute_health_report(nominal_telemetry)
    assert nom_report.overall_health_score >= 95.0
    assert nom_report.status == "OPTIMAL"

    # 2. Test degraded scenario -> itemized penalties
    degraded_telemetry = ScenarioCatalog.generate_telemetry("conflicting_evidence")
    deg_report = explainable_health_scorer.compute_health_report(degraded_telemetry)
    assert deg_report.overall_health_score < 100.0

    core_breakdown = next((d for d in deg_report.device_breakdowns if d.device_id == "Core-Router-01"), None)
    assert core_breakdown is not None
    assert len(core_breakdown.penalties) > 0
    # Core-Router-01 has 99.4% CPU -> should have a penalty of 45 pts
    cpu_pen = next((p for p in core_breakdown.penalties if p.metric_name == "cpu_utilization_pct"), None)
    assert cpu_pen is not None
    assert cpu_pen.points_deducted >= 40.0
    assert "saturation" in cpu_pen.reason.lower() or "cpu" in cpu_pen.reason.lower()


def test_agent_investigation_trace_stopping_condition():
    """
    Verifies that the multi-agent orchestrator records deterministic investigation traces
    and halts with explicit termination reasons without infinite loops.
    """
    orchestrator = MultiAgentOrchestrator()
    telem = ScenarioCatalog.generate_telemetry("conflicting_evidence")

    result = orchestrator.run_diagnosis(telem, incident_id="INC-TRACE-TEST")
    assert "investigation_trace" in result
    trace = result["investigation_trace"]

    assert trace["total_rounds_executed"] <= trace["max_rounds_allowed"]
    assert trace["max_rounds_allowed"] == 2
    assert trace["termination_reason"] in [
        InvestigationTerminationReason.EVIDENTIAL_CONSENSUS.value,
        InvestigationTerminationReason.SUFFICIENT_PROOF.value,
    ]
    assert len(trace["query_priority_ranking"]) == 3
    assert "termination_explanation" in trace


def test_scenario_shared_upstream_fault():
    """
    Verifies that Scenario 9 (Shared Upstream Fault) is cataloged and produces valid multi-agent diagnosis.
    """
    meta_list = ScenarioCatalog.get_scenario_metadata()
    sc9 = next((s for s in meta_list if s["id"] == "shared_upstream_fault"), None)
    assert sc9 is not None, "Scenario 9 metadata must be registered in catalog"
    assert sc9["severity"] == "CRITICAL"

    telemetry = ScenarioCatalog.generate_telemetry("shared_upstream_fault")
    assert len(telemetry) == 6

    orchestrator = MultiAgentOrchestrator()
    diag = orchestrator.run_diagnosis(telemetry, incident_id="INC-SC9-TEST", scenario_id="shared_upstream_fault")

    assert diag["confidence"] >= 0.85
    assert "Agg-Switch-01" in diag["affected_devices"] or "Edge-Switch-01" in diag["affected_devices"]
    assert len(diag["canonical_report"]["proactive_warnings"]) > 0
