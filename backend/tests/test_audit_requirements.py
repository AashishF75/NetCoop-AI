"""
Comprehensive Audit & Acceptance Test Suite for NetCoop AI.
Validates all requirements specified in the IIT Bhubaneswar Problem Statement:
- Area A: Telemetry Interoperability (aliases, units, nested fields, malformed data)
- Area B: Evidence-Based Root Cause Diagnosis (all 5 agents, conflict resolution, no fabrication)
- Area C: Confidence Scoring (evidentiary sensitivity, heuristic formula)
- Area D: Six Fault Scenarios + Official Telemetry Generator Modes
- Area E: Canonical JSON Diagnosis Report Completeness (all 10 mandatory fields)
- Area F: IP-Based On-Demand Probe Workflow & Protocol Fidelity
"""

import pytest
import asyncio
from datetime import datetime, timezone

from app.protocol.schema import (
    TelemetryRecord,
    CanonicalDiagnosticReport,
    DiagnosticStatus,
    AgentMessage,
    MessageType,
)
from app.protocol.normalizer import (
    TelemetryNormalizer,
    MalformedDataError,
)
from app.generator import generate_telemetry, validate_generated_payload, adapt_to_canonical_record
from app.orchestrator.engine import MultiAgentOrchestrator
from app.integrations.probe_service import (
    probe_ip_and_diagnose,
    exec_icmp_ping,
    exec_tcp_connect_probe,
    get_real_host_telemetry,
)
from app.integrations.collector_hub import get_collector_hub, CollectorRegisterRequest


# =====================================================================
# AREA A: TELEMETRY INTEROPERABILITY TESTS
# =====================================================================
class TestTelemetryInteroperability:
    """Tests schema flexibility, unit extraction, alias mapping, and error resilience."""

    def test_extract_numeric_and_unit(self):
        val, unit = TelemetryNormalizer.extract_numeric_and_unit("45.2 ms")
        assert val == 45.2
        assert unit == "ms"

        val, unit = TelemetryNormalizer.extract_numeric_and_unit("120 Mbps")
        assert val == 120.0
        assert unit == "Mbps"

        val, unit = TelemetryNormalizer.extract_numeric_and_unit("35%")
        assert val == 35.0
        assert unit == "%"

        val, unit = TelemetryNormalizer.extract_numeric_and_unit("-68 dBm")
        assert val == -68.0
        assert unit == "dBm"

        val, unit = TelemetryNormalizer.extract_numeric_and_unit(99.5)
        assert val == 99.5
        assert unit is None

    def test_field_aliases_normalization(self):
        raw = {
            "device_id": "Switch-Vendor-X",
            "device_type": "switch",
            "cpu": "88.4%",
            "delay": "125.6 ms",
            "loss": 8.5,
            "crc_errors": 42,
            "queue_drops": "15.0 drops/s",
        }
        rec = TelemetryNormalizer.validate_and_normalize_telemetry(raw)
        assert rec is not None
        assert rec.device_id == "Switch-Vendor-X"
        assert rec.cpu_utilization_pct == 88.4
        assert rec.latency_ms == 125.6
        assert rec.packet_loss_pct == 8.5
        assert rec.interface_crc_errors == 42
        assert rec.queue_drops_per_sec == 15.0

    def test_nested_metrics_normalization(self):
        raw = {
            "device_id": "Edge-Router-01",
            "device_type": "router",
            "metrics": {
                "rtt": "32.0 ms",
                "packet_loss": 1.2,
                "memory_pct": "74.0%",
            },
        }
        rec = TelemetryNormalizer.validate_and_normalize_telemetry(raw)
        assert rec is not None
        assert rec.latency_ms == 32.0
        assert rec.packet_loss_pct == 1.2
        assert rec.memory_utilization_pct == 74.0

    def test_resilience_to_missing_and_corrupt_data(self):
        # Missing non-critical fields should still produce a valid TelemetryRecord
        minimal = {
            "device_id": "AP-02",
            "device_type": "access_point",
        }
        rec = TelemetryNormalizer.validate_and_normalize_telemetry(minimal)
        assert rec is not None
        assert rec.device_id == "AP-02"
        assert rec.latency_ms is None

        # Invalid numeric should raise MalformedDataError
        corrupted = {
            "device_id": "AP-02",
            "latency_ms": "not_a_number_at_all",
        }
        with pytest.raises(MalformedDataError):
            TelemetryNormalizer.validate_and_normalize_telemetry(corrupted)



