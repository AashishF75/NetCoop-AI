"""
Performance Agent.
Analyzes traffic performance, congestion, latency spikes, jitter, packet loss, and buffer queue drops.
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

    def analyze(self, telemetry: List[TelemetryRecord]) -> List[AgentMessage]:
        self.set_status("ANALYZING", "Evaluating latency, loss, and queue drops")
        anomalies: List[AgentMessage] = []

        for record in telemetry:
            dev = record.device_id
            
            # 1. Evaluate Latency
            if record.latency_ms is not None:
                if record.latency_ms >= self.LATENCY_CRIT_MS:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="latency_ms",
                        value=record.latency_ms,
                        unit="ms",
                        evidence={
                            "observed": record.latency_ms,
                            "baseline": 5.0,
                            "threshold": self.LATENCY_CRIT_MS,
                            "severity": "CRITICAL",
                            "metric_type": "latency"
                        },
                        confidence=min(0.95, 0.70 + (record.latency_ms / 500.0) * 0.25),
                        findings=[
                            f"Critical latency spike on {dev}: {record.latency_ms} ms (threshold: {self.LATENCY_CRIT_MS} ms)"
                        ]
                    )
                    anomalies.append(msg)
                elif record.latency_ms >= self.LATENCY_WARN_MS:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="latency_ms",
                        value=record.latency_ms,
                        unit="ms",
                        evidence={
                            "observed": record.latency_ms,
                            "baseline": 5.0,
                            "threshold": self.LATENCY_WARN_MS,
                            "severity": "WARNING",
                            "metric_type": "latency"
                        },
                        confidence=0.75,
                        findings=[
                            f"Elevated latency on {dev}: {record.latency_ms} ms (baseline: 5.0 ms)"
                        ]
                    )
                    anomalies.append(msg)

            # 2. Evaluate Packet Loss
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
                        "metric_type": "packet_loss"
                    },
                    confidence=min(0.98, 0.80 + (record.packet_loss_pct / 100.0) * 0.18),
                    findings=[
                        f"Abnormal packet loss on {dev}: {record.packet_loss_pct}% ({severity})"
                    ]
                )
                anomalies.append(msg)

            # 3. Evaluate Link Utilization & Queue Drops (Congestion signature)
            is_util_high = record.utilization_pct is not None and record.utilization_pct >= self.UTIL_WARN_PCT
            has_queue_drops = record.queue_drops_per_sec is not None and record.queue_drops_per_sec > self.QUEUE_DROP_CRIT

            if is_util_high or has_queue_drops:
                util_val = record.utilization_pct or 0.0
                drops_val = record.queue_drops_per_sec or 0.0
                conf = 0.92 if (is_util_high and has_queue_drops) else 0.75

                msg = self.create_message(
                    message_type=MessageType.TELEMETRY_ANOMALY,
                    device_id=dev,
                    metric="queue_drops_per_sec" if has_queue_drops else "utilization_pct",
                    value=drops_val if has_queue_drops else util_val,
                    unit="pkts/s" if has_queue_drops else "%",
                    evidence={
                        "utilization_pct": util_val,
                        "queue_drops_per_sec": drops_val,
                        "bandwidth_mbps": record.bandwidth_mbps,
                        "throughput_mbps": record.throughput_mbps,
                        "severity": "CRITICAL" if (util_val > 95 or drops_val > 50) else "WARNING",
                        "metric_type": "congestion"
                    },
                    confidence=conf,
                    findings=[
                        f"Buffer congestion detected on {dev}: {util_val}% link utilization with {drops_val} queue drops/sec"
                    ]
                )
                anomalies.append(msg)

        self.findings_history.extend(anomalies)
        self.set_status("COMPLETE", f"Found {len(anomalies)} performance anomalies")
        return anomalies

    def handle_query(self, query: AgentMessage, telemetry: List[TelemetryRecord]) -> AgentMessage:
        """
        Responds to inquiries from Fault Correlation Agent.
        e.g., verifying if high packet loss is accompanied by buffer queue drops.
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
                evidence={"error": "DEVICE_NOT_FOUND"}
            )

        # Summarize device performance metrics
        rec = matching_records[-1]
        has_drops = (rec.queue_drops_per_sec or 0) > 5.0
        high_util = (rec.utilization_pct or 0) > 85.0
        high_loss = (rec.packet_loss_pct or 0) > 2.0

        is_buffer_congested = has_drops and high_util
        response_findings = []
        if is_buffer_congested:
            response_findings.append(
                f"CONFIRMED: Buffer exhaustion on {target_device}. "
                f"Queue drops: {rec.queue_drops_per_sec} pkts/s, Utilization: {rec.utilization_pct}%."
            )
        elif high_loss and not has_drops:
            response_findings.append(
                f"NOTE: Packet loss ({rec.packet_loss_pct}%) observed WITHOUT queue drops on {target_device}. "
                f"Likely non-congestion cause (physical/layer 1 or wireless RF)."
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
            value={"is_buffer_congested": is_buffer_congested, "has_queue_drops": has_drops},
            evidence={
                "latency_ms": rec.latency_ms,
                "packet_loss_pct": rec.packet_loss_pct,
                "queue_drops_per_sec": rec.queue_drops_per_sec,
                "utilization_pct": rec.utilization_pct,
            },
            confidence=0.92,
            findings=response_findings,
            target_agent_id=query.agent_id,
            correlation_id=query.correlation_id,
        )
        self.set_status("COMPLETE", "Query answered")
        return resp
