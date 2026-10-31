"""
Performance Agent.
Analyzes traffic performance, congestion, latency spikes, jitter, packet loss,
interface utilization, and buffer queue drops.
Strictly requires corroborating evidence (queue drops, discards, utilization)
before asserting congestion; never infers congestion from ping latency alone.
"""

from typing import List, Dict, Any, Optional
from app.agents.base_agent import BaseAgent
from app.protocol.schema import (
    AgentMessage,
    MessageType,
    TelemetryRecord,
)


class PerformanceAgent(BaseAgent):
    def __init__(self, agent_id: str = "perf-agent-01"):
        super().__init__(
            agent_id=agent_id,
            name="Performance Agent",
            role="Traffic & Congestion Analyzer",
        )
        # Performance baseline & thresholds
        self.LATENCY_WARN_MS = 50.0
        self.LATENCY_CRIT_MS = 100.0
        self.JITTER_CRIT_MS = 25.0
        self.LOSS_WARN_PCT = 1.0
        self.LOSS_CRIT_PCT = 5.0
        self.UTIL_WARN_PCT = 85.0
        self.UTIL_CRIT_PCT = 95.0
        self.QUEUE_DROP_CRIT = 20.0
        self.DISCARD_WARN_COUNT = 5

    def analyze(self, telemetry: List[TelemetryRecord]) -> List[AgentMessage]:
        self.set_status("ANALYZING", "Evaluating latency, loss, throughput, utilization, and queue drops")
        anomalies: List[AgentMessage] = []

        for record in telemetry:
            dev = record.device_id
            origin = getattr(record, "telemetry_origin", "SIMULATED_SCENARIO")

            # Check corroboration flags on this record
            drops_val = record.queue_drops_per_sec or 0.0
            in_discards = record.interface_in_discards or 0
            out_discards = record.interface_out_discards or 0
            total_discards = in_discards + out_discards
            util_val = record.utilization_pct

            has_queue_drops = drops_val > self.QUEUE_DROP_CRIT
            has_discards = total_discards >= self.DISCARD_WARN_COUNT
            is_util_high = util_val is not None and util_val >= self.UTIL_WARN_PCT
            has_corroborating_congestion_evidence = (
                has_queue_drops or has_discards or (is_util_high and (drops_val > 5.0 or total_discards > 0))
            )

            # ---------------------------------------------------------
            # 1. Evaluate Latency & Jitter (Do NOT assert congestion alone)
            # ---------------------------------------------------------
            if record.latency_ms is not None:
                lat = record.latency_ms
                if lat >= self.LATENCY_CRIT_MS:
                    if has_corroborating_congestion_evidence:
                        finding_note = (
                            f"Critical latency spike on {dev}: {lat} ms, corroborated by buffer exhaustion "
                            f"(queue drops: {drops_val} pkts/s, discards: {total_discards}, util: {util_val}%)."
                        )
                        c_type = "corroborated_congestion_latency"
                    else:
                        finding_note = (
                            f"Critical latency spike on {dev}: {lat} ms (threshold: {self.LATENCY_CRIT_MS} ms). "
                            f"Egress queue drops ({drops_val} pkts/s) and link utilization ({util_val or 0}%) "
                            "do NOT corroborate local buffer congestion. High ping latency alone does NOT confirm congestion."
                        )
                        c_type = "unexplained_transit_latency"

                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="latency_ms",
                        value=lat,
                        unit="ms",
                        evidence={
                            "observed": lat,
                            "baseline": 5.0,
                            "threshold": self.LATENCY_CRIT_MS,
                            "severity": "CRITICAL",
                            "metric_type": c_type,
                            "congestion_corroborated": has_corroborating_congestion_evidence,
                            "queue_drops_per_sec": drops_val,
                            "interface_discards": total_discards,
                            "utilization_pct": util_val,
                            "telemetry_origin": origin,
                        },
                        confidence=min(0.95, 0.70 + (lat / 500.0) * 0.25),
                        findings=[finding_note],
                    )
                    anomalies.append(msg)

                elif lat >= self.LATENCY_WARN_MS:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="latency_ms",
                        value=lat,
                        unit="ms",
                        evidence={
                            "observed": lat,
                            "baseline": 5.0,
                            "threshold": self.LATENCY_WARN_MS,
                            "severity": "WARNING",
                            "metric_type": "latency",
                            "congestion_corroborated": has_corroborating_congestion_evidence,
                            "queue_drops_per_sec": drops_val,
                            "interface_discards": total_discards,
                            "utilization_pct": util_val,
                            "telemetry_origin": origin,
                        },
                        confidence=0.75,
                        findings=[
                            f"Elevated latency on {dev}: {lat} ms (baseline: 5.0 ms). "
                            f"Congestion corroborated: {has_corroborating_congestion_evidence}."
                        ],
                    )
                    anomalies.append(msg)

            # Jitter anomaly
            if record.jitter_ms is not None and record.jitter_ms >= self.JITTER_CRIT_MS:
                msg = self.create_message(
                    message_type=MessageType.TELEMETRY_ANOMALY,
                    device_id=dev,
                    metric="jitter_ms",
                    value=record.jitter_ms,
                    unit="ms",
                    evidence={
                        "observed": record.jitter_ms,
                        "threshold": self.JITTER_CRIT_MS,
                        "severity": "WARNING",
                        "metric_type": "jitter",
                        "telemetry_origin": origin,
                    },
                    confidence=0.80,
                    findings=[f"Excessive packet jitter on {dev}: {record.jitter_ms} ms"],
                )
                anomalies.append(msg)

            # ---------------------------------------------------------
            # 2. Evaluate Packet Loss
            # ---------------------------------------------------------
            if record.packet_loss_pct is not None and record.packet_loss_pct >= self.LOSS_WARN_PCT:
                severity = "CRITICAL" if record.packet_loss_pct >= self.LOSS_CRIT_PCT else "WARNING"
                msg = self.create_message(
                    message_type=MessageType.TELEMETRY_ANOMALY,
                    device_id=dev,
                    metric="packet_loss_pct",
                    value=record.packet_loss_pct,
                    unit="%",
                    evidence={
                        "observed": record.packet_loss_pct,
                        "baseline": 0.0,
                        "threshold": self.LOSS_WARN_PCT,
                        "severity": severity,
                        "metric_type": "packet_loss",
                        "telemetry_origin": origin,
                    },
                    confidence=min(0.98, 0.80 + (record.packet_loss_pct / 100.0) * 0.18),
                    findings=[
                        f"Abnormal packet loss on {dev}: {record.packet_loss_pct}% ({severity})"
                    ],
                )
                anomalies.append(msg)

            # ---------------------------------------------------------
            # 3. Evaluate Interface Discards & Queue Drops (Congestion Evidence)
            # ---------------------------------------------------------
            if is_util_high or has_queue_drops or has_discards:
                effective_util = util_val if util_val is not None else 0.0
                conf = 0.94 if (is_util_high and (has_queue_drops or has_discards)) else 0.82

                metric_key = "queue_drops_per_sec" if has_queue_drops else ("utilization_pct" if is_util_high else "interface_discards")
                metric_val = drops_val if has_queue_drops else (effective_util if is_util_high else total_discards)
                metric_unit = "pkts/s" if has_queue_drops else ("%" if is_util_high else "pkts")

                msg = self.create_message(
                    message_type=MessageType.TELEMETRY_ANOMALY,
                    device_id=dev,
                    metric=metric_key,
                    value=metric_val,
                    unit=metric_unit,
                    evidence={
                        "utilization_pct": util_val,
                        "queue_drops_per_sec": drops_val,
                        "interface_in_discards": in_discards,
                        "interface_out_discards": out_discards,
                        "bandwidth_mbps": record.bandwidth_mbps,
                        "throughput_mbps": record.throughput_mbps,
                        "severity": "CRITICAL" if (effective_util > 95 or drops_val > 50 or total_discards > 50) else "WARNING",
                        "metric_type": "congestion",
                        "corroboration_status": "CORROBORATED_BY_TELEMETRY",
                        "telemetry_origin": origin,
                    },
                    confidence=conf,
                    findings=[
                        f"Buffer congestion substantiated on {dev}: {effective_util}% link utilization, "
                        f"{drops_val} queue drops/sec, {total_discards} interface discards."
                    ],
                )
                anomalies.append(msg)

        self.findings_history.extend(anomalies)
        self.set_status("COMPLETE", f"Found {len(anomalies)} performance anomalies")
        return anomalies

    def handle_query(self, query: AgentMessage, telemetry: List[TelemetryRecord]) -> AgentMessage:
        """
        Responds to inquiries from Fault Correlation Agent.
        Verifies whether high latency or packet loss is corroborated by buffer queue drops / discards.
        """
        self.received_messages.append(query)
        self.set_status("ANALYZING", f"Responding to query from {query.agent_id}")

        target_device = query.device_id
        matching_records = [r for r in telemetry if r.device_id == target_device] if target_device else telemetry

        if not matching_records:
            return self.create_message(
                message_type=MessageType.QUERY_RESPONSE,
                device_id=target_device,
                target_agent_id=query.agent_id,
                correlation_id=query.correlation_id,
                confidence=0.1,
                findings=[f"No telemetry records found for device '{target_device}' in performance database."],
                evidence={"error": "DEVICE_NOT_FOUND"},
            )

        rec = matching_records[-1]
        drops = rec.queue_drops_per_sec or 0.0
        in_disc = rec.interface_in_discards or 0
        out_disc = rec.interface_out_discards or 0
        discards = in_disc + out_disc
        high_util = (rec.utilization_pct or 0.0) >= self.UTIL_WARN_PCT
        has_drops = drops > 5.0 or discards > 5
        high_lat = (rec.latency_ms or 0.0) >= self.LATENCY_WARN_MS
        high_loss = (rec.packet_loss_pct or 0.0) >= self.LOSS_WARN_PCT

        # Strict corroboration check
        is_buffer_congested = (has_drops and high_util) or (drops > self.QUEUE_DROP_CRIT)
        is_congestion_refuted = high_lat and not has_drops and not high_util

        response_findings = []
        if is_buffer_congested:
            response_findings.append(
                f"CORROBORATED: Egress buffer exhaustion on {target_device}. "
                f"Queue drops: {drops} pkts/s, Discards: {discards}, Utilization: {rec.utilization_pct}%."
            )
        elif is_congestion_refuted:
            response_findings.append(
                f"REFUTED: High latency ({rec.latency_ms} ms) observed on {target_device} "
                f"WITHOUT corroborating queue drops (drops: {drops}, discards: {discards}, util: {rec.utilization_pct or 0}%). "
                "Buffer congestion hypothesis is physically contradicted."
            )
        elif high_loss and not has_drops:
            response_findings.append(
                f"NOTE: Packet loss ({rec.packet_loss_pct}%) observed WITHOUT queue drops on {target_device}. "
                "Likely non-congestion cause (physical link/layer 1 defect, wireless RF, or upstream policy drop)."
            )
        else:
            response_findings.append(
                f"Performance metrics for {target_device} show normal queue state. "
                f"Latency: {rec.latency_ms or 0}ms, Loss: {rec.packet_loss_pct or 0}%."
            )

        resp = self.create_message(
            message_type=MessageType.QUERY_RESPONSE,
            device_id=target_device,
            metric="performance_correlation",
            value={
                "is_buffer_congested": is_buffer_congested,
                "has_queue_drops": has_drops,
                "congestion_refuted": is_congestion_refuted,
            },
            evidence={
                "latency_ms": rec.latency_ms,
                "packet_loss_pct": rec.packet_loss_pct,
                "queue_drops_per_sec": drops,
                "interface_in_discards": in_disc,
                "interface_out_discards": out_disc,
                "utilization_pct": rec.utilization_pct,
                "telemetry_origin": getattr(rec, "telemetry_origin", "SIMULATED_SCENARIO"),
            },
            confidence=0.94,
            findings=response_findings,
            target_agent_id=query.agent_id,
            correlation_id=query.correlation_id,
        )
        self.set_status("COMPLETE", "Query answered")
        return resp