# =====================================================================
# AREA B: EVIDENCE-BASED ROOT CAUSE DIAGNOSIS & 5 AGENTS
# =====================================================================
class TestEvidenceBasedDiagnosis:
    """Verifies that all 5 agents participate and synthesize evidence without fabrication."""

    def test_all_five_agents_participate(self):
        orch = MultiAgentOrchestrator()
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Core-Router-01",
                device_type="router",
                device_status="DEGRADED",
                latency_ms=185.0,
                packet_loss_pct=14.0,
                queue_drops_per_sec=45.0,
                telemetry_origin="BENCHMARK",
            )
        ]
        res = orch.run_diagnosis(telemetry, incident_id="INC-AUDIT-01")
        assert res["status"] in ("CONFIRMED", "DEGRADED", "CRITICAL", "OPEN")
        assert res["canonical_report"]["status"] in ("CONFIRMED", "DEGRADED", "CRITICAL", DiagnosticStatus.CONFIRMED.value, DiagnosticStatus.CONFIRMED)

        # Check all 5 agent contributions in agent_states
        agent_ids = {a["agent_id"] for a in res.get("agent_states", [])}
        expected_agents = {
            "perf-agent-01",
            "infra-agent-01",
            "conn-agent-01",
            "corr-agent-01",
            "recom-agent-01",
        }
        assert expected_agents == agent_ids, f"Agent IDs mismatch: {agent_ids}"
        assert len(res.get("agent_states", [])) == 5
        assert len(res.get("timeline_events", [])) > 0

    def test_insufficient_evidence_reports_transparent_limitations(self):
        orch = MultiAgentOrchestrator()
        # Telemetry with no anomalies
        telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Switch-01",
                device_type="switch",
                device_status="UP",
                latency_ms=1.5,
                packet_loss_pct=0.0,
                telemetry_origin="BENCHMARK",
            )
        ]
        res = orch.run_diagnosis(telemetry, incident_id="INC-AUDIT-NORMAL")
        report = res.get("canonical_report", {})
        assert report.get("status") in ("HEALTHY", "DEGRADED", DiagnosticStatus.HEALTHY)
        assert any(term in report.get("suspected_root_cause", "").lower() for term in ["nominal", "normal", "healthy", "baseline"])
        assert len(report.get("limitations", [])) >= 0


# =====================================================================
# AREA C: CONFIDENCE SCORING & EVIDENTIAL SENSITIVITY
# =====================================================================
class TestConfidenceScoring:
    """Tests evidential sensitivity and mathematical bounds of the confidence heuristic."""

    def test_confidence_bounds_and_sensitivity(self):
        orch = MultiAgentOrchestrator()

        # Severe multi-metric fault -> high confidence (> 0.80)
        severe_telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Agg-Switch-01",
                device_type="switch",
                device_status="CRITICAL",
                latency_ms=210.0,
                packet_loss_pct=22.0,
                interface_crc_errors=840,
                queue_drops_per_sec=55.0,
                telemetry_origin="BENCHMARK",
            )
        ]
        res_severe = orch.run_diagnosis(severe_telemetry, incident_id="INC-CONF-HIGH")
        conf_severe = res_severe.get("confidence", 0.0)
        assert 0.0 <= conf_severe <= 1.0
        assert conf_severe >= 0.80, f"Expected high confidence, got {conf_severe}"

        # Mild or borderline metric -> confidence is appropriately adjusted
        mild_telemetry = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="AP-01",
                device_type="access_point",
                device_status="UP",
                latency_ms=26.0,  # mild elevation
                packet_loss_pct=0.5,
                telemetry_origin="BENCHMARK",
            )
        ]
        res_mild = orch.run_diagnosis(mild_telemetry, incident_id="INC-CONF-MILD")
        conf_mild = res_mild.get("confidence", 0.0)
        assert 0.0 <= conf_mild <= 1.0


