"""
Recommendation and Reporting Agent.
Generates structured remediation runbooks, actionable CLI operational procedures,
and compiles the final canonical JSON diagnostic report.
Strictly ties recommendations to collected supporting evidence, avoids recommending
risky changes without human approval, and provides safe diagnostic checks when uncertain.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

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
        evidence_items: Optional[List[EvidenceItem]] = None,
    ) -> List[RemediationAction]:
        """
        Synthesizes technical, executable remediation steps strictly tied to supporting evidence.
        Flags risky operational modifications with requires_human_approval=True.
        Prioritizes non-destructive diagnostic checks when cause is inconclusive or uncertain.
        """
        primary_device = affected_devices[0] if affected_devices else "Edge-Switch-01"
        actions: List[RemediationAction] = []
        ev_summaries = [e.summary for e in (evidence_items or []) if e.summary]

        # -------------------------------------------------------------
        # 1. Healthy / Nominal Network
        # -------------------------------------------------------------
        if status == DiagnosticStatus.HEALTHY or str(status).upper() == "HEALTHY":
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
                    supporting_evidence=ev_summaries or ["Telemetry metrics within nominal bounds"],
                    requires_human_approval=False,
                )
            )
            return actions

        # -------------------------------------------------------------
        # 2. Inconclusive / Insufficient Evidence (Safe Diagnostics Only)
        # -------------------------------------------------------------
        if status in (DiagnosticStatus.INCONCLUSIVE, DiagnosticStatus.INSUFFICIENT_EVIDENCE) or str(status).upper() in ("INCONCLUSIVE", "INSUFFICIENT_EVIDENCE"):
            actions.extend([
                RemediationAction(
                    step=1,
                    action="Execute Hop-by-Hop Path Ping & Tracepath Analysis",
                    target_device=primary_device,
                    command=f"traceroute {primary_device} timeout 2",
                    risk_level="LOW",
                    rationale="Root cause is uncertain without node queue telemetry; isolate specific hop inducing transit delay.",
                    rollback_plan="Read-only diagnostic",
                    expected_outcome="Isolates intermediate transit hop responsible for latency spike or packet loss.",
                    supporting_evidence=ev_summaries or ["High transit latency or packet loss without corroborating node telemetry"],
                    requires_human_approval=False,
                ),
                RemediationAction(
                    step=2,
                    action="Poll Target Node via SNMPv3 / RESTCONF for Hardware Metrics",
                    target_device=primary_device,
                    command=f"show interface counters | include drops|errors",
                    risk_level="LOW",
                    rationale="Collect queue discards, CRC counters, and CPU load before executing any operational configuration changes.",
                    rollback_plan="Read-only diagnostic",
                    expected_outcome="Provides ground-truth internal counters to corroborate or rule out buffer congestion.",
                    supporting_evidence=["Insufficient telemetry dimensions to assert root cause"],
                    requires_human_approval=False,
                ),
                RemediationAction(
                    step=3,
                    action="Verify Upstream Carrier / ISP Policing & CIR Allocation",
                    target_device=primary_device,
                    command="show policy-map interface | include drop",
                    risk_level="LOW",
                    rationale="Check if traffic shaping or upstream carrier policer is silently dropping transit packets.",
                    rollback_plan="Read-only diagnostic",
                    expected_outcome="Verifies whether transit latency is caused by external carrier CIR throttling.",
                    supporting_evidence=["Transit latency uncorroborated by local buffer telemetry"],
                    requires_human_approval=False,
                ),
            ])
            return actions

        # -------------------------------------------------------------
        # 3. Interface / Port Down Outage
        # -------------------------------------------------------------
        if "Interface Down" in root_cause or "Port Down" in root_cause:
            actions.extend([
                RemediationAction(
                    step=1,
                    action="Inspect Physical Link State & Transceiver Connection",
                    target_device=primary_device,
                    command="show interface status | include down",
                    risk_level="LOW",
                    rationale="Verify whether interface is physically unplugged, transceiver unseated, or administratively down.",
                    rollback_plan="Read-only diagnostic",
                    expected_outcome="Confirms Layer-1 physical link status and port configuration.",
                    supporting_evidence=ev_summaries or ["Interface operational status reported DOWN"],
                    requires_human_approval=False,
                ),
                RemediationAction(
                    step=2,
                    action="Execute Administrative Port Re-enablement",
                    target_device=primary_device,
                    command="interface GigabitEthernet0/0/1\n shutdown\n no shutdown",
                    risk_level="MEDIUM",
                    rationale="Clear software-disabled interface state and re-initialize PHY auto-negotiation.",
                    rollback_plan="interface GigabitEthernet0/0/1\n shutdown",
                    expected_outcome="Restores physical interface operational state to UP.",
                    supporting_evidence=["Operational state reported DOWN"],
                    requires_human_approval=True,
                ),
            ])

        # -------------------------------------------------------------
        # 4. Corroborated Buffer Congestion Remediation
        # -------------------------------------------------------------
        elif "Congestion" in root_cause:
            actions.extend([
                RemediationAction(
                    step=1,
                    action="Inspect Egress Interface Queue Statistics & Active Drops",
                    target_device=primary_device,
                    command="show interface GigabitEthernet0/1/0 | include drops|utilization",
                    risk_level="LOW",
                    rationale="Verify buffer queue depth and discard counters on congested egress interface.",
                    rollback_plan="Read-only diagnostic",
                    expected_outcome="Pinpoints active drop rate and buffer memory occupancy on congested interface.",
                    supporting_evidence=ev_summaries or ["Corroborated by high link utilization and active queue drops"],
                    requires_human_approval=False,
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
                    supporting_evidence=["Sustained bandwidth saturation and buffer drops"],
                    requires_human_approval=True,
                ),
                RemediationAction(
                    step=3,
                    action="Engage LACP / ECMP Alternative Equal-Cost Link",
                    target_device=primary_device,
                    command="interface Port-Channel1\n minimum-links 2\n lacp max-bundle 4",
                    risk_level="MEDIUM",
                    rationale="Doubles inter-switch bandwidth from 1 Gbps to 2 Gbps using aggregated secondary trunk.",
                    rollback_plan="lacp max-bundle 2",
                    expected_outcome="Doubles trunk bandwidth headroom to 2 Gbps, reducing transit latency.",
                    supporting_evidence=["Egress interface bandwidth capacity exceeded"],
                    requires_human_approval=True,
                ),
            ])

        # -------------------------------------------------------------
        # 5. Physical Link / Transceiver Integrity Fault
        # -------------------------------------------------------------
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
                    supporting_evidence=ev_summaries or ["Interface CRC frame corruption detected"],
                    requires_human_approval=False,
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
                    supporting_evidence=["Physical CRC errors inducing frame loss"],
                    requires_human_approval=True,
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
                    supporting_evidence=["Sustained CRC error rate > 20 errors/sec"],
                    requires_human_approval=True,
                ),
            ])

        # -------------------------------------------------------------
        # 6. Wireless RF Attenuation Remediation
        # -------------------------------------------------------------
        elif "Wireless" in root_cause or "RF" in root_cause or "Wi-Fi" in root_cause:
            actions.extend([
                RemediationAction(
                    step=1,
                    action="Increase AP Radio Transmit Power & Dynamic Channel Optimization",
                    target_device=primary_device,
                    command="ap name AP-02 dot11 5ghz txpower 18\nap name AP-02 dot11 5ghz channel auto",
                    risk_level="MEDIUM",
                    rationale="Boosts signal strength to improve SNR above 20 dB margin and reduce 802.11 retries.",
                    rollback_plan="ap name AP-02 dot11 5ghz txpower auto",
                    expected_outcome="Improves client RSSI and lifts SNR above 25 dB margin.",
                    supporting_evidence=ev_summaries or ["Wireless RSSI degradation below -80 dBm"],
                    requires_human_approval=True,
                ),
                RemediationAction(
                    step=2,
                    action="Trigger 802.11k/v Fast BSS Transition / Client Steer to Nearest AP",
                    target_device=primary_device,
                    command="wireless client steer mac 00:a1:b2:c3:d4:e5 target-ap AP-01",
                    risk_level="LOW",
                    rationale="Steers sticky edge clients experiencing attenuation to adjacent Access Point with stronger RSSI.",
                    rollback_plan="wireless client steer disable",
                    expected_outcome="Roams client to nearest AP, cutting 802.11 frame retransmissions.",
                    supporting_evidence=["High frame retransmissions detected on wireless client"],
                    requires_human_approval=False,
                ),
            ])

        # -------------------------------------------------------------
        # 7. Control Plane CPU Saturation Remediation
        # -------------------------------------------------------------
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
                    expected_outcome="Pinpoints rogue process or protocol storm consuming Route Processor interrupts.",
                    supporting_evidence=ev_summaries or ["CPU utilization saturated above 90%"],
                    requires_human_approval=False,
                ),
                RemediationAction(
                    step=2,
                    action="Activate Control Plane Policing (CoPP) Hardware Rate-Limiters",
                    target_device=primary_device,
                    command="control-plane\n service-policy input COPP-PROTECT-STORM",
                    risk_level="HIGH",
                    rationale="Protects the router Route Processor by hardware-policing unclassified broadcast/control packets.",
                    rollback_plan="no service-policy input COPP-PROTECT-STORM",
                    expected_outcome="Hardware rate-limits control plane storm; drops router CPU and restores packet latency.",
                    supporting_evidence=["Critical control plane processor saturation"],
                    requires_human_approval=True,
                ),
            ])

        # -------------------------------------------------------------
        # 8. Core Services (DNS / DHCP) Failure Remediation
        # -------------------------------------------------------------
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
                    expected_outcome="Restores domain name resolution latency down to < 15ms.",
                    supporting_evidence=ev_summaries or ["DNS resolution timeout on primary resolver"],
                    requires_human_approval=True,
                ),
                RemediationAction(
                    step=2,
                    action="Flush DHCP Stale Bindings & Restart Resolver Daemon",
                    target_device=primary_device,
                    command="systemctl restart named && clear ip dhcp binding * expired",
                    risk_level="MEDIUM",
                    rationale="Frees depleted IP address pools and restores name daemon responsiveness.",
                    rollback_plan="systemctl restart named",
                    expected_outcome="Reclaims exhausted lease table and restores DHCP address pool headroom.",
                    supporting_evidence=["DHCP pool exhaustion > 95%"],
                    requires_human_approval=True,
                ),
            ])

        # -------------------------------------------------------------
        # 9. Fallback Safe Operational Steps
        # -------------------------------------------------------------
        else:
            actions.extend([
                RemediationAction(
                    step=1,
                    action="Verify Telemetry Agent Connectivity & Polling Frequency",
                    target_device=primary_device,
                    command="show telemetry connection status",
                    risk_level="LOW",
                    rationale="Restore missing telemetry dimensions before applying corrective operational changes.",
                    rollback_plan="No state change",
                    expected_outcome="Restores missing telemetry dimensions (CPU, queue drops, CRC errors).",
                    supporting_evidence=ev_summaries or ["Uncorroborated anomaly detected"],
                    requires_human_approval=False,
                ),
                RemediationAction(
                    step=2,
                    action="Execute End-to-End Diagnostic Ping & Tracepath",
                    target_device=primary_device,
                    command=f"traceroute {primary_device} timeout 2",
                    risk_level="LOW",
                    rationale="Collect auxiliary hop-by-hop latency and loss measurements.",
                    rollback_plan="N/A",
                    expected_outcome="Provides hop-by-hop latency and packet loss ground truth.",
                    supporting_evidence=["Auxiliary path analysis required"],
                    requires_human_approval=False,
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
        telemetry_origin: str = "SIMULATED_SCENARIO",
        next_diagnostic_checks: Optional[List[str]] = None,
        observed_facts: Optional[List[str]] = None,
        protocol_rejection_confidence: Optional[float] = None,
        conflict_status: Optional[str] = "NO_CONFLICT",
        resolved_conflict_details: Optional[Dict[str, Any]] = None,
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
            evidence_items=supporting_evidence,
        )

        primary_hyp = alternative_causes[0] if alternative_causes else None

        report = CanonicalDiagnosticReport(
            incident_id=incident_id,
            investigation_id=incident_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=status,
            suspected_root_cause=root_cause,
            confidence=round(confidence, 4),
            confidence_calculation_method=confidence_calculation_method or "Evidence-Based Multi-Factor Calibrated Confidence (Corroborating Signals, Completeness, Freshness & Contradiction Penalties)",
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
            next_diagnostic_checks=next_diagnostic_checks or [],
            observed_facts=observed_facts or [],
            execution_time_ms=round(execution_time_ms, 2),
            inter_agent_messages_count=inter_agent_messages_count,
            telemetry_origin=telemetry_origin,
            protocol_rejection_confidence=protocol_rejection_confidence,
            conflict_status=conflict_status,
            resolved_conflict_details=resolved_conflict_details,
        )

        # Emit completion message
        self.create_message(
            message_type=MessageType.REMEDIATION_PLAN,
            confidence=confidence,
            findings=[
                f"Canonical Report compiled for Incident #{incident_id}",
                f"Generated {len(remediation_actions)} actionable remediation steps",
            ],
            evidence={"incident_id": incident_id, "actions_count": len(remediation_actions)},
        )

        self.set_status("COMPLETE", "Canonical report ready")
        return report
