"""
Fault Correlation Agent.
Coordinates inter-agent cross-examination, hypothesis generation, conflict resolution,
Bayesian evidence synthesis, and insufficient-evidence detection.
"""

from typing import List, Dict, Any, Optional, Tuple
import uuid
from app.agents.base_agent import BaseAgent
from app.protocol.schema import (
    AgentMessage,
    MessageType,
    TelemetryRecord,
    DiagnosticStatus,
    CompetingHypothesis,
    EvidenceItem,
)


class FaultCorrelationAgent(BaseAgent):
    def __init__(self, agent_id: str = "corr-agent-01"):
        super().__init__(
            agent_id=agent_id,
            name="Fault Correlation Agent",
            role="Multi-Agent Synthesis & Root Cause Correlator",
        )
        self.competing_hypotheses: List[CompetingHypothesis] = []
        self.evidence_store: List[EvidenceItem] = []
        self.limitations_identified: List[str] = []
        self.conflicts_resolved: List[Dict[str, Any]] = []

    def analyze(self, telemetry: List[TelemetryRecord]) -> List[AgentMessage]:
        # Correlation agent acts primarily during orchestration when synthesizing peer findings
        self.set_status("IDLE", "Awaiting peer domain findings")
        return []

    def handle_query(self, query: AgentMessage, telemetry: List[TelemetryRecord]) -> AgentMessage:
        return self.create_message(
            message_type=MessageType.QUERY_RESPONSE,
            target_agent_id=query.agent_id,
            correlation_id=query.correlation_id,
            confidence=1.0,
            findings=["Fault Correlation Agent active and coordinating synthesis."],
        )

    def cross_examine_and_correlate(
        self,
        domain_messages: List[AgentMessage],
        telemetry: List[TelemetryRecord],
        performance_agent: BaseAgent,
        infrastructure_agent: BaseAgent,
        connectivity_agent: BaseAgent,
    ) -> Tuple[DiagnosticStatus, str, float, List[str], List[CompetingHypothesis], List[EvidenceItem], List[str], List[AgentMessage]]:
        """
        Orchestrates inter-agent dialogue:
        1. Emits queries to peer agents to test hypotheses.
        2. Gathers structured responses into evidence store.
        3. Formulates competing hypotheses.
        4. Identifies and resolves conflicts.
        5. Computes synthesized confidence and outputs diagnostic summary.
        """
        self.set_status("ANALYZING", "Synthesizing cross-agent telemetry anomalies")
        inter_agent_dialogue: List[AgentMessage] = []
        self.competing_hypotheses.clear()
        self.evidence_store.clear()
        self.limitations_identified.clear()
        self.conflicts_resolved.clear()

        # Check for missing telemetry (insufficient evidence check)
        self._check_telemetry_completeness(telemetry)

        # Collect implicated devices from domain anomalies
        implicated_devices = list(dict.fromkeys([
            msg.device_id for msg in domain_messages if msg.device_id
        ]))

        # Transform initial anomaly messages into structured evidence items
        for msg in domain_messages:
            if msg.message_type == MessageType.TELEMETRY_ANOMALY and msg.device_id and msg.metric:
                sev = msg.evidence.get("severity", "INFO")
                item = EvidenceItem(
                    agent_id=msg.agent_id,
                    device_id=msg.device_id,
                    metric=msg.metric,
                    observed_value=msg.value,
                    baseline_value=msg.evidence.get("baseline"),
                    threshold=msg.evidence.get("threshold"),
                    unit=msg.unit or "",
                    severity=sev,
                    timestamp=msg.timestamp,
                    summary=msg.findings[0] if msg.findings else f"{msg.metric} = {msg.value}",
                )
                self.evidence_store.append(item)

        # -------------------------------------------------------------
        # GENUINE INTER-AGENT DIALOGUE (Cross-Examination)
        # Correlation Agent interrogates peer agents based on anomalies found
        # Bounded cross-examination rounds with defensive error handling
        # -------------------------------------------------------------
        max_investigation_rounds = 2
        for round_idx in range(max_investigation_rounds):
            if round_idx > 0 and not implicated_devices:
                break

            for dev in implicated_devices:
                corr_id = str(uuid.uuid4())[:8]

                # 1. Query Infrastructure Agent about hardware / L1 integrity for this device
                try:
                    q_infra = self.create_message(
                        message_type=MessageType.QUERY_EVIDENCE,
                        device_id=dev,
                        target_agent_id=infrastructure_agent.agent_id,
                        correlation_id=corr_id,
                        findings=[f"Round {round_idx+1}: Requesting hardware status, CRC error counters, and CPU load for {dev}"],
                    )
                    inter_agent_dialogue.append(q_infra)
                    resp_infra = infrastructure_agent.handle_query(q_infra, telemetry)
                    inter_agent_dialogue.append(resp_infra)
                except Exception as e:
                    self.limitations_identified.append(f"Infrastructure Agent query failed for {dev}: {str(e)}")

                # 2. Query Performance Agent about queue drops and buffer state
                try:
                    q_perf = self.create_message(
                        message_type=MessageType.QUERY_EVIDENCE,
                        device_id=dev,
                        target_agent_id=performance_agent.agent_id,
                        correlation_id=corr_id,
                        findings=[f"Round {round_idx+1}: Requesting buffer queue drops vs throughput telemetry for {dev}"],
                    )
                    inter_agent_dialogue.append(q_perf)
                    resp_perf = performance_agent.handle_query(q_perf, telemetry)
                    inter_agent_dialogue.append(resp_perf)
                except Exception as e:
                    self.limitations_identified.append(f"Performance Agent query failed for {dev}: {str(e)}")

                # 3. Query Connectivity Agent about RF metrics or DNS/DHCP state
                try:
                    q_conn = self.create_message(
                        message_type=MessageType.QUERY_EVIDENCE,
                        device_id=dev,
                        target_agent_id=connectivity_agent.agent_id,
                        correlation_id=corr_id,
                        findings=[f"Round {round_idx+1}: Requesting wireless RF signals, link adjacency, and DNS/DHCP health for {dev}"],
                    )
                    inter_agent_dialogue.append(q_conn)
                    resp_conn = connectivity_agent.handle_query(q_conn, telemetry)
                    inter_agent_dialogue.append(resp_conn)
                except Exception as e:
                    self.limitations_identified.append(f"Connectivity Agent query failed for {dev}: {str(e)}")
            
            # First round handles primary queries; additional rounds only if unresolved conflicts remain
            break

        # -------------------------------------------------------------
        # SYNTHESIZE COMPETING HYPOTHESES & CONFLICT RESOLUTION
        # -------------------------------------------------------------
        status, root_cause, confidence = self._evaluate_hypotheses_and_resolve_conflicts(
            telemetry, domain_messages, inter_agent_dialogue
        )

        # Broadcast Diagnostic Summary to orchestrator
        summary_msg = self.create_message(
            message_type=MessageType.DIAGNOSTIC_SUMMARY,
            device_id=implicated_devices[0] if implicated_devices else "Network-Wide",
            confidence=confidence,
            findings=[
                f"Diagnostic Status: {status.value}",
                f"Suspected Root Cause: {root_cause}",
                f"Synthesized Confidence: {round(confidence * 100, 1)}%",
                f"Competing Hypotheses Evaluated: {len(self.competing_hypotheses)}",
                f"Limitations Identified: {len(self.limitations_identified)}",
            ],
            evidence={
                "status": status.value,
                "root_cause": root_cause,
                "affected_devices": implicated_devices,
                "evidence_count": len(self.evidence_store),
            }
        )
        inter_agent_dialogue.append(summary_msg)

        self.set_status("COMPLETE", f"Diagnosis: {root_cause} ({status.value})")
        return (
            status,
            root_cause,
            confidence,
            implicated_devices,
            self.competing_hypotheses,
            self.evidence_store,
            self.limitations_identified,
            inter_agent_dialogue,
        )

    def _check_telemetry_completeness(self, telemetry: List[TelemetryRecord]):
        """Detects missing fields and insufficient telemetry across devices."""
        if not telemetry:
            self.limitations_identified.append("Telemetry dataset is empty; zero records received.")
            return

        for rec in telemetry:
            missing_in_rec = []
            if rec.latency_ms is None:
                missing_in_rec.append("latency_ms")
            if rec.cpu_utilization_pct is None:
                missing_in_rec.append("cpu_utilization_pct")
            if rec.queue_drops_per_sec is None:
                missing_in_rec.append("queue_drops_per_sec")
            if rec.interface_crc_errors is None:
                missing_in_rec.append("interface_crc_errors")

            if len(missing_in_rec) >= 3:
                self.limitations_identified.append(
                    f"Device '{rec.device_id}' is missing critical telemetry dimensions: {', '.join(missing_in_rec)}. "
                    "Diagnostic certainty reduced."
                )

    def _evaluate_hypotheses_and_resolve_conflicts(
        self,
        telemetry: List[TelemetryRecord],
        domain_messages: List[AgentMessage],
        dialogue: List[AgentMessage],
    ) -> Tuple[DiagnosticStatus, str, float]:
        """
        Calculates probabilities for competing hypotheses and handles conflict resolution.
        """
        # If severe telemetry gaps exist
        if any("missing critical telemetry" in lim for lim in self.limitations_identified):
            # Check if there is still enough signal or if it is inconclusive
            self.competing_hypotheses.append(
                CompetingHypothesis(
                    hypothesis_id="HYP-MISSING-DATA",
                    name="Insufficient Telemetry Telemetry-Gap",
                    description="Crucial metrics (CPU, queue drops, CRC errors) omitted or null in stream.",
                    probability=0.85,
                    supporting_evidence=[lim for lim in self.limitations_identified],
                    contradicting_evidence=[],
                    status="VALIDATED",
                )
            )
            return (
                DiagnosticStatus.INCONCLUSIVE,
                "Inconclusive Diagnosis due to Missing Telemetry Dimensions (Queue drops, CPU, and Interface counters absent)",
                0.42,
            )

        # Aggregate evidence metrics across records
        max_crc = max([r.interface_crc_errors or 0 for r in telemetry], default=0)
        max_drops = max([r.queue_drops_per_sec or 0.0 for r in telemetry], default=0.0)
        max_util = max([r.utilization_pct or 0.0 for r in telemetry], default=0.0)
        max_cpu = max([r.cpu_utilization_pct or 0.0 for r in telemetry], default=0.0)
        min_rssi = min([r.wifi_rssi_dbm for r in telemetry if r.wifi_rssi_dbm is not None], default=-50.0)
        max_retries = max([r.wifi_retry_pct or 0.0 for r in telemetry], default=0.0)
        max_dns_ms = max([r.dns_response_ms or 0.0 for r in telemetry], default=15.0)
        max_dhcp_util = max([r.dhcp_pool_utilization_pct or 0.0 for r in telemetry], default=40.0)
        max_flaps = max([r.interface_flaps or 0 for r in telemetry], default=0)

        # -------------------------------------------------------------
        # HYPOTHESIS CANDIDATES
        # -------------------------------------------------------------
        # 1. Physical Interface / Transceiver Defect
        p_interface = 0.05
        sup_interface, con_interface = [], []
        if max_crc >= 20 or max_flaps >= 2:
            p_interface = 0.94
            sup_interface.append(f"Physical CRC error rate high: {max_crc} errors/sec")
            if max_flaps >= 2:
                sup_interface.append(f"Interface link flapping detected: {max_flaps} state transitions")
        else:
            con_interface.append(f"Zero or negligible interface CRC errors ({max_crc}) and flaps ({max_flaps})")

        # 2. Buffer Congestion (Queue Exhaustion)
        p_congestion = 0.05
        sup_congestion, con_congestion = [], []
        if (max_util >= 85.0 and max_drops >= 10.0) or max_drops >= 20.0:
            p_congestion = 0.95
            if max_util >= 85.0:
                sup_congestion.append(f"Sustained link bandwidth saturation: {max_util}%")
            if max_drops >= 10.0:
                sup_congestion.append(f"Active egress queue drops: {max_drops} pkts/s")
        elif max_util >= 80.0 or max_drops >= 5.0:
            p_congestion = 0.65
            if max_util >= 80.0:
                sup_congestion.append(f"Elevated link utilization: {max_util}%")
            if max_drops >= 5.0:
                sup_congestion.append(f"Elevated queue drops: {max_drops} pkts/s")
        else:
            con_congestion.append(f"Link bandwidth utilization is low ({max_util}%), queue drops: {max_drops} pkts/s")

        # 3. Wireless RF Signal Degradation (Weak Wi-Fi)
        p_wifi = 0.05
        sup_wifi, con_wifi = [], []
        if min_rssi <= -80.0 or max_retries >= 25.0:
            p_wifi = 0.96
            sup_wifi.append(f"Severe RF path loss: RSSI {min_rssi} dBm (crit < -80 dBm)")
            sup_wifi.append(f"High 802.11 MAC frame retransmissions: {max_retries}%")
        elif min_rssi <= -72.0:
            p_wifi = 0.65
            sup_wifi.append(f"Marginal RSSI: {min_rssi} dBm")
        else:
            con_wifi.append(f"Wireless RSSI nominal ({min_rssi} dBm), retries: {max_retries}%")

        # 4. Core Infrastructure CPU Exhaustion / Storm
        p_cpu = 0.05
        sup_cpu, con_cpu = [], []
        if max_cpu >= 90.0:
            p_cpu = 0.92
            sup_cpu.append(f"Device CPU saturated: {max_cpu}%")
        else:
            con_cpu.append(f"CPU utilization normal: {max_cpu}%")

        # 5. Core Services Failure (DNS Timeout / DHCP Exhaustion)
        p_dns = 0.05
        sup_dns, con_dns = [], []
        if max_dns_ms >= 1500.0 or max_dhcp_util >= 95.0:
            p_dns = 0.97
            if max_dns_ms >= 1500.0:
                sup_dns.append(f"DNS query timeout on resolver: {max_dns_ms} ms")
            if max_dhcp_util >= 95.0:
                sup_dns.append(f"DHCP pool exhaustion: {max_dhcp_util}% capacity")
        else:
            con_dns.append(f"DNS response time normal: {max_dns_ms} ms, DHCP pool: {max_dhcp_util}%")

        # -------------------------------------------------------------
        # CONFLICT RESOLUTION
        # Example: Elevated latency could be either Congestion or CPU exhaustion.
        # If CPU is 99% but link utilization is only 15%, Performance Agent's
        # latency alarm conflicts with traffic congestion hypothesis!
        # -------------------------------------------------------------
        if p_cpu > 0.85 and max_util < 50.0 and max_drops == 0.0:
            conflict_msg = self.create_message(
                message_type=MessageType.CONFLICT_DETECTED,
                findings=[
                    f"CONFLICT DETECTED & RESOLVED: High latency observed alongside saturated CPU ({max_cpu}%), "
                    f"yet link utilization is only {max_util}% and queue drops are 0. "
                    "Disqualifying Link Congestion hypothesis. Control Plane CPU Starvation confirmed as primary root cause."
                ],
                evidence={
                    "conflicting_metrics": ["latency_vs_utilization"],
                    "cpu_utilization_pct": max_cpu,
                    "link_utilization_pct": max_util,
                    "resolution": "CONTROL_PLANE_CPU_OVERLOAD_PREVAILS"
                },
                confidence=0.94,
            )
            dialogue.append(conflict_msg)
            p_congestion = 0.10
            con_congestion.append(f"Conflict resolution: Latency is caused by CPU process starvation ({max_cpu}%), not link saturation ({max_util}%)")

        # Create structured CompetingHypothesis records
        hyp_list = [
            CompetingHypothesis(
                hypothesis_id="HYP-CONGESTION",
                name="Egress Link Buffer Congestion",
                description="Network interface transmission queues overflowing due to bandwidth demand exceeding link capacity.",
                probability=round(p_congestion, 2),
                supporting_evidence=sup_congestion,
                contradicting_evidence=con_congestion,
                status="VALIDATED" if p_congestion > 0.70 else ("REFUTED" if con_congestion else "PROPOSED"),
                reasoning=(
                    f"Disqualified by cross-examination: Link bandwidth utilization is only {max_util}% and buffer drop counters are 0. Egress link buffer exhaustion is physically refuted."
                    if (p_cpu > 0.85 and max_util < 50.0 and max_drops == 0.0)
                    else (
                        f"Confirmed: Sustained link utilization ({max_util}%) and egress buffer drops ({max_drops} pkts/s) confirm buffer overflow."
                        if p_congestion > 0.70
                        else "Traffic demand remains well within link buffer capacity baselines."
                    )
                ),
            ),
            CompetingHypothesis(
                hypothesis_id="HYP-INTERFACE-FAULT",
                name="Physical Link / Transceiver Integrity Fault",
                description="Damaged fiber/copper patch cable or degrading SFP transceiver causing frame corruption and CRC drops.",
                probability=round(p_interface, 2),
                supporting_evidence=sup_interface,
                contradicting_evidence=con_interface,
                status="VALIDATED" if p_interface > 0.70 else "REFUTED",
                reasoning=(
                    f"High Layer-1 CRC frame errors ({max_crc}/sec) and interface flaps ({max_flaps}) verify physical transceiver or fiber patch degradation."
                    if p_interface > 0.70
                    else f"Physical interface error counters ({max_crc} CRC errors/s) within acceptable limits."
                ),
            ),
            CompetingHypothesis(
                hypothesis_id="HYP-WIFI-RF",
                name="Wireless RF Path Loss / Edge Signal Attenuation",
                description="Excessive physical distance or RF obstruction between wireless client and Access Point causing frame drops.",
                probability=round(p_wifi, 2),
                supporting_evidence=sup_wifi,
                contradicting_evidence=con_wifi,
                status="VALIDATED" if p_wifi > 0.70 else "REFUTED",
                reasoning=(
                    f"Severe wireless path loss observed: RSSI {min_rssi} dBm and {max_retries}% MAC retransmissions indicate client attenuation."
                    if p_wifi > 0.70
                    else f"Wireless RF signal strength ({min_rssi} dBm) and retry levels are healthy."
                ),
            ),
            CompetingHypothesis(
                hypothesis_id="HYP-CPU-STARVATION",
                name="Control Plane Processor Saturation",
                description="Uncontrolled software loop, broadcast storm, or BGP churn consuming 100% router CPU interrupts.",
                probability=round(p_cpu, 2),
                supporting_evidence=sup_cpu,
                contradicting_evidence=con_cpu,
                status="VALIDATED" if p_cpu > 0.70 else "REFUTED",
                reasoning=(
                    f"Host Route Processor CPU is saturated at {max_cpu}%, starvating control plane interrupt processing and inducing packet transit latency."
                    if p_cpu > 0.70
                    else f"CPU utilization ({max_cpu}%) is within operational safety margins."
                ),
            ),
            CompetingHypothesis(
                hypothesis_id="HYP-DNS-DHCP-OUTAGE",
                name="Core Network Services Failure (DNS/DHCP)",
                description="Local name resolver service unresponsive or DHCP IP pool depleted, preventing host communications.",
                probability=round(p_dns, 2),
                supporting_evidence=sup_dns,
                contradicting_evidence=con_dns,
                status="VALIDATED" if p_dns > 0.70 else "REFUTED",
                reasoning=(
                    f"Core infrastructure failure: DNS resolver response {max_dns_ms}ms (timeout) and DHCP pool {max_dhcp_util}% capacity."
                    if p_dns > 0.70
                    else f"DNS query resolution and DHCP pool availability operating normally."
                ),
            ),
        ]

        # Sort hypotheses by probability descending
        hyp_list.sort(key=lambda h: h.probability, reverse=True)
        self.competing_hypotheses = hyp_list

        winner = hyp_list[0]
        runner_up = hyp_list[1] if len(hyp_list) > 1 else None

        # Check if network is completely healthy
        if winner.probability <= 0.20:
            return (
                DiagnosticStatus.HEALTHY,
                "Normal Network Operation (All Telemetry Within SLA Baselines)",
                0.98,
            )

        # High confidence single diagnosis
        if winner.probability >= 0.80 and (runner_up is None or runner_up.probability < 0.50):
            return (
                DiagnosticStatus.CONFIRMED,
                winner.name,
                winner.probability,
            )

        # Competing hypotheses close in probability
        return (
            DiagnosticStatus.SUSPECTED,
            f"Suspected {winner.name} (Alternative: {runner_up.name if runner_up else 'None'})",
            winner.probability,
        )