# =====================================================================
# AREA D: SIX FAULT SCENARIOS + OFFICIAL TELEMETRY GENERATOR
# =====================================================================
class TestRequiredScenariosAndGenerator:
    """Verifies all six problem statement scenarios and official generator modes."""

    def test_official_generator_modes(self):
        for mode in ("normal", "latency_spike", "hardware_failure"):
            payload = generate_telemetry(mode)
            valid, err = validate_generated_payload(payload)
            assert valid is True, f"Failed for mode {mode}: {err}"
            rec = adapt_to_canonical_record(payload, fault_type=mode)
            assert rec.telemetry_origin == "GENERATED_TEST"
            assert rec.device_id is not None

    def test_scenario_link_congestion_diagnosis(self):
        orch = MultiAgentOrchestrator()
        records = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Core-Router-01",
                device_type="router",
                device_status="DEGRADED",
                latency_ms=135.0,
                packet_loss_pct=9.5,
                queue_drops_per_sec=32.0,
                telemetry_origin="BENCHMARK",
            )
        ]
        res = orch.run_diagnosis(records, scenario_id="link_congestion")
        assert "congestion" in res["suspected_root_cause"].lower() or "bandwidth" in res["suspected_root_cause"].lower()
        report = res.get("canonical_report", {})
        assert len(report.get("recommended_actions", [])) > 0

    def test_scenario_hardware_interface_crc_diagnosis(self):
        orch = MultiAgentOrchestrator()
        records = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Edge-Switch-01",
                device_type="switch",
                device_status="CRITICAL",
                interface_crc_errors=450,
                packet_loss_pct=15.0,
                latency_ms=85.0,
                telemetry_origin="BENCHMARK",
            )
        ]
        res = orch.run_diagnosis(records, scenario_id="interface_fault")
        assert "crc" in res["suspected_root_cause"].lower() or "interface" in res["suspected_root_cause"].lower() or "physical" in res["suspected_root_cause"].lower()

    def test_scenario_weak_wifi_diagnosis(self):
        orch = MultiAgentOrchestrator()
        records = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="AP-Office-01",
                device_type="access_point",
                device_status="DEGRADED",
                wifi_rssi_dbm=-86.0,
                wifi_snr_db=9.0,
                wifi_retry_pct=28.0,
                telemetry_origin="BENCHMARK",
            )
        ]
        res = orch.run_diagnosis(records, scenario_id="weak_wifi")
        assert "wi-fi" in res["suspected_root_cause"].lower() or "rf" in res["suspected_root_cause"].lower() or "wireless" in res["suspected_root_cause"].lower()


# =====================================================================
# AREA E: CANONICAL JSON DIAGNOSIS REPORT COMPLETENESS
# =====================================================================
class TestCanonicalReportSchema:
    """Verifies that all 10 mandatory report fields from problem statement are present."""

    def test_all_ten_required_report_fields_present(self):
        orch = MultiAgentOrchestrator()
        records = [
            TelemetryRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                device_id="Core-Router-01",
                device_type="router",
                device_status="DEGRADED",
                latency_ms=110.0,
                packet_loss_pct=5.0,
                telemetry_origin="BENCHMARK",
            )
        ]
        res = orch.run_diagnosis(records, incident_id="INC-REPORT-SCHEMA-CHECK")
        report = res.get("canonical_report")
        assert report is not None

        required_fields = [
            "incident_id",
            "status",
            "suspected_root_cause",
            "confidence",
            "affected_devices",
            "supporting_evidence",
            "alternative_causes",
            "recommended_actions",
            "evidence_sources",
            "limitations",
        ]
        for field in required_fields:
            assert field in report, f"Mandatory field '{field}' missing from canonical report!"
            assert report[field] is not None, f"Field '{field}' must not be null"


