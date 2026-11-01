"""
Regression and verification test suite for Telemetry Provenance and Anti-Fabrication.

Validates:
1. Live ICMP probe with latency and packet loss only (all unmeasured metrics are None).
2. InfrastructureAgent, PerformanceAgent, and ConnectivityAgent handle None metrics
   without asserting 0-value nominal findings.
3. FaultCorrelationAgent excludes unmeasured metrics from observed_facts and hypotheses.
4. Simulated benchmark scenarios populate synthetic values with SIMULATED_SCENARIO provenance.
5. Canonical report serialization preserves None without fabricating numeric zeros.
"""

import pytest
from app.protocol.schema import (
    TelemetryRecord,
    DiagnosticStatus,
    CanonicalDiagnosticReport,
    AgentMessage,
    MessageType,
)
from app.agents.infrastructure_agent import InfrastructureAgent
from app.agents.performance_agent import PerformanceAgent
from app.agents.connectivity_agent import ConnectivityAgent
from app.agents.correlation_agent import FaultCorrelationAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.orchestrator.engine import MultiAgentOrchestrator
from app.scenarios.generator import ScenarioCatalog


class TestTelemetryProvenanceAndAntiFabrication:

    def test_live_icmp_probe_telemetry_unmeasured_fields_are_none(self):
        """
        A live ICMP echo probe measures round-trip latency and packet loss.
        All router internal metrics (CPU, memory, queues, CRC, Wi-Fi, DNS)
        MUST be strictly None and not defaulted to 0 or nominal values.
        """
        rec = TelemetryRecord(
            device_id="10.10.214.160",
            timestamp="2026-11-01T05:00:00Z",
            latency_ms=14.2,
            packet_loss_pct=0.0,
            telemetry_origin="LIVE_DEVICE",
        )

        assert rec.latency_ms == 14.2
        assert rec.packet_loss_pct == 0.0
        assert rec.telemetry_origin == "LIVE_DEVICE"

        # Strictly None - never defaulted to 0
        assert rec.cpu_utilization_pct is None
        assert rec.memory_utilization_pct is None
        assert rec.queue_drops_per_sec is None
        assert rec.interface_crc_errors is None
        assert rec.interface_flaps is None
        assert rec.interface_in_discards is None
        assert rec.interface_out_discards is None
        assert rec.utilization_pct is None
        assert rec.wifi_rssi_dbm is None
        assert rec.wifi_snr_db is None
        assert rec.wifi_retry_pct is None
        assert rec.dns_response_ms is None
        assert rec.dhcp_pool_utilization_pct is None
        assert rec.fan_status is None
        assert rec.power_supply_status is None

    def test_infrastructure_agent_handles_none_without_zero_fabrication(self):
        """
        InfrastructureAgent should NOT claim '0.0% CPU, 0.0% RAM, 0 CRC' when
        metrics are None. Findings must explicitly state metrics were not exposed.
        """
        agent = InfrastructureAgent()
        rec = TelemetryRecord(
            device_id="10.10.214.160",
            timestamp="2026-11-01T05:00:00Z",
            latency_ms=12.0,
            packet_loss_pct=0.0,
            telemetry_origin="LIVE_DEVICE",
        )

        # 1. Direct analysis should emit 0 anomalies since no threshold is breached
        anomalies = agent.analyze([rec])
        assert len(anomalies) == 0

        # 2. Query response should clearly document that metrics were not exposed
        query = AgentMessage(
            message_type=MessageType.QUERY_EVIDENCE,
            agent_id="test-correlation",
            device_id="10.10.214.160",
            correlation_id="corr-1",
        )
        response = agent.handle_query(query, [rec])
        assert response.value["cpu_utilization_pct"] is None
        assert response.value["memory_utilization_pct"] is None
        assert response.value["crc_errors"] is None

        # Check findings message does NOT claim 0.0% CPU or 0 CRC
        finding_text = " ".join(response.findings)
        assert "not exposed on this probe" in finding_text
        assert "0.0% CPU" not in finding_text
        assert "CRC: 0" not in finding_text

    def test_performance_agent_handles_none_without_zero_fabrication(self):
        """
        PerformanceAgent should NOT assert congestion or zero drops when
        queue_drops_per_sec is None.
        """
        agent = PerformanceAgent()
        rec = TelemetryRecord(
            device_id="10.10.214.160",
            timestamp="2026-11-01T05:00:00Z",
            latency_ms=250.0,  # Critical latency
            packet_loss_pct=2.0,
            telemetry_origin="LIVE_DEVICE",
            # queue_drops_per_sec is None
            # utilization_pct is None
        )

        anomalies = agent.analyze([rec])
        lat_anom = next((a for a in anomalies if a.metric == "latency_ms"), None)
        assert lat_anom is not None

        # Evidence should preserve None for queue drops and utilization
        assert lat_anom.evidence["queue_drops_per_sec"] is None
        assert lat_anom.evidence["utilization_pct"] is None
        assert lat_anom.evidence["congestion_corroborated"] is False

        # Findings must explain that drops and utilization were not exposed
        finding_text = " ".join(lat_anom.findings)
        assert "were not exposed" in finding_text
        assert "High ping latency alone does NOT confirm congestion" in finding_text

        # Query response check
        query = AgentMessage(
            message_type=MessageType.QUERY_EVIDENCE,
            agent_id="test-correlation",
            device_id="10.10.214.160",
            correlation_id="corr-2",
        )
        q_resp = agent.handle_query(query, [rec])
        assert q_resp.evidence["queue_drops_per_sec"] is None
        assert q_resp.evidence["utilization_pct"] is None
        q_finding = " ".join(q_resp.findings)
        assert "were not exposed" in q_finding

    def test_connectivity_agent_handles_none_without_false_claims(self):
        """
        ConnectivityAgent should report that wireless RF and DNS/DHCP metrics
        were not collected, rather than assuming 0ms DNS response or 0% retries.
        """
        agent = ConnectivityAgent()
        rec = TelemetryRecord(
            device_id="10.10.214.160",
            timestamp="2026-11-01T05:00:00Z",
            latency_ms=10.0,
            packet_loss_pct=0.0,
            telemetry_origin="LIVE_DEVICE",
        )

        anomalies = agent.analyze([rec])
        assert len(anomalies) == 0

        query = AgentMessage(
            message_type=MessageType.QUERY_EVIDENCE,
            agent_id="test-correlation",
            device_id="10.10.214.160",
            correlation_id="corr-3",
        )
        q_resp = agent.handle_query(query, [rec])
        assert q_resp.value["rssi_dbm"] is None
        assert q_resp.value["dns_response_ms"] is None
        assert q_resp.value["dns_evidence_available"] is False
        assert q_resp.value["dhcp_evidence_available"] is False

        finding_text = " ".join(q_resp.findings)
        assert "Wireless RF and DNS/DHCP service metrics were not collected on this probe" in finding_text

    def test_fault_correlation_agent_excludes_unmeasured_metrics_from_observed_facts(self):
        """
        FaultCorrelationAgent must only include measured facts in observed_facts,
        and competing hypotheses must accurately report when protocol metrics
        were unexposed.
        """
        corr = FaultCorrelationAgent()
        rec = TelemetryRecord(
            device_id="10.10.214.160",
            timestamp="2026-11-01T05:00:00Z",
            latency_ms=15.0,
            packet_loss_pct=0.0,
            telemetry_origin="LIVE_DEVICE",
        )

        corr._extract_observed_facts([rec])
        # Latency and loss must be in observed_facts
        assert any("15.0 ms" in fact and "latency" in fact.lower() for fact in corr.observed_facts)
        assert any("Measured packet loss is 0.0%" in fact for fact in corr.observed_facts)

        # Unmeasured metrics MUST NOT appear in observed_facts
        assert not any("CPU load is" in fact for fact in corr.observed_facts)
        assert not any("memory allocation is" in fact for fact in corr.observed_facts)
        assert not any("CRC frame errors" in fact for fact in corr.observed_facts)
        assert not any("queue drop rate" in fact for fact in corr.observed_facts)
        assert not any("DNS query resolution" in fact for fact in corr.observed_facts)
        assert not any("Wireless RF signal" in fact for fact in corr.observed_facts)

    def test_end_to_end_orchestration_live_icmp_probe_preserves_provenance(self):
        """
        Full 5-agent swarm diagnosis of a live ICMP probe:
        - Result status is NOMINAL (or appropriate)
        - Telemetry origin is preserved as LIVE_DEVICE
        - Serialized telemetry preserves None for unmeasured metrics (no zeros)
        - Canonical report limitations note unexposed dimensions
        """
        orch = MultiAgentOrchestrator()
        live_record = TelemetryRecord(
            device_id="10.10.214.160",
            timestamp="2026-11-01T05:00:00Z",
            latency_ms=18.4,
            packet_loss_pct=0.0,
            telemetry_origin="LIVE_DEVICE",
        )

        result = orch.run_diagnosis(
            telemetry=[live_record],
            incident_id="INC-LIVE-TEST-001",
        )

        assert result["telemetry_origin"] == "LIVE_DEVICE"
        assert result["canonical_report"]["telemetry_origin"] == "LIVE_DEVICE"
        assert result["status"] == "HEALTHY"
        assert "Normal Network Operation" in result["suspected_root_cause"]

        # Check serialized telemetry records
        serialized_rec = result["telemetry"][0]
        assert serialized_rec["latency_ms"] == 18.4
        assert serialized_rec["packet_loss_pct"] == 0.0
        assert serialized_rec["cpu_utilization_pct"] is None
        assert serialized_rec["queue_drops_per_sec"] is None
        assert serialized_rec["interface_crc_errors"] is None
        assert serialized_rec["wifi_rssi_dbm"] is None
        assert serialized_rec["dns_response_ms"] is None

        # Limitations must record unexposed dimensions
        limitations = result["canonical_report"]["limitations"]
        assert any("missing critical telemetry dimensions" in lim for lim in limitations)

    def test_simulated_scenario_populates_synthetic_values_with_proper_provenance(self):
        """
        Simulated scenarios (e.g. link_congestion, normal_network) from
        ScenarioCatalog have SIMULATED_SCENARIO provenance and populate
        their respective synthetic benchmark values.
        """
        records = ScenarioCatalog.generate_telemetry("link_congestion")
        assert len(records) > 0

        for r in records:
            assert r.telemetry_origin == "SIMULATED_SCENARIO"

        # Verify that congested record has synthetic utilization and drops
        congested_records = [r for r in records if r.utilization_pct and r.utilization_pct > 80.0]
        assert len(congested_records) > 0
        assert congested_records[0].queue_drops_per_sec is not None
        assert congested_records[0].queue_drops_per_sec > 0.0

    def test_live_icmp_high_rtt_does_not_fabricate_zero_metrics_or_refute_hypotheses(self):
        """
        Exact regression test for judge-provided private IP 10.10.214.160 probed via ICMP:
        - Measured RTT: 927.0 ms, Packet loss: 0%
        - CPU, memory, queues, CRC, Wi-Fi, DNS are unsupported / None
        Verifies:
        1. Result status is INCONCLUSIVE (or INSUFFICIENT_EVIDENCE) with low confidence (<= 45%).
        2. No false conflict resolution (e.g. CONGESTION_REFUTED_BY_ZERO_DROPS) is triggered.
        3. Alternative hypotheses for unmeasured dimensions are marked NOT EVALUATED (not REFUTED).
        4. No fabricated zero values (0% CPU, 0 queue drops, 0 CRC, -50 dBm RSSI) appear in rationales.
        5. Assumptions explicitly indicate live telemetry, not benchmark digital twin simulation.
        """
        orch = MultiAgentOrchestrator()
        live_record = TelemetryRecord(
            device_id="10.10.214.160",
            timestamp="2026-11-01T05:00:00Z",
            latency_ms=927.0,
            packet_loss_pct=0.0,
            telemetry_origin="LIVE_DEVICE",
        )

        result = orch.run_diagnosis(
            telemetry=[live_record],
            incident_id="INC-LIVE-HIGH-RTT-001",
        )

        assert result["status"] in ("INCONCLUSIVE", "INSUFFICIENT_EVIDENCE")
        assert result["confidence"] <= 0.45
        assert result["telemetry_origin"] == "LIVE_DEVICE"

        cr = result["canonical_report"]
        assert cr["conflict_status"] == "NO_CONFLICT"

        # Check alternative causes (hypotheses)
        alt_causes = {h["hypothesis_id"]: h for h in cr["alternative_causes"]}
        
        # 1. Congestion
        assert "HYP-CONGESTION" in alt_causes
        h_cong = alt_causes["HYP-CONGESTION"]
        assert h_cong["status"] == "NOT EVALUATED"
        assert "not exposed" in h_cong["reasoning"].lower() or "unsupported" in h_cong["reasoning"].lower()
        assert "0.0 pkts/s" not in h_cong["reasoning"]
        assert "utilization is 0" not in h_cong["reasoning"].lower()

        # 2. CPU Starvation
        assert "HYP-CPU-STARVATION" in alt_causes
        h_cpu = alt_causes["HYP-CPU-STARVATION"]
        assert h_cpu["status"] == "NOT EVALUATED"
        assert "0.0%" not in h_cpu["reasoning"]
        assert "not exposed" in h_cpu["reasoning"].lower() or "unsupported" in h_cpu["reasoning"].lower()

        # 3. Interface Fault
        assert "HYP-INTERFACE-FAULT" in alt_causes
        h_if = alt_causes["HYP-INTERFACE-FAULT"]
        assert h_if["status"] == "NOT EVALUATED"
        assert "0 CRC" not in h_if["reasoning"]
        assert "not exposed" in h_if["reasoning"].lower() or "unsupported" in h_if["reasoning"].lower()

        # 4. Interface Down
        assert "HYP-INTERFACE-DOWN" in alt_causes
        h_down = alt_causes["HYP-INTERFACE-DOWN"]
        assert h_down["status"] == "NOT EVALUATED"
        assert "UP" not in h_down["reasoning"]
        assert "not exposed" in h_down["reasoning"].lower()

        # 5. Wireless RF
        assert "HYP-WIFI-RF" in alt_causes
        h_wifi = alt_causes["HYP-WIFI-RF"]
        assert h_wifi["status"] == "NOT EVALUATED"
        assert "-50 dBm" not in h_wifi["reasoning"]
        assert "wireless rf" in h_wifi["reasoning"].lower()
        assert "not collected" in h_wifi["reasoning"].lower() or "unsupported" in h_wifi["reasoning"].lower()

        # 6. DNS/DHCP
        assert "HYP-DNS-DHCP-OUTAGE" in alt_causes
        h_dns = alt_causes["HYP-DNS-DHCP-OUTAGE"]
        assert h_dns["status"] == "NOT EVALUATED"
        assert "dns" in h_dns["reasoning"].lower()
        assert "not exposed" in h_dns["reasoning"].lower() or "not collected" in h_dns["reasoning"].lower() or "unsupported" in h_dns["reasoning"].lower()

        # Check observed facts: only measured latency and loss appear, no 0-values for missing metrics
        facts = cr.get("observed_facts", [])
        facts_text = " ".join(facts)
        assert "927.0 ms" in facts_text
        assert "0.0%" in facts_text
        assert "CPU load is" not in facts_text
        assert "CRC frame errors" not in facts_text
        assert "queue drop rate" not in facts_text

        # Check assumptions & limitations
        expl = cr.get("investigation_explanation", {})
        assumptions = expl.get("assumptions_and_limitations", [])
        assump_text = " ".join(assumptions)
        assert "benchmark digital twin simulation environment" not in assump_text
        assert "live" in assump_text.lower()
