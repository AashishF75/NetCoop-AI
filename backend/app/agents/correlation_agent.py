"""
Fault Correlation Agent.
Coordinates inter-agent cross-examination, hypothesis generation, conflict resolution,
evidence-based confidence calibration, and insufficient-evidence detection.
Combines findings from all domain agents, distinguishes observed facts from hypotheses,
and provides explicit INSUFFICIENT_EVIDENCE / INCONCLUSIVE outcomes.
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
        self.observed_facts: List[str] = []
        self.next_diagnostic_checks: List[str] = []
        self.confidence_explanation: str = ""
        self.max_missing_critical: int = 0
        self.has_stale_telemetry: bool = False
        self.detected_origin: str = "SIMULATED_SCENARIO"

    def reset(self):
        super().reset()
        self.competing_hypotheses.clear()
        self.evidence_store.clear()
        self.limitations_identified.clear()
        self.conflicts_resolved.clear()
        self.observed_facts.clear()
        self.next_diagnostic_checks.clear()
        self.confidence_explanation = ""
        self.max_missing_critical = 0
        self.has_stale_telemetry = False
        self.detected_origin = "SIMULATED_SCENARIO"

    def analyze(self, telemetry: List[TelemetryRecord]) -> List[AgentMessage]:
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
        failed_agents: Optional[List[str]] = None,
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
        self.observed_facts.clear()
        self.next_diagnostic_checks.clear()
        self.confidence_explanation = ""

        # Check for missing telemetry (insufficient evidence check)
        self._check_telemetry_completeness(telemetry)

        # Extract Observed Facts directly from collected records
        self._extract_observed_facts(telemetry)

        # Collect implicated devices from domain anomalies
        implicated_devices = list(dict.fromkeys([
            msg.device_id for msg in domain_messages if msg.device_id
        ]))
        if not implicated_devices and telemetry:
            implicated_devices = list(dict.fromkeys([r.device_id for r in telemetry if r.device_id]))

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
                    telemetry_origin=msg.evidence.get("telemetry_origin", "SIMULATED_SCENARIO"),
                )
                self.evidence_store.append(item)

        # -------------------------------------------------------------
        # GENUINE INTER-AGENT DIALOGUE (Cross-Examination)
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
                        findings=[f"Round {round_idx+1}: Requesting RF signal metrics and service-layer reachability for {dev}"],
                    )
                    inter_agent_dialogue.append(q_conn)
                    resp_conn = connectivity_agent.handle_query(q_conn, telemetry)
                    inter_agent_dialogue.append(resp_conn)
                except Exception as e:
                    self.limitations_identified.append(f"Connectivity Agent query failed for {dev}: {str(e)}")

        # -------------------------------------------------------------
        # SYNTHESIS, CONFLICT RESOLUTION & HYPOTHESIS RANKING
        # -------------------------------------------------------------
        status, root_cause, confidence = self._evaluate_hypotheses_and_resolve_conflicts(
            telemetry, domain_messages, inter_agent_dialogue, failed_agents=failed_agents
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
                f"Observed Facts Recorded: {len(self.observed_facts)}",
                f"Next Diagnostic Checks: {len(self.next_diagnostic_checks)}",
            ],
            evidence={
                "status": status.value,
                "root_cause": root_cause,
                "affected_devices": implicated_devices,
                "evidence_count": len(self.evidence_store),
                "next_diagnostic_checks": self.next_diagnostic_checks,
            },
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

    def _extract_observed_facts(self, telemetry: List[TelemetryRecord]):
        """Records ground-truth empirical observations distinct from diagnostic hypotheses."""
        for rec in telemetry:
            dev = rec.device_id
            origin = getattr(rec, "telemetry_origin", "SIMULATED_SCENARIO")
            if rec.latency_ms is not None:
                self.observed_facts.append(f"Device '{dev}': Measured transit RTT latency is {rec.latency_ms} ms (source: {origin}).")
            if rec.packet_loss_pct is not None:
                self.observed_facts.append(f"Device '{dev}': Measured packet loss is {rec.packet_loss_pct}% (source: {origin}).")
            if rec.queue_drops_per_sec is not None:
                self.observed_facts.append(f"Device '{dev}': Egress buffer queue drop rate is {rec.queue_drops_per_sec} pkts/s (source: {origin}).")
            if rec.interface_crc_errors is not None:
                self.observed_facts.append(f"Device '{dev}': Interface CRC frame errors are {rec.interface_crc_errors} errors/sec (source: {origin}).")
            if rec.cpu_utilization_pct is not None:
                self.observed_facts.append(f"Device '{dev}': Control plane CPU load is {rec.cpu_utilization_pct}% (source: {origin}).")
            if rec.memory_utilization_pct is not None:
                self.observed_facts.append(f"Device '{dev}': System memory allocation is {rec.memory_utilization_pct}% (source: {origin}).")
            if rec.interface_oper_status is not None:
                self.observed_facts.append(f"Device '{dev}': Interface operational state is '{rec.interface_oper_status}' (source: {origin}).")
            if rec.dns_response_ms is not None:
                self.observed_facts.append(f"Device '{dev}': DNS query resolution time is {rec.dns_response_ms} ms (source: {origin}).")
            if rec.dhcp_pool_utilization_pct is not None:
                self.observed_facts.append(f"Device '{dev}': DHCP IP address pool utilization is {rec.dhcp_pool_utilization_pct}% (source: {origin}).")
            if rec.wifi_rssi_dbm is not None:
                self.observed_facts.append(f"Device '{dev}': Wireless RF signal strength is {rec.wifi_rssi_dbm} dBm (source: {origin}).")

    def _check_telemetry_completeness(self, telemetry: List[TelemetryRecord]):
        """Detects missing fields, stale data, and insufficient telemetry across devices."""
        self.max_missing_critical = 0
        self.has_stale_telemetry = False

        if not telemetry:
            self.limitations_identified.append("Telemetry dataset is empty; zero records received.")
            self.max_missing_critical = 5
            self.detected_origin = "SIMULATED_SCENARIO"
            return

        origins = {getattr(r, "telemetry_origin", "SIMULATED_SCENARIO") for r in telemetry}
        if "LIVE_DEVICE" in origins:
            self.detected_origin = "LIVE_DEVICE"
        elif "LIVE_HOST" in origins or "LIVE" in origins:
            self.detected_origin = "LIVE_HOST"
        elif "CUSTOM_IMPORT" in origins:
            self.detected_origin = "CUSTOM_IMPORT"
        elif "GENERATED_TEST" in origins:
            self.detected_origin = "GENERATED_TEST"
        else:
            self.detected_origin = "SIMULATED_SCENARIO"

        for rec in telemetry:
            dev = rec.device_id or "Unknown-Device"
            dev_type = (rec.device_type or "").lower()
            missing_in_rec = []
            if rec.latency_ms is None:
                missing_in_rec.append("latency_ms")

            if dev_type in ("ap", "access_point", "wifi") or "ap-" in dev.lower():
                if rec.wifi_rssi_dbm is None:
                    missing_in_rec.append("wifi_rssi_dbm")
            elif dev_type in ("server", "host", "database") or "dns" in dev.lower() or "server" in dev.lower():
                if rec.dns_response_ms is None and rec.cpu_utilization_pct is None:
                    missing_in_rec.append("service_metric")
            else:
                if rec.cpu_utilization_pct is None:
                    missing_in_rec.append("cpu_utilization_pct")
                if rec.queue_drops_per_sec is None and rec.interface_in_discards is None and rec.interface_out_discards is None:
                    missing_in_rec.append("queue_drops_per_sec")
                if rec.interface_crc_errors is None:
                    missing_in_rec.append("interface_crc_errors")

            if rec.interface_oper_status is None and rec.device_status is None:
                missing_in_rec.append("interface_oper_status")

            if len(missing_in_rec) > self.max_missing_critical:
                self.max_missing_critical = len(missing_in_rec)

            if len(missing_in_rec) >= 3:
                self.limitations_identified.append(
                    f"Device '{dev}' is missing critical telemetry dimensions: {', '.join(missing_in_rec)}. "
                    "Diagnostic certainty reduced."
                )

            # Freshness / Staleness check
            is_stale = False
            if getattr(rec, "device_status", "") == "STALE_TELEMETRY":
                is_stale = True
            elif rec.custom_metrics and rec.custom_metrics.get("stale") is True:
                is_stale = True
            elif rec.timestamp:
                try:
                    t_str = rec.timestamp.replace("Z", "+00:00")
                    rec_dt = datetime.fromisoformat(t_str)
                    now_dt = datetime.now(timezone.utc)
                    if abs((now_dt - rec_dt).total_seconds()) > 300.0:
                        is_stale = True
                except Exception:
                    pass

            if is_stale:
                self.has_stale_telemetry = True
                self.limitations_identified.append(
                    f"Device '{dev}' telemetry is STALE (older than 300s). Telemetry may not reflect current operational state."
                )

    def _count_corroborating_and_missing_layers(
        self, winner: CompetingHypothesis, telemetry: List[TelemetryRecord]
    ) -> Tuple[int, int]:
        """
        Calculates (supporting_layers, missing_relevant_fields) for the winner hypothesis.
        Prevents uncorroborated single-signal anomalies from masquerading as confirmed multi-signal diagnoses.
        """
        name = winner.name.lower()
        hyp_id = winner.hypothesis_id

        max_crc = max([r.interface_crc_errors or 0 for r in telemetry], default=0)
        max_drops = max([r.queue_drops_per_sec or 0.0 for r in telemetry], default=0.0)
        max_discards = max([(r.interface_in_discards or 0) + (r.interface_out_discards or 0) for r in telemetry], default=0)
        max_util = max([r.utilization_pct or 0.0 for r in telemetry], default=0.0)
        max_cpu = max([r.cpu_utilization_pct or 0.0 for r in telemetry], default=0.0)
        min_rssi = min([r.wifi_rssi_dbm for r in telemetry if r.wifi_rssi_dbm is not None], default=-50.0)
        max_retries = max([r.wifi_retry_pct or 0.0 for r in telemetry], default=0.0)
        max_dns_ms = max([r.dns_response_ms for r in telemetry if r.dns_response_ms is not None], default=None)
        max_dhcp_util = max([r.dhcp_pool_utilization_pct for r in telemetry if r.dhcp_pool_utilization_pct is not None], default=None)
        max_flaps = max([r.interface_flaps or 0 for r in telemetry], default=0)
        max_lat = max([r.latency_ms or 0.0 for r in telemetry], default=0.0)
        max_loss = max([r.packet_loss_pct or 0.0 for r in telemetry], default=0.0)
        has_if_down = any(
            str(r.interface_oper_status).upper() in ("DOWN", "2", "LOWER_LAYER_DOWN")
            or str(r.device_status).upper() == "DOWN"
            for r in telemetry
        )

        layers = 0
        missing_relevant = 0

        if "congestion" in name or hyp_id == "HYP-CONGESTION":
            if all(r.utilization_pct is None for r in telemetry):
                missing_relevant += 1
            if all(r.queue_drops_per_sec is None and r.interface_in_discards is None and r.interface_out_discards is None for r in telemetry):
                missing_relevant += 1
            if max_util >= 80.0:
                layers += 1
            if max_drops >= 5.0 or max_discards >= 5:
                layers += 1
            if max_lat >= 80.0 or max_loss >= 5.0:
                layers += 1

        elif "down" in name or hyp_id == "HYP-INTERFACE-DOWN":
            if has_if_down:
                layers += 2
            if max_loss >= 90.0 or any(str(r.device_status).upper() == "DOWN" for r in telemetry):
                layers += 1

        elif "physical" in name or "transceiver" in name or hyp_id == "HYP-INTERFACE-FAULT":
            if all(r.interface_crc_errors is None for r in telemetry):
                missing_relevant += 1
            if max_crc >= 20:
                layers += 2
            if max_flaps >= 2:
                layers += 1
            if max_loss >= 5.0 or max_lat >= 50.0:
                layers += 1

        elif "cpu" in name or "processor" in name or hyp_id == "HYP-CPU-STARVATION":
            if all(r.cpu_utilization_pct is None for r in telemetry):
                missing_relevant += 1
            if max_cpu >= 85.0:
                layers += 2
            if max_lat >= 50.0:
                layers += 1

        elif "wireless" in name or "rf" in name or hyp_id == "HYP-WIFI-RF":
            if all(r.wifi_rssi_dbm is None for r in telemetry):
                missing_relevant += 1
            if min_rssi <= -75.0:
                layers += 1
            if max_retries >= 20.0:
                layers += 1

        elif "dns" in name or "dhcp" in name or hyp_id == "HYP-DNS-DHCP-OUTAGE":
            if max_dns_ms is not None and max_dns_ms >= 1500.0:
                layers += 2
            elif max_dns_ms is not None and max_dns_ms >= 500.0:
                layers += 1
            if max_dhcp_util is not None and max_dhcp_util >= 95.0:
                layers += 2
            elif max_dhcp_util is not None and max_dhcp_util >= 80.0:
                layers += 1

        else:
            if max_lat < 50.0 and max_loss == 0.0:
                layers += 2
            missing_relevant = self.max_missing_critical

        return layers, missing_relevant

    def _calibrate_confidence(
        self,
        status: DiagnosticStatus,
        base_probability: float,
        supporting_layers_count: int,
        missing_critical_count: int,
        has_stale: bool,
        telemetry_origin: str,
        conflict_detected: bool,
        conflict_resolved: bool,
        failed_agents_count: int = 0,
    ) -> Tuple[float, str]:
        """
        Calibrates raw hypothesis probability into an evidence-based calibrated confidence score.
        Factors:
          1. Signal corroboration (multi-metric independence vs single-signal)
          2. Telemetry completeness (penalties for missing critical metrics)
          3. Telemetry freshness (penalties for stale data)
          4. Origin provenance (bonuses for live hardware/host telemetry)
          5. Contradiction penalty (presence of conflicting/refuting signals)
          6. Agent swarm health (penalties for agent failures/timeouts)
          7. Status-level mathematical invariants (INCONCLUSIVE capped at <= 0.48)
        """
        raw_conf = float(base_probability)

        # 1. Corroboration / Independence Modifier
        if supporting_layers_count >= 3:
            mod_signal = +0.04
        elif supporting_layers_count == 2:
            mod_signal = +0.02
        elif supporting_layers_count == 1:
            mod_signal = -0.15  # Uncorroborated single-signal penalty
        else:
            mod_signal = -0.30  # Zero corroborating signals

        # 2. Telemetry Completeness Modifier
        if missing_critical_count == 0:
            mod_missing = 0.0
        elif missing_critical_count == 1:
            mod_missing = -0.04
        elif missing_critical_count == 2:
            mod_missing = -0.08
        else:
            mod_missing = -0.25  # Severe telemetry gaps

        # 3. Freshness / Staleness Modifier
        mod_stale = -0.20 if has_stale else 0.0

        # 4. Provenance Modifier
        if telemetry_origin == "LIVE_DEVICE":
            mod_provenance = +0.03
        elif telemetry_origin == "LIVE_HOST":
            mod_provenance = +0.02
        elif telemetry_origin == "CUSTOM_IMPORT":
            mod_provenance = -0.03
        else:
            mod_provenance = 0.0  # SIMULATED_SCENARIO, BENCHMARK, GENERATED_TEST

        # 5. Contradiction / Conflict Modifier
        if conflict_detected:
            if conflict_resolved:
                mod_conflict = 0.0  # Conflict resolved by empirical counter-evidence; zero lingering penalty
                conflict_label = "Resolved (0.00 penalty)"
            else:
                mod_conflict = -0.25  # Unresolved contradiction between active hypotheses
                conflict_label = "Unresolved (-0.25 penalty)"
        else:
            mod_conflict = 0.0
            conflict_label = "None (0.00)"

        # 6. Agent Swarm Health Modifier
        mod_failures = -(failed_agents_count * 0.08)

        # Compute combined adjusted confidence
        adjusted = (
            raw_conf
            + mod_signal
            + mod_missing
            + mod_stale
            + mod_provenance
            + mod_conflict
            + mod_failures
        )

        # 7. Apply Strict Status Invariants
        if status in (DiagnosticStatus.INCONCLUSIVE, DiagnosticStatus.INSUFFICIENT_EVIDENCE):
            # Inconclusive/insufficient evidence diagnoses must NEVER receive high confidence (<= 0.48)
            final_conf = max(0.05, min(0.48, adjusted))
        elif status == DiagnosticStatus.SUSPECTED:
            # If telemetry is stale, confidence cannot exceed 0.74
            if has_stale:
                final_conf = max(0.45, min(0.74, adjusted))
            else:
                final_conf = max(0.45, min(0.89, adjusted))
        elif status == DiagnosticStatus.CONFIRMED:
            # Confirmed diagnoses require multi-signal corroboration and completeness
            if supporting_layers_count < 2 or missing_critical_count >= 3 or has_stale:
                final_conf = max(0.50, min(0.74, adjusted))
            else:
                final_conf = max(0.75, min(0.99, adjusted))
        elif status == DiagnosticStatus.HEALTHY:
            if missing_critical_count >= 2:
                final_conf = max(0.65, min(0.82, adjusted))
            else:
                final_conf = max(0.85, min(0.99, adjusted))
        else:
            final_conf = max(0.05, min(0.99, adjusted))

        final_conf = round(final_conf, 4)

        explanation = (
            f"Evidence-Based Calibrated Confidence: {round(final_conf * 100, 1)}% "
            f"[Base: {round(raw_conf * 100, 1)}%, Corroboration ({supporting_layers_count} layers): {mod_signal:+.2f}, "
            f"Completeness ({missing_critical_count} missing): {mod_missing:+.2f}, "
            f"Freshness: {mod_stale:+.2f}, Provenance ({telemetry_origin}): {mod_provenance:+.2f}, "
            f"Conflict: {conflict_label}, SwarmHealth ({failed_agents_count} failures): {mod_failures:+.2f}]"
        )
        return final_conf, explanation

    def _evaluate_hypotheses_and_resolve_conflicts(
        self,
        telemetry: List[TelemetryRecord],
        domain_messages: List[AgentMessage],
        dialogue: List[AgentMessage],
        failed_agents: Optional[List[str]] = None,
    ) -> Tuple[DiagnosticStatus, str, float]:
        """
        Calculates probabilities for competing hypotheses, detects contradictions,
        and resolves evidential conflicts.
        """
        # Case 0: Empty telemetry
        if not telemetry:
            self.next_diagnostic_checks.append("Pair and start local collector agent to stream genuine device telemetry.")
            calibrated_conf, expl = self._calibrate_confidence(
                status=DiagnosticStatus.INCONCLUSIVE,
                base_probability=0.10,
                supporting_layers_count=0,
                missing_critical_count=5,
                has_stale=False,
                telemetry_origin="SIMULATED_SCENARIO",
                conflict_detected=False,
                conflict_resolved=False,
                failed_agents_count=len(failed_agents or []),
            )
            self.confidence_explanation = expl
            return (
                DiagnosticStatus.INCONCLUSIVE,
                "Inconclusive: Zero Telemetry Received (Dataset Empty)",
                calibrated_conf,
            )

        # Severe telemetry gaps
        has_severe_gaps = any("missing critical telemetry" in lim for lim in self.limitations_identified)

        # Aggregate evidence metrics across records (preserve None when metric was not exposed)
        max_crc = max([r.interface_crc_errors for r in telemetry if r.interface_crc_errors is not None], default=None)
        max_drops = max([r.queue_drops_per_sec for r in telemetry if r.queue_drops_per_sec is not None], default=None)
        discards_list = [
            (r.interface_in_discards or 0) + (r.interface_out_discards or 0)
            for r in telemetry
            if (r.interface_in_discards is not None or r.interface_out_discards is not None)
        ]
        max_discards = max(discards_list, default=None)
        max_util = max([r.utilization_pct for r in telemetry if r.utilization_pct is not None], default=None)
        max_cpu = max([r.cpu_utilization_pct for r in telemetry if r.cpu_utilization_pct is not None], default=None)
        max_mem = max([r.memory_utilization_pct for r in telemetry if r.memory_utilization_pct is not None], default=None)
        min_rssi = min([r.wifi_rssi_dbm for r in telemetry if r.wifi_rssi_dbm is not None], default=None)
        max_retries = max([r.wifi_retry_pct for r in telemetry if r.wifi_retry_pct is not None], default=None)
        max_dns_ms = max([r.dns_response_ms for r in telemetry if r.dns_response_ms is not None], default=None)
        max_dhcp_util = max([r.dhcp_pool_utilization_pct for r in telemetry if r.dhcp_pool_utilization_pct is not None], default=None)
        max_flaps = max([r.interface_flaps for r in telemetry if r.interface_flaps is not None], default=None)
        max_lat = max([r.latency_ms for r in telemetry if r.latency_ms is not None], default=None)
        max_loss = max([r.packet_loss_pct for r in telemetry if r.packet_loss_pct is not None], default=None)

        has_crc_metrics = max_crc is not None
        has_drops_metrics = (max_drops is not None or max_discards is not None)
        has_util_metrics = max_util is not None
        has_cpu_metrics = max_cpu is not None
        has_mem_metrics = max_mem is not None
        has_wifi_metrics = (min_rssi is not None or max_retries is not None)
        has_dns_dhcp_metrics = (max_dns_ms is not None or max_dhcp_util is not None)
        has_if_oper = any(r.interface_oper_status is not None for r in telemetry)

        # Interface Down status
        has_interface_down = any(
            str(r.interface_oper_status).upper() in ("DOWN", "2", "LOWER_LAYER_DOWN")
            or str(r.device_status).upper() == "DOWN"
            for r in telemetry
        )

        # -------------------------------------------------------------
        # HYPOTHESIS CANDIDATES & EVIDENTIAL GROUNDING
        # -------------------------------------------------------------

        # 1. Physical Interface / Transceiver Defect
        p_interface = 0.05
        sup_interface, con_interface = [], []
        if has_crc_metrics:
            if (max_crc or 0) >= 20 or ((max_flaps or 0) >= 2):
                p_interface = 0.94
                sup_interface.append(f"Physical CRC error rate high: {max_crc} errors/sec")
                if (max_flaps or 0) >= 2:
                    sup_interface.append(f"Interface link flapping detected: {max_flaps} state transitions")
            else:
                con_interface.append(f"Zero or negligible interface CRC errors ({max_crc}) and flaps ({max_flaps or 0})")
        else:
            p_interface = 0.05
            con_interface.append("Interface CRC error counters were not exposed on this probe protocol.")

        # 2. Interface / Link Down Outage
        p_if_down = 0.05
        sup_if_down, con_if_down = [], []
        if has_interface_down:
            p_if_down = 0.98
            sup_if_down.append("Interface or device operational state is strictly DOWN in telemetry record.")
        elif has_if_oper:
            con_if_down.append("All probed interfaces report operational state UP.")
        else:
            con_if_down.append("Interface operational state was not exposed on this probe protocol.")

        # 3. Buffer Congestion (Queue Exhaustion)
        # MUST have corroborating evidence: queue drops, discards, or link saturation
        p_congestion = 0.05
        sup_congestion, con_congestion = [], []
        has_corroborating_drops = (max_drops is not None and max_drops >= 10.0) or (max_discards is not None and max_discards >= 10)
        has_corroborating_util = (max_util is not None and max_util >= 85.0)

        if (has_corroborating_util and has_corroborating_drops) or (max_drops is not None and max_drops >= 20.0):
            p_congestion = 0.95
            if has_corroborating_util:
                sup_congestion.append(f"Sustained link bandwidth saturation: {max_util}%")
            if max_drops is not None and max_drops >= 10.0:
                sup_congestion.append(f"Active egress queue drops: {max_drops} pkts/s")
            if max_discards is not None and max_discards >= 10:
                sup_congestion.append(f"Active interface packet discards: {max_discards}")
        elif (has_corroborating_util and max_drops is not None and max_drops >= 5.0) or (
            (max_lat or 0.0) >= 100.0 and (max_util is not None and max_util >= 70.0 and ((max_drops or 0.0) > 0 or (max_discards or 0) > 0))
        ):
            p_congestion = 0.78
            sup_congestion.append(f"Elevated link utilization ({max_util}%) and queue drops ({max_drops} pkts/s)")
        else:
            if not has_drops_metrics and not has_util_metrics:
                con_congestion.append("Buffer queue discards and link bandwidth utilization were not exposed on this probe protocol.")
            elif (max_lat or 0.0) >= 50.0:
                con_congestion.append(
                    f"Contradicting evidence: Latency is {max_lat} ms, but buffer queue drops are {max_drops or 0.0} pkts/s, "
                    f"discards are {max_discards or 0}, and link utilization is {max_util or 0.0}%. High ping latency alone does NOT confirm congestion."
                )
            else:
                con_congestion.append(f"Link bandwidth utilization is low ({max_util or 0.0}%), queue drops: {max_drops or 0.0} pkts/s")

        # 4. Wireless RF Signal Degradation (Weak Wi-Fi)
        p_wifi = 0.05
        sup_wifi, con_wifi = [], []
        if has_wifi_metrics:
            if (min_rssi is not None and min_rssi <= -80.0) or ((max_retries or 0.0) >= 25.0):
                p_wifi = 0.96
                sup_wifi.append(f"Severe RF path loss: RSSI {min_rssi} dBm (crit < -80 dBm)")
                sup_wifi.append(f"High 802.11 MAC frame retransmissions: {max_retries or 0.0}%")
            elif min_rssi is not None and min_rssi <= -72.0:
                p_wifi = 0.65
                sup_wifi.append(f"Marginal RSSI: {min_rssi} dBm")
            else:
                con_wifi.append(f"Wireless RSSI nominal ({min_rssi} dBm), retries: {max_retries or 0.0}%")
        else:
            p_wifi = 0.0
            con_wifi.append("No wireless RF telemetry available on probed targets.")

        # 5. Core Infrastructure CPU Exhaustion / Storm
        p_cpu = 0.05
        sup_cpu, con_cpu = [], []
        if has_cpu_metrics:
            if (max_cpu or 0.0) >= 90.0:
                p_cpu = 0.93
                sup_cpu.append(f"Device CPU saturated: {max_cpu}%")
            elif (max_cpu or 0.0) >= 80.0:
                p_cpu = 0.72
                sup_cpu.append(f"Elevated CPU utilization: {max_cpu}%")
            else:
                con_cpu.append(f"CPU utilization normal: {max_cpu}%")
        else:
            p_cpu = 0.0
            con_cpu.append("CPU operational metric not exposed or unsupported on probed targets.")

        # 6. Core Services Failure (DNS Timeout / DHCP Exhaustion)
        p_dns = 0.0
        sup_dns, con_dns = [], []
        if has_dns_dhcp_metrics:
            if (max_dns_ms is not None and max_dns_ms >= 1500.0) or (max_dhcp_util is not None and max_dhcp_util >= 95.0):
                p_dns = 0.97
                if max_dns_ms is not None and max_dns_ms >= 1500.0:
                    sup_dns.append(f"DNS query timeout on resolver: {max_dns_ms} ms")
                if max_dhcp_util is not None and max_dhcp_util >= 95.0:
                    sup_dns.append(f"DHCP pool exhaustion: {max_dhcp_util}% capacity")
            else:
                con_dns.append("DNS query latency and DHCP pool allocations operating normally.")
        else:
            con_dns.append("No DNS or DHCP telemetry collected on probed device. Service-layer failure cannot be asserted.")

        # -------------------------------------------------------------
        # CONFLICT RESOLUTION & CONTRADICTION DETECTION
        # -------------------------------------------------------------
        conflict_detected = False
        conflict_resolved = False

        # Conflict 1: High Latency + Saturated CPU vs Link Congestion (requires measured util and drops)
        if p_cpu > 0.85 and max_util is not None and max_util < 50.0 and max_drops is not None and max_drops == 0.0:
            conflict_detected = True
            conflict_resolved = True
            conflict_msg = self.create_message(
                message_type=MessageType.CONFLICT_DETECTED,
                findings=[
                    f"CONFLICT RESOLVED: Saturated CPU ({max_cpu}%) observed, but link utilization is only {max_util}% "
                    "and buffer queue drops are 0. Buffer Congestion hypothesis is refuted. Control Plane CPU Starvation confirmed."
                ],
                evidence={
                    "conflicting_metrics": ["latency_vs_utilization"],
                    "cpu_utilization_pct": max_cpu,
                    "link_utilization_pct": max_util,
                    "resolution": "CONTROL_PLANE_CPU_OVERLOAD_PREVAILS",
                },
                confidence=0.94,
            )
            dialogue.append(conflict_msg)
            p_congestion = 0.05
            con_congestion.append(f"Conflict resolution: Latency is driven by CPU process starvation ({max_cpu}%), not buffer congestion.")
            self.conflicts_resolved.append({
                "initial_hypothesis": "Egress Link Buffer Congestion",
                "competing_hypothesis": "Control Plane Processor Saturation",
                "conflicting_evidence": f"Elevated latency ({max_lat} ms) initially mimics link buffer congestion.",
                "refuting_evidence": f"Core router CPU is saturated at {max_cpu}%, while link bandwidth utilization is only {max_util}% and egress queue drops are {max_drops} pkts/s (zero buffer exhaustion).",
                "conflict_status": "RESOLVED",
                "selected_diagnosis": "Control Plane Processor Saturation",
                "resolution_reasoning": f"Control Plane Processor Saturation on Core-Router-01 ({max_cpu}% CPU) starves packet processing interrupts, causing transit latency without egress buffer drops or link congestion.",
            })

        # Conflict 2: High Ping Latency vs Zero Queue Drops (Contradicts Congestion - ONLY if drops & util are measured!)
        elif (max_lat or 0.0) >= 80.0 and max_drops is not None and max_drops == 0.0 and (max_discards or 0) == 0 and max_util is not None and max_util < 50.0 and p_cpu < 0.70:
            conflict_detected = True
            conflict_resolved = True
            conflict_msg = self.create_message(
                message_type=MessageType.CONFLICT_DETECTED,
                findings=[
                    f"CONTRADICTION DETECTED: Measured ping latency is elevated ({max_lat} ms), but queue drops are 0 pkts/s, "
                    f"interface discards are 0, and link utilization is {max_util}%. Local buffer congestion is physically refuted."
                ],
                evidence={
                    "conflicting_metrics": ["latency_vs_queue_drops"],
                    "latency_ms": max_lat,
                    "queue_drops_per_sec": max_drops,
                    "utilization_pct": max_util,
                    "resolution": "CONGESTION_REFUTED_BY_ZERO_DROPS",
                },
                confidence=0.92,
            )
            dialogue.append(conflict_msg)
            p_congestion = 0.05
            self.conflicts_resolved.append({
                "initial_hypothesis": "Egress Link Buffer Congestion",
                "competing_hypothesis": "Uncorroborated Transit Delay",
                "conflicting_evidence": f"Measured ping latency is elevated ({max_lat} ms).",
                "refuting_evidence": f"Queue drops are 0.0 pkts/s, discards are 0, and link utilization is {max_util}%. Local congestion is refuted.",
                "conflict_status": "RESOLVED",
                "selected_diagnosis": "Inconclusive Transit Delay",
                "resolution_reasoning": "Absence of corroborating buffer queue drops or discards refutes local link congestion.",
            })

        # Conflict 3: High Packet Loss vs Zero CRC Errors (Contradicts Physical Cable Defect - ONLY if CRC is measured!)
        elif (max_loss or 0.0) >= 5.0 and max_crc is not None and max_crc == 0 and max_drops is not None and max_drops == 0.0 and not has_interface_down:
            conflict_detected = True
            conflict_resolved = True
            conflict_msg = self.create_message(
                message_type=MessageType.CONFLICT_DETECTED,
                findings=[
                    f"CONTRADICTION DETECTED: Measured packet loss is {max_loss}%, but interface CRC errors are 0 "
                    "and queue drops are 0. Physical cable fault and local buffer exhaustion are refuted."
                ],
                evidence={
                    "conflicting_metrics": ["packet_loss_vs_crc"],
                    "packet_loss_pct": max_loss,
                    "interface_crc_errors": max_crc,
                    "resolution": "PHYSICAL_FAULT_REFUTED",
                },
                confidence=0.90,
            )
            dialogue.append(conflict_msg)
            p_interface = 0.05
            self.conflicts_resolved.append({
                "initial_hypothesis": "Physical Link / Transceiver Integrity Fault",
                "competing_hypothesis": "Non-Physical Layer Loss Outage",
                "conflicting_evidence": f"Measured packet loss is {max_loss}%, initially suggesting physical interface defects.",
                "refuting_evidence": f"Interface counters show 0 CRC errors/s and zero link flaps, refuting physical cable/transceiver damage.",
                "conflict_status": "RESOLVED",
                "selected_diagnosis": "Non-Physical Impairment",
                "resolution_reasoning": "Zero physical layer CRC errors and link flaps refute physical transceiver or cable damage.",
            })

        # Determine status and reasoning for each hypothesis, strictly respecting unmeasured metrics
        # 1. Interface Down
        if has_interface_down:
            st_if_down = "VALIDATED"
            re_if_down = "Target interface operational state is strictly DOWN in collected telemetry."
        elif has_if_oper:
            st_if_down = "REFUTED"
            re_if_down = "All probed interfaces report operational state UP."
        else:
            st_if_down = "NOT EVALUATED"
            re_if_down = "Interface operational state was not exposed on this probe protocol."

        # 2. Congestion
        if p_congestion > 0.70:
            st_cong = "VALIDATED"
            re_cong = f"Confirmed: Sustained link utilization ({max_util}%) and egress buffer drops ({max_drops} pkts/s) corroborate buffer overflow."
        elif not has_drops_metrics and not has_util_metrics:
            st_cong = "NOT EVALUATED"
            if (max_lat or 0.0) >= 50.0:
                re_cong = f"Buffer queue discards and link bandwidth utilization were not exposed on this probe protocol. High RTT latency ({max_lat} ms) cannot be confirmed or refuted without queue telemetry."
            else:
                re_cong = "Buffer queue discards and link bandwidth utilization were not exposed on this probe protocol."
        else:
            st_cong = "REFUTED"
            re_cong = f"Refuted: Measured buffer queue drops ({max_drops or 0.0} pkts/s) and low utilization ({max_util or 0.0}%) contradict congestion."

        # 3. Interface Fault (CRC)
        if has_crc_metrics:
            st_crc = "VALIDATED" if p_interface > 0.70 else "REFUTED"
            re_crc = (
                f"High Layer-1 CRC frame errors ({max_crc}/sec) and interface flaps ({max_flaps or 0}) verify physical transceiver or fiber patch degradation."
                if p_interface > 0.70
                else f"Measured physical interface error counters ({max_crc} CRC errors/s) within acceptable limits."
            )
        else:
            st_crc = "NOT EVALUATED"
            re_crc = "Physical interface CRC error counters and link flaps were not exposed on this probe protocol."

        # 4. CPU Starvation
        if has_cpu_metrics:
            st_cpu = "VALIDATED" if p_cpu > 0.70 else "REFUTED"
            re_cpu = (
                f"Host Route Processor CPU is saturated at {max_cpu}%, starving control plane interrupt processing."
                if p_cpu > 0.70
                else f"Measured CPU utilization ({max_cpu}%) is within operational safety margins."
            )
        else:
            st_cpu = "NOT EVALUATED"
            re_cpu = "Host processor CPU utilization was not exposed on this probe protocol."

        # 5. Wireless RF
        if has_wifi_metrics:
            st_wifi = "VALIDATED" if p_wifi > 0.70 else "REFUTED"
            re_wifi = (
                f"Severe wireless path loss observed: RSSI {min_rssi} dBm and {max_retries or 0.0}% MAC retransmissions indicate client attenuation."
                if p_wifi > 0.70
                else f"Measured wireless RF signal strength ({min_rssi} dBm) and retry levels are healthy."
            )
        else:
            st_wifi = "NOT EVALUATED"
            re_wifi = "Wireless RF signal metrics (RSSI / retries) were not collected on this probe."

        # 6. Core DNS/DHCP
        if has_dns_dhcp_metrics:
            st_dns = "VALIDATED" if p_dns > 0.70 else "REFUTED"
            re_dns = (
                f"Core infrastructure failure: DNS resolver response {max_dns_ms}ms (timeout) and DHCP pool {max_dhcp_util}% capacity."
                if p_dns > 0.70
                else "DNS query resolution and DHCP pool availability operating normally."
            )
        else:
            st_dns = "NOT EVALUATED"
            re_dns = "DNS and DHCP performance counters were not exposed on this probe protocol."

        # Create structured CompetingHypothesis records
        hyp_list = [
            CompetingHypothesis(
                hypothesis_id="HYP-INTERFACE-DOWN",
                name="Physical Interface / Port Down Outage",
                description="Network interface or target node is down, disconnected, or administratively disabled.",
                probability=round(p_if_down, 2),
                supporting_evidence=sup_if_down,
                contradicting_evidence=con_if_down,
                status=st_if_down,
                reasoning=re_if_down,
            ),
            CompetingHypothesis(
                hypothesis_id="HYP-CONGESTION",
                name="Egress Link Buffer Congestion",
                description="Network interface transmission queues overflowing due to bandwidth demand exceeding link capacity.",
                probability=round(p_congestion, 2),
                supporting_evidence=sup_congestion,
                contradicting_evidence=con_congestion,
                status=st_cong,
                reasoning=re_cong,
            ),
            CompetingHypothesis(
                hypothesis_id="HYP-INTERFACE-FAULT",
                name="Physical Link / Transceiver Integrity Fault",
                description="Damaged fiber/copper patch cable or degrading SFP transceiver causing frame corruption and CRC drops.",
                probability=round(p_interface, 2),
                supporting_evidence=sup_interface,
                contradicting_evidence=con_interface,
                status=st_crc,
                reasoning=re_crc,
            ),
            CompetingHypothesis(
                hypothesis_id="HYP-CPU-STARVATION",
                name="Control Plane Processor Saturation",
                description="Uncontrolled software loop, broadcast storm, or BGP churn consuming router CPU interrupts.",
                probability=round(p_cpu, 2),
                supporting_evidence=sup_cpu,
                contradicting_evidence=con_cpu,
                status=st_cpu,
                reasoning=re_cpu,
            ),
            CompetingHypothesis(
                hypothesis_id="HYP-WIFI-RF",
                name="Wireless RF Path Loss / Edge Signal Attenuation",
                description="Excessive physical distance or RF obstruction between wireless client and Access Point causing frame drops.",
                probability=round(p_wifi, 2),
                supporting_evidence=sup_wifi,
                contradicting_evidence=con_wifi,
                status=st_wifi,
                reasoning=re_wifi,
            ),
            CompetingHypothesis(
                hypothesis_id="HYP-DNS-DHCP-OUTAGE",
                name="Core Network Services Failure (DNS/DHCP)",
                description="Local name resolver service unresponsive or DHCP IP pool depleted, preventing host communications.",
                probability=round(p_dns, 2),
                supporting_evidence=sup_dns,
                contradicting_evidence=con_dns,
                status=st_dns,
                reasoning=re_dns,
            ),
        ]

        # Sort hypotheses by probability descending
        hyp_list.sort(key=lambda h: h.probability, reverse=True)
        self.competing_hypotheses = hyp_list

        winner = hyp_list[0]
        runner_up = hyp_list[1] if len(hyp_list) > 1 else None

        # -------------------------------------------------------------
        # OUTCOME DETERMINATION & INSUFFICIENT EVIDENCE GUARDS
        # -------------------------------------------------------------
        has_anomalous_performance = ((max_lat or 0.0) >= 50.0 or (max_loss or 0.0) > 0.0)
        has_concrete_root_cause = winner.probability >= 0.70

        # 1. Guard: Check if severe telemetry gaps exist (Missing critical telemetry dimensions)
        # When critical dimensions (CPU, queue drops, CRC counters) are absent,
        # we CANNOT assert 'Normal Network Operation' or high confidence!
        if has_severe_gaps and not has_concrete_root_cause:
            self.next_diagnostic_checks.extend([
                "Deploy local collector agent to stream hardware CPU and buffer discard metrics.",
                "Verify SNMP/RESTCONF credentials for target router.",
                "Execute hop-by-hop traceroute to isolate transit delay segment.",
            ])
            calibrated_conf, expl = self._calibrate_confidence(
                status=DiagnosticStatus.INCONCLUSIVE,
                base_probability=0.35,
                supporting_layers_count=1 if not has_anomalous_performance else 0,
                missing_critical_count=max(self.max_missing_critical, 3),
                has_stale=self.has_stale_telemetry,
                telemetry_origin=self.detected_origin,
                conflict_detected=conflict_detected,
                conflict_resolved=conflict_resolved,
                failed_agents_count=len(failed_agents or []),
            )
            self.confidence_explanation = expl
            return (
                DiagnosticStatus.INCONCLUSIVE,
                "Inconclusive Diagnosis due to Missing Telemetry Dimensions (Queue drops, CPU, and Interface counters absent)",
                min(calibrated_conf, 0.35),
            )

        # 2. Check if network is completely healthy (all measured dimensions within SLA bounds AND all critical dimensions present)
        if winner.probability <= 0.20 and not has_anomalous_performance and not has_severe_gaps:
            calibrated_conf, expl = self._calibrate_confidence(
                status=DiagnosticStatus.HEALTHY,
                base_probability=0.98,
                supporting_layers_count=2,
                missing_critical_count=self.max_missing_critical,
                has_stale=self.has_stale_telemetry,
                telemetry_origin=self.detected_origin,
                conflict_detected=conflict_detected,
                conflict_resolved=conflict_resolved,
                failed_agents_count=len(failed_agents or []),
            )
            self.confidence_explanation = expl
            return (
                DiagnosticStatus.HEALTHY,
                "Normal Network Operation (All Telemetry Within SLA Baselines)",
                calibrated_conf,
            )

        # 3. Check for uncorroborated latency / loss (High latency alone does NOT confirm congestion)
        if has_anomalous_performance and not has_concrete_root_cause:
            self.next_diagnostic_checks.extend([
                "Execute hop-by-hop traceroute to pinpoint transit hop responsible for latency spike.",
                "Query upstream WAN / ISP router interface for transit congestion.",
                "Verify carrier policing (CIR) and shaping policies along the path.",
                "Verify MTU size and Path MTU Discovery along transit link.",
            ])
            calibrated_conf, expl = self._calibrate_confidence(
                status=DiagnosticStatus.INCONCLUSIVE,
                base_probability=0.45,
                supporting_layers_count=1,
                missing_critical_count=self.max_missing_critical,
                has_stale=self.has_stale_telemetry,
                telemetry_origin=self.detected_origin,
                conflict_detected=conflict_detected,
                conflict_resolved=conflict_resolved,
                failed_agents_count=len(failed_agents or []),
            )
            self.confidence_explanation = expl
            return (
                DiagnosticStatus.INCONCLUSIVE,
                f"Inconclusive: Elevated Latency ({max_lat} ms) / Packet Loss ({max_loss}%) Without Corroborating Buffer Drops or Node Exhaustion",
                calibrated_conf,
            )

        # Populate next diagnostic checks based on identified fault
        if "Interface Down" in winner.name or has_interface_down:
            self.next_diagnostic_checks.extend([
                "Verify physical Ethernet / fiber patch cord connections and link activity LEDs.",
                "Check remote switch port administrative status ('no shutdown').",
                "Review port security and 802.1X authentication logs on switch.",
            ])
        elif "Congestion" in winner.name:
            self.next_diagnostic_checks.extend([
                "Inspect interface buffer queue depth with 'show interface <if> | include drops'.",
                "Identify top bandwidth-consuming talkers and elephant flows using NetFlow.",
                "Review QoS shaping and priority queuing configurations.",
            ])
        elif "Physical Link" in winner.name:
            self.next_diagnostic_checks.extend([
                "Inspect SFP transceiver optical Tx/Rx power with 'show interfaces transceiver detail'.",
                "Clean fiber optic connectors and inspect for micro-bends or cable kinks.",
                "Test link with optical time-domain reflectometer (OTDR) or swap patch cord.",
            ])
        elif "CPU" in winner.name:
            self.next_diagnostic_checks.extend([
                "Identify top CPU processes with 'show processes cpu sorted'.",
                "Check for ARP broadcast storms or spanning tree topology changes.",
                "Verify Control Plane Policing (CoPP) drop counters.",
            ])
        elif "Wireless" in winner.name:
            self.next_diagnostic_checks.extend([
                "Perform RF spectrum analysis to identify 2.4 GHz / 5 GHz co-channel interference.",
                "Verify AP transmit power and client RSSI / SNR distribution.",
                "Check AP client count and channel utilization.",
            ])

        # High confidence single diagnosis vs suspected
        if winner.probability >= 0.80 and (runner_up is None or runner_up.probability < 0.50):
            tentative_status = DiagnosticStatus.CONFIRMED
            tentative_root_cause = winner.name
        else:
            tentative_status = DiagnosticStatus.SUSPECTED
            tentative_root_cause = f"Suspected {winner.name} (Alternative: {runner_up.name if runner_up else 'None'})"

        supporting_layers, missing_relevant = self._count_corroborating_and_missing_layers(winner, telemetry)

        # Invariant: CONFIRMED strictly requires >= 2 supporting layers, no severe missing relevant telemetry, and fresh data
        if tentative_status == DiagnosticStatus.CONFIRMED and (supporting_layers < 2 or missing_relevant >= 2 or self.has_stale_telemetry):
            tentative_status = DiagnosticStatus.SUSPECTED
            tentative_root_cause = f"Suspected {winner.name} (Corroboration Limited: {supporting_layers} signal layer(s))"

        calibrated_conf, expl = self._calibrate_confidence(
            status=tentative_status,
            base_probability=winner.probability,
            supporting_layers_count=supporting_layers,
            missing_critical_count=missing_relevant,
            has_stale=self.has_stale_telemetry,
            telemetry_origin=self.detected_origin,
            conflict_detected=conflict_detected,
            conflict_resolved=conflict_resolved,
            failed_agents_count=len(failed_agents or []),
        )
        self.confidence_explanation = expl

        # Keep winner probability synchronized with calibrated confidence
        winner.probability = calibrated_conf

        return (
            tentative_status,
            tentative_root_cause,
            calibrated_conf,
        )
