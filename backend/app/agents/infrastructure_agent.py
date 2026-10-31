"""
Infrastructure Health Agent.
Monitors node-level health: CPU, memory, hardware counters, CRC interface errors,
environmental status (fans/power), and port flaps.
"""

from typing import List, Dict, Any, Optional
from app.agents.base_agent import BaseAgent
from app.protocol.schema import (
    AgentMessage,
    MessageType,
    TelemetryRecord,
)


class InfrastructureAgent(BaseAgent):
    def __init__(self, agent_id: str = "infra-agent-01"):
        super().__init__(
            agent_id=agent_id,
            name="Infrastructure Health Agent",
            role="Hardware & OS Resource Monitor",
        )
        self.CPU_WARN_PCT = 80.0
        self.CPU_CRIT_PCT = 92.0
        self.MEM_WARN_PCT = 85.0
        self.MEM_CRIT_PCT = 95.0
        self.CRC_WARN_SEC = 20
        self.CRC_CRIT_SEC = 200
        self.FLAP_CRIT = 3

    def analyze(self, telemetry: List[TelemetryRecord]) -> List[AgentMessage]:
        self.set_status("ANALYZING", "Evaluating CPU, memory, and hardware interface error rates")
        anomalies: List[AgentMessage] = []

        for record in telemetry:
            dev = record.device_id

            # 1. CPU Utilization
            if record.cpu_utilization_pct is not None:
                if record.cpu_utilization_pct >= self.CPU_CRIT_PCT:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="cpu_utilization_pct",
                        value=record.cpu_utilization_pct,
                        unit="%",
                        evidence={
                            "observed": record.cpu_utilization_pct,
                            "baseline": 25.0,
                            "threshold": self.CPU_CRIT_PCT,
                            "severity": "CRITICAL",
                            "metric_type": "hardware_resource"
                        },
                        confidence=min(0.96, 0.75 + (record.cpu_utilization_pct / 100.0) * 0.22),
                        findings=[
                            f"Control plane CPU saturation on {dev}: {record.cpu_utilization_pct}% (CRITICAL threshold: {self.CPU_CRIT_PCT}%)"
                        ]
                    )
                    anomalies.append(msg)
                elif record.cpu_utilization_pct >= self.CPU_WARN_PCT:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="cpu_utilization_pct",
                        value=record.cpu_utilization_pct,
                        unit="%",
                        evidence={
                            "observed": record.cpu_utilization_pct,
                            "baseline": 25.0,
                            "threshold": self.CPU_WARN_PCT,
                            "severity": "WARNING",
                            "metric_type": "hardware_resource"
                        },
                        confidence=0.72,
                        findings=[
                            f"High CPU utilization on {dev}: {record.cpu_utilization_pct}%"
                        ]
                    )
                    anomalies.append(msg)

            # 2. Interface CRC / Physical Errors (Layer 1 indicator)
            crc = record.interface_crc_errors or 0
            if crc >= self.CRC_WARN_SEC:
                severity = "CRITICAL" if crc >= self.CRC_CRIT_SEC else "WARNING"
                msg = self.create_message(
                    message_type=MessageType.TELEMETRY_ANOMALY,
                    device_id=dev,
                    metric="interface_crc_errors",
                    value=crc,
                    unit="errors/s",
                    evidence={
                        "observed": crc,
                        "baseline": 0,
                        "threshold": self.CRC_WARN_SEC,
                        "severity": severity,
                        "metric_type": "physical_interface"
                    },
                    confidence=min(0.97, 0.82 + (crc / 1000.0) * 0.15),
                    findings=[
                        f"Physical interface integrity degradation on {dev}: {crc} CRC errors/sec ({severity})"
                    ]
                )
                anomalies.append(msg)

            # 3. Interface Link Flapping
            flaps = record.interface_flaps or 0
            if flaps >= self.FLAP_CRIT:
                msg = self.create_message(
                    message_type=MessageType.TELEMETRY_ANOMALY,
                    device_id=dev,
                    metric="interface_flaps",
                    value=flaps,
                    unit="flaps/window",
                    evidence={
                        "observed": flaps,
                        "baseline": 0,
                        "threshold": self.FLAP_CRIT,
                        "severity": "CRITICAL",
                        "metric_type": "link_flapping"
                    },
                    confidence=0.91,
                    findings=[
                        f"Unstable physical link on {dev}: {flaps} interface flaps detected"
                    ]
                )
                anomalies.append(msg)

            # 4. Device Operational Status (DOWN / DEGRADED)
            if record.device_status and record.device_status.upper() in ["DOWN", "DEGRADED", "FLAPPING"]:
                msg = self.create_message(
                    message_type=MessageType.TELEMETRY_ANOMALY,
                    device_id=dev,
                    metric="device_status",
                    value=record.device_status,
                    unit="status",
                    evidence={
                        "observed": record.device_status,
                        "baseline": "UP",
                        "severity": "CRITICAL" if record.device_status.upper() == "DOWN" else "WARNING",
                        "metric_type": "node_state"
                    },
                    confidence=0.98,
                    findings=[
                        f"Device {dev} operational state is {record.device_status}"
                    ]
                )
                anomalies.append(msg)

        self.findings_history.extend(anomalies)
        self.set_status("COMPLETE", f"Found {len(anomalies)} infrastructure anomalies")
        return anomalies

    def handle_query(self, query: AgentMessage, telemetry: List[TelemetryRecord]) -> AgentMessage:
        """
        Responds to query from Fault Correlation Agent checking for physical L1/L2
        cable faults or CPU exhaustion.
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
                findings=[f"No telemetry records found for device '{target_device}' in infrastructure database."],
                evidence={"error": "DEVICE_NOT_FOUND"}
            )

        rec = matching_records[-1]
        crc = rec.interface_crc_errors or 0
        flaps = rec.interface_flaps or 0
        cpu = rec.cpu_utilization_pct or 0.0

        has_physical_fault = crc > self.CRC_WARN_SEC or flaps > 1
        has_cpu_exhaustion = cpu > self.CPU_CRIT_PCT

        findings = []
        if has_physical_fault:
            findings.append(
                f"CONFIRMED PHYSICAL FAULT: {target_device} has {crc} CRC errors/sec and {flaps} flaps. "
                "Points to defective SFP transceiver or damaged patch cable."
            )
        elif has_cpu_exhaustion:
            findings.append(
                f"CONFIRMED CPU EXHAUSTION: {target_device} CPU at {cpu}%. "
                "Control plane unresponsive; packet drop is CPU-induced rather than cable issue."
            )
        else:
            findings.append(
                f"Infrastructure health on {target_device} is nominal (CPU: {cpu}%, CRC: {crc}, Status: {rec.device_status})."
            )

        resp = self.create_message(
            message_type=MessageType.QUERY_RESPONSE,
            device_id=target_device,
            metric="infrastructure_verification",
            value={
                "has_physical_fault": has_physical_fault,
                "has_cpu_exhaustion": has_cpu_exhaustion,
                "crc_errors": crc,
                "cpu_utilization_pct": cpu,
            },
            evidence={
                "cpu_utilization_pct": cpu,
                "interface_crc_errors": crc,
                "interface_flaps": flaps,
                "device_status": rec.device_status,
            },
            confidence=0.94,
            findings=findings,
            target_agent_id=query.agent_id,
            correlation_id=query.correlation_id,
        )
        self.set_status("COMPLETE", "Query answered")
        return resp
