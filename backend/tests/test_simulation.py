"""
Automated Unit Tests for Network Digital Twin and What-If Remediation Simulator.
IIT Bhubaneswar Agentic AI Grand Finale — NetCoop AI.
"""

import pytest
from app.protocol.schema import (
    TelemetryRecord,
    DiagnosticStatus,
    SLAStatus,
    DeviceOperationalStatus,
    IncidentPriority,
)
from app.simulator.twin import digital_twin_engine, DEVICE_DEPENDENCY_GRAPH
from app.simulator.engine import remediation_simulator
from app.simulator.prioritizer import incident_prioritizer
from app.orchestrator.engine import MultiAgentOrchestrator
from app.scenarios.generator import ScenarioCatalog


@pytest.fixture
def orchestrator():
    return MultiAgentOrchestrator()


def test_digital_twin_topology_and_dependencies():
    """Verify Digital Twin accurately models topology devices and upstream/downstream dependency hierarchy."""
    snapshot = digital_twin_engine.build_snapshot([])
    assert snapshot.environment_mode == "BENCHMARK_DIGITAL_TWIN_SIMULATION"
    assert len(snapshot.devices) == len(DEVICE_DEPENDENCY_GRAPH)
    
    device_map = {d.device_id: d for d in snapshot.devices}
    assert "Core-Router-01" in device_map
    assert "Agg-Switch-01" in device_map
    assert "AP-01" in device_map

    # Upstream / downstream hierarchy
    core = device_map["Core-Router-01"]
    assert core.upstream_dependencies == []
    assert "Agg-Switch-01" in core.downstream_dependencies

    agg = device_map["Agg-Switch-01"]
    assert "Core-Router-01" in agg.upstream_dependencies
    assert "Edge-Switch-01" in agg.downstream_dependencies


def test_digital_twin_health_and_sla_scoring():
    """Verify health score and SLA calculations on degraded telemetry."""
    bad_telemetry = [
        TelemetryRecord(
            device_id="Core-Router-01",
            cpu_utilization_pct=99.4,
            latency_ms=115.0,
            packet_loss_pct=4.2,
        )
    ]
    snapshot = digital_twin_engine.build_snapshot(bad_telemetry)
    core = next(d for d in snapshot.devices if d.device_id == "Core-Router-01")
    
    assert core.status in [DeviceOperationalStatus.WARNING, DeviceOperationalStatus.CRITICAL]
    assert core.sla_status == SLAStatus.BREACHED
    assert core.health_score < 50.0
    assert len(core.active_anomalies) >= 2


def test_what_if_remediation_simulation_deterministic():
    """Verify deterministic What-If simulation calculates correct deltas, recovery status, and risk assessments."""
    strategies = remediation_simulator.get_candidate_strategies(
        root_cause="Control Plane Processor Saturation",
        target_device="Core-Router-01",
    )
    assert len(strategies) == 3
    strat_a = strategies[0]  # CoPP Rate-Limiting
    assert strat_a.strategy_id == "strat-copp-01"
    assert strat_a.operational_risk == "LOW"
    assert strat_a.recovery_time_seconds == 15

    current_telem = {
        "cpu_utilization_pct": 99.4,
        "latency_ms": 115.0,
        "packet_loss_pct": 4.2,
        "utilization_pct": 14.0,
        "queue_drops_per_sec": 0.0,
    }

    result = remediation_simulator.run_simulation(
        incident_id="INC-TEST-01",
        strategy=strat_a,
        current_telemetry=current_telem,
        target_device="Core-Router-01",
    )

    assert result.strategy_id == "strat-copp-01"
    assert result.projected_telemetry["cpu_utilization_pct"] == 24.5
    assert result.projected_telemetry["latency_ms"] == 5.8
    assert result.recovery_status == "FULL_RECOVERY"
    assert result.sla_status_after == "COMPLIANT"
    assert result.device_health_after > result.device_health_before

    # Verify deltas
    cpu_delta = result.telemetry_deltas["cpu_utilization_pct"]
    assert cpu_delta["before"] == 99.4
    assert cpu_delta["after"] == 24.5
    assert cpu_delta["delta"] == -74.9
    assert cpu_delta["status"] == "IMPROVED"

    assert len(result.assumptions) >= 2
    assert len(result.limitations) >= 1


def test_strategy_comparison_matrix():
    """Verify side-by-side strategy trade-off comparison matrix."""
    matrix = remediation_simulator.generate_comparison_matrix(
        incident_id="INC-TEST-02",
        target_device="Core-Router-01",
        root_cause="Control Plane Processor Saturation",
    )
    assert len(matrix.strategies) == 3
    assert matrix.recommended_strategy_id == "strat-copp-01"
    assert "lowest operational risk" in matrix.recommendation_rationale.lower()
    
    # Check that alternative strategies present realistic trade-offs
    strat_c = next(s for s in matrix.strategies if s.operational_risk == "HIGH")
    assert strat_c.recovery_time_seconds > matrix.strategies[0].recovery_time_seconds


def test_multi_incident_prioritization_ordering():
    """Verify incidents are ranked deterministically by priority score."""
    items = incident_prioritizer.prioritize_incidents()
    assert len(items) >= 4

    # Verify sorted descending
    scores = [item.priority_score for item in items]
    assert scores == sorted(scores, reverse=True)

    # Core Router high-severity incident must rank higher than localized Wi-Fi RF issue
    p1_items = [item for item in items if item.priority == IncidentPriority.P1]
    assert len(p1_items) >= 1
    assert p1_items[0].device_id == "Core-Router-01"
    assert p1_items[0].sla_breached is True


def test_investigation_explanation_generation(orchestrator):
    """Verify structured InvestigationExplanation is attached to report explaining swarm reasoning."""
    telem = ScenarioCatalog.generate_telemetry("conflicting_evidence")
    result = orchestrator.run_diagnosis(telem, incident_id="INC-TEST-EXPLAIN")

    report = result["canonical_report"]
    explanation = report.get("investigation_explanation")
    assert explanation is not None

    assert len(explanation["initial_symptoms"]) > 0
    assert len(explanation["initial_hypotheses"]) > 0
    assert len(explanation["inter_agent_queries"]) > 0
    assert len(explanation["supporting_evidence"]) > 0
    assert len(explanation["refuting_evidence"]) > 0
    assert "consensus" in explanation["final_resolution"].lower()
    assert len(explanation["assumptions_and_limitations"]) > 0


def test_remediation_strategies_for_link_congestion():
    """Verify deterministic strategies for link congestion scenario."""
    strategies = remediation_simulator.get_candidate_strategies(
        root_cause="Egress Link Buffer Congestion",
        target_device="Agg-Switch-01",
    )
    assert len(strategies) == 3
    names = [s.name for s in strategies]
    assert any("QoS" in n or "WRED" in n for n in names)
    assert any("ECMP" in n or "Deflection" in n for n in names)
    assert any("LACP" in n or "Aggregation" in n for n in names)