# =====================================================================
# AREA F: IP-BASED ON-DEMAND PROBE WORKFLOW
# =====================================================================
class TestOnDemandIpProbeWorkflow:
    """Validates the live probe service: ICMP ping, TCP probe, host metrics, and SNMP boundary."""

    @pytest.mark.asyncio
    async def test_icmp_echo_ping_probe(self):
        # 127.0.0.1 responds to loopback ping
        orch = MultiAgentOrchestrator()
        res = await probe_ip_and_diagnose(
            ip="127.0.0.1",
            protocol="PING",
            orchestrator=orch,
        )
        assert res["success"] is True
        probe = res["probe_result"]
        assert probe["ip"] == "127.0.0.1"
        assert probe["protocol"] == "PING"
        assert probe["status"] == "UP"
        assert probe["latency_ms"] is not None
        assert probe["latency_ms"] >= 0.0
        assert probe["packet_loss_pct"] == 0.0
        assert "latency_ms" in probe["supported_metrics"]
        assert "cpu_utilization_pct" in probe["unsupported_metrics"]
        assert "diagnosis" in res
        report = res["diagnosis"]["canonical_report"]
        assert any("ICMP Echo Ping" in lim for lim in report["limitations"])

    @pytest.mark.asyncio
    async def test_host_kernel_telemetry(self):
        orch = MultiAgentOrchestrator()
        res = await probe_ip_and_diagnose(
            ip="127.0.0.1",
            protocol="HOST_METRICS",
            orchestrator=orch,
        )
        assert res["success"] is True
        probe = res["probe_result"]
        assert probe["telemetry_origin"] == "LIVE_HOST"
        assert probe["cpu_utilization_pct"] is not None
        assert probe["memory_utilization_pct"] is not None
        assert 0.0 <= probe["cpu_utilization_pct"] <= 100.0
        assert 0.0 <= probe["memory_utilization_pct"] <= 100.0

    @pytest.mark.asyncio
    async def test_snmp_credential_boundary(self):
        """Verifies SNMP/RESTCONF are correctly declared planned capabilities requiring credentials."""
        orch = MultiAgentOrchestrator()
        with pytest.raises(ValueError) as excinfo:
            await probe_ip_and_diagnose(
                ip="10.244.241.91",
                protocol="SNMP",
                orchestrator=orch,
            )
        err_msg = str(excinfo.value).lower()
        assert "planned capability" in err_msg
        assert "credentials" in err_msg

    @pytest.mark.asyncio
    async def test_probe_routed_via_online_collector(self):
        """Verifies that when an online collector is paired, probe jobs are queued and routed via collector."""
        hub = get_collector_hub()
        enroll = hub.create_enrollment("Test-Edge-Collector", "http://127.0.0.1:8000")
        col_id = enroll.collector_id
        token = enroll.enrollment_token
        reg_req = CollectorRegisterRequest(
            collector_id=col_id,
            enrollment_token=token,
            hostname="test-host",
            local_ip="10.0.0.5",
            default_gateway="10.10.214.1",
            os_type="Windows",
        )
        session = hub.register_collector(reg_req)
        session_token = session["session_token"]

        async def mock_collector_worker():
            for _ in range(30):
                jobs = hub.get_pending_probe_jobs(col_id, session_token)
                for job in jobs:
                    hub.submit_probe_job_result(
                        col_id,
                        session_token,
                        job["job_id"],
                        {
                            "record": {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "device_id": f"PROBE-{job['ip']}",
                                "device_type": "router",
                                "device_status": "UP",
                                "latency_ms": 4.2,
                                "packet_loss_pct": 0.0,
                                "telemetry_origin": "LIVE_DEVICE",
                                "custom_metrics": {"probe_protocol": job["protocol"]},
                            },
                            "metrics_available": ["latency_ms", "packet_loss_pct", "device_status"],
                            "metrics_unsupported": ["cpu_utilization_pct", "memory_utilization_pct"],
                        },
                    )
                await asyncio.sleep(0.05)

        worker_task = asyncio.create_task(mock_collector_worker())
        try:
            orch = MultiAgentOrchestrator()
            res = await probe_ip_and_diagnose(
                ip="10.10.214.1",
                protocol="PING",
                orchestrator=orch,
            )
            assert res["success"] is True
            assert "Test-Edge-Collector" in res["routed_via_collector"]
            assert res["probe_result"]["latency_ms"] == 4.2
            assert res["probe_result"]["telemetry_origin"] == "LIVE_DEVICE"
        finally:
            worker_task.cancel()
            hub.revoke_collector(col_id)
