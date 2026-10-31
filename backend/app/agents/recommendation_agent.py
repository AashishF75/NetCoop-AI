"""
Recommendation and Reporting Agent.
Generates structured remediation runbooks, actionable CLI operational procedures,
and compiles the final canonical JSON diagnostic report.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from app.agents.base_agent import BaseAgent
from app.protocol.schema import (
    AgentMessage,
    MessageType,
    DiagnosticStatus,
    CompetingHypothesis,
    EvidenceItem,
    RemediationAction,
    CanonicalDiagnosticReport,
    InvestigationExplanation,
    AgentInvestigationTrace,
    ProactiveRiskWarning,
    TelemetryRecord,
)


class RecommendationAgent(BaseAgent):
    def __init__(self, agent_id: str = "recom-agent-01"):
        super().__init__(
            agent_id=agent_id,
            name="Recommendation & Reporting Agent",
            role="Runbook Synthesizer & Canonical Report Compiler",
        )

    def analyze(self, telemetry: List[TelemetryRecord]) -> List[AgentMessage]:
        self.set_status("IDLE", "Standing by for correlation report")
        return []

    def handle_query(self, query: AgentMessage, telemetry: List[TelemetryRecord]) -> AgentMessage:
        return self.create_message(
            message_type=MessageType.QUERY_RESPONSE,
            target_agent_id=query.agent_id,
            correlation_id=query.correlation_id,
            confidence=1.0,
            findings=["Recommendation Agent standing by to generate action plan."],
        )

    def generate_remediation_actions(
        self,
        status: DiagnosticStatus,
        root_cause: str,
        affected_devices: List[str],
        hypotheses: List[CompetingHypothesis],
    ) -> List[RemediationAction]:
        """
        Synthesizes technical, executable remediation steps based on the identified fault.
        """
        primary_device = affected_devices[0] if affected_devices else "Edge-Switch-01"
        actions: List[RemediationAction] = []

        if status == DiagnosticStatus.HEALTHY:
            actions.append(
                RemediationAction(
                    step=1,
                    action="Maintain Monitoring Baseline",
                    target_device=primary_device,
                    command="show telemetry ietf subscription brief",
                    risk_level="LOW",
                    rationale="All telemetry signals are within normal operating bounds. No corrective action required.",
                    rollback_plan="N/A",
                    expected_outcome="Telemetry metrics remain verified within baselines (latency < 5ms, loss 0%).",
                )
            )
            return actions

        # 1. Congestion Remediation
        if "Congestion" in root_cause:
            actions.extend([
                RemediationAction(
                    step=1,
                    action="Inspect Egress Interface Queue Statistics",
                    target_device=primary_device,
                    command="show interface GigabitEthernet0/1/0 | include drops|utilization",
                    risk_level="LOW",
                    rationale="Verify buffer queue depth and discard counters on congested egress interface.",
                    rollback_plan="No state change",
                    expected_outcome="Pinpoints active drop rate and buffer memory occupancy on congested egress interface.",
                ),
                RemediationAction(
                    step=2,
                    action="Apply QoS Rate-Limiting Policy to Bulk Non-Priority Traffic",
                    target_device=primary_device,
                    command="policy-map SHAPE-BULK-TRAFFIC\n class class-default\n  shape average 400000000",
                    risk_level="MEDIUM",
                    rationale="Throttles bulk backups and elephant flows to prevent buffer overflow for latency-critical traffic.",
                    rollback_plan="no policy-map SHAPE-BULK-TRAFFIC",
                    expected_outcome="Reduces link utilization from 98% to < 75%, eliminating egress queue discards.",
                ),
                RemediationAction(
                    step=3,
                    action="Engage LACP / ECMP Alternative Equal-Cost Link",
                    target_device=primary_device,
                    command="interface Port-Channel1\n minimum-links 2\n lacp max-bundle 4",
                    risk_level="MEDIUM",
                    rationale="Doubles inter-switch bandwidth from 1 Gbps to 2 Gbps using aggregated secondary trunk.",
                    rollback_plan="lacp max-bundle 2",
                    expected_outcome="Doubles trunk bandwidth headroom to 2 Gbps, reducing transit latency from 142ms to < 10ms.",
                ),
            ])

        # 2. Physical Interface / Transceiver Defect Remediation
        elif "Physical Link" in root_cause or "Interface" in root_cause:
            actions.extend([
                RemediationAction(
                    step=1,
                    action="Perform Digital Optical Monitoring (DOM) Diagnostics on Transceiver",
                    target_device=primary_device,
                    command="show interfaces transceiver detail | include Tx Power|Rx Power|Temperature",
                    risk_level="LOW",
                    rationale="Determine if laser optical power levels (dBm) have dropped below receiver sensitivity limit.",
                    rollback_plan="Read-only diagnostic",
                    expected_outcome="Quantifies optical attenuation; confirms SFP RX power degradation below receiver sensitivity threshold.",
                ),
                RemediationAction(
                    step=2,
                    action="Failover Traffic to Redundant Standby Interface",
                    target_device=primary_device,
                    command="interface TenGigabitEthernet0/1/1\n standby 10 priority 120 preempt",
                    risk_level="MEDIUM",
                    rationale="Immediately divert user packets away from degraded link to eliminate ongoing packet discards.",
                    rollback_plan="standby 10 priority 100",
                    expected_outcome="Immediately redirects packet transit across redundant link, terminating ongoing frame discards.",
                ),
                RemediationAction(
                    step=3,
                    action="Dispatch On-Site Technician to Reseat/Replace SFP+ Transceiver & Patch Cord",
                    target_device=primary_device,
                    command="hw-module subslot 0/1 transceiver 1 idprom",
                    risk_level="HIGH",
                    rationale="Physical hardware repair required to clear CRC frame corruption.",
                    rollback_plan="Retain swapped hardware for RMA inspection",
                    expected_outcome="Restores clean optical transceiver link with 0 CRC errors/sec and zero link flapping.",
                ),
            ])

        # 3. Wireless RF Attenuation Remediation
        elif "Wireless" in root_cause or "RF" in root_cause or "Wi-Fi" in root_cause:
            actions.extend([
                RemediationAction(
                    step=1,
                    action="Increase AP Radio Transmit Power & Dynamic Channel Optimization",
                    target_device=primary_device,
                    command="ap name AP-02 dot11 5ghz txpower 18\nap name AP-02 dot11 5ghz channel auto",
                    risk_level="MEDIUM",
                    rationale="Boosts signal strength by +4 dBm to improve SNR above 20 dB margin and reduce 802.11 retries.",
                    rollback_plan="ap name AP-02 dot11 5ghz txpower auto",
                    expected_outcome="Improves client RSSI from -86.5 dBm to > -68 dBm and lifts SNR above 25 dB margin.",
                ),
                RemediationAction(
                    step=2,
                    action="Trigger 802.11k/v Fast BSS Transition / Client Steer to Nearest AP",
                    target_device=primary_device,
                    command="wireless client steer mac 00:a1:b2:c3:d4:e5 target-ap AP-01",
                    risk_level="LOW",
                    rationale="Steers sticky edge clients experiencing -85 dBm attenuation to adjacent Access Point with -58 dBm RSSI.",
                    rollback_plan="wireless client steer disable",
                    expected_outcome="Roams client to AP-01, cutting 802.11 frame retransmissions from 42% down to < 5%.",
                ),
            ])

        # 4. Control Plane CPU Saturation Remediation
        elif "CPU" in root_cause or "Processor" in root_cause:
            actions.extend([
                RemediationAction(
                    step=1,
                    action="Isolate Top CPU-Consuming Control Plane Process",
                    target_device=primary_device,
                    command="show processes cpu sorted | exclude 0.00%",
                    risk_level="LOW",
                    rationale="Identify whether CPU spike is driven by BGP routing churn, ARP broadcast storms, or memory leaks.",
                    rollback_plan="Read-only diagnostic",
                    expected_outcome="Pinpoints rogue process or protocol storm consuming 99.4% CPU Route Processor interrupts.",
                ),
                RemediationAction(
                    step=2,
                    action="Activate Control Plane Policing (CoPP) Hardware Rate-Limiters",
                    target_device=primary_device,
                    command="control-plane\n service-policy input COPP-PROTECT-STORM",
                    risk_level="HIGH",
                    rationale="Protects the router Route Processor by hardware-policing unclassified broadcast/control packets.",
                    rollback_plan="no service-policy input COPP-PROTECT-STORM",
                    expected_outcome="Hardware rate-limits control plane storm; drops router CPU from 99.4% to < 25% and restores transit packet latency to < 5ms.",
                ),
            ])

        # 5. Core Services (DNS / DHCP) Failure Remediation
        elif "DNS" in root_cause or "DHCP" in root_cause or "Services" in root_cause:
            actions.extend([
                RemediationAction(
                    step=1,
                    action="Switch Host DNS Resolver to Secondary High-Availability Forwarder",
                    target_device=primary_device,
                    command="ip name-server 10.0.0.54 1.1.1.1\nno ip name-server 10.0.0.53",
                    risk_level="MEDIUM",
                    rationale="Directs network lookups to redundant standby resolver, restoring immediate domain resolution.",
                    rollback_plan="ip name-server 10.0.0.53",
                    expected_outcome="Restores domain name resolution latency from 3250ms (timeout) down to < 15ms.",
                ),
                RemediationAction(
                    step=2,
                    action="Flush DHCP Stale Bindings & Restart Resolver Daemon",
                    target_device=primary_device,
                    command="systemctl restart named && clear ip dhcp binding * expired",
                    risk_level="MEDIUM",
                    rationale="Frees depleted IP address pools and restores name daemon responsiveness.",
                    rollback_plan="systemctl restart named",
                    expected_outcome="Reclaims exhausted lease table and restores DHCP address pool headroom to > 40% capacity.",
                ),
            ])

        # 6. Fallback / Insufficient Data Remediation
        else:
            actions.extend([
                RemediationAction(
                    step=1,
                    action="Verify Telemetry Agent Connectivity & SNMP/gNMI Polling Frequency",
                    target_device=primary_device,
                    command="show telemetry connection status",
                    risk_level="LOW",
                    rationale="Restore missing telemetry dimensions before applying corrective operational changes.",
                    rollback_plan="No state change",
                    expected_outcome="Restores missing telemetry dimensions (CPU, queue drops, CRC errors) from unmonitored node.",
                ),
                RemediationAction(
                    step=2,
                    action="Execute End-to-End Synthetic Probe Ping & Tracepath",
                    target_device=primary_device,
                    command=f"traceroute {primary_device} timeout 2",
                    risk_level="LOW",
                    rationale="Collect auxiliary hop-by-hop latency and loss measurements.",
                    rollback_plan="N/A",
                    expected_outcome="Provides hop-by-hop latency and packet loss ground truth.",
                ),
            ])

        return actions

    def compile_canonical_report(
        self,
        incident_id: str,
        status: DiagnosticStatus,
        root_cause: str,
        confidence: float,
        affected_devices: List[str],
        supporting_evidence: List[EvidenceItem],
        alternative_causes: List[CompetingHypothesis],
        evidence_sources: List[str],
        limitations: List[str],
        execution_time_ms: float,
        inter_agent_messages_count: int,
        fault_propagation_paths: Optional[List[List[str]]] = None,
        missing_telemetry: Optional[List[str]] = None,
        confidence_calculation_method: Optional[str] = None,
        investigation_explanation: Optional[InvestigationExplanation] = None,
        investigation_trace: Optional[AgentInvestigationTrace] = None,
        proactive_warnings: Optional[List[ProactiveRiskWarning]] = None,
        telemetry_origin: str = "SIMULATED",
    ) -> CanonicalDiagnosticReport:
        """
        Produces the official standardized CanonicalDiagnosticReport matching problem statement.
        """
        self.set_status("ANALYZING", "Compiling official diagnostic report and remediation runbook")
        
        remediation_actions = self.generate_remediation_actions(
            status=status,
            root_cause=root_cause,
            affected_devices=affected_devices,
            hypotheses=alternative_causes,
        )

        primary_hyp = alternative_causes[0] if alternative_causes else None

        report = CanonicalDiagnosticReport(
            incident_id=incident_id,
            investigation_id=incident_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=status,
            suspected_root_cause=root_cause,
            confidence=round(confidence, 4),
            confidence_calculation_method=confidence_calculation_method or "Weighted Multi-Agent Anomaly Scoring & Bayesian Evidence Synthesis",
            affected_devices=affected_devices,
            supporting_evidence=supporting_evidence,
            alternative_causes=alternative_causes,
            primary_hypothesis=primary_hyp,
            fault_propagation_paths=fault_propagation_paths or [],
            missing_telemetry=missing_telemetry or [],
            recommended_actions=remediation_actions,
            investigation_explanation=investigation_explanation,
            investigation_trace=investigation_trace,
            proactive_warnings=proactive_warnings or [],
            evidence_sources=evidence_sources,
            limitations=limitations,
            execution_time_ms=round(execution_time_ms, 2),
            inter_agent_messages_count=inter_agent_messages_count,
            telemetry_origin=telemetry_origin,
        )

        # Emit completion message
        self.create_message(
            message_type=MessageType.REMEDIATION_PLAN,
            confidence=confidence,
            findings=[
                f"Canonical Report compiled for Incident #{incident_id}",
                f"Generated {len(remediation_actions)} actionable remediation steps",
            ],
            evidence={"incident_id": incident_id, "actions_count": len(remediation_actions)}
        )

        self.set_status("COMPLETE", "Canonical report ready")
        return report
