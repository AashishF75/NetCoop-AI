"""
Infrastructure Health Agent.
Monitors node-level health: CPU, memory pressure, interface operational state,
CRC interface errors, and port flaps.
Strictly relies on real collected telemetry; never asserts hardware failure
on missing or uncorroborated data.
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
        self.set_status("ANALYZING", "Evaluating CPU, memory pressure, interface status, and CRC error rates")
        anomalies: List[AgentMessage] = []

        for record in telemetry:
            dev = record.device_id
            origin = getattr(record, "telemetry_origin", "SIMULATED_SCENARIO")
            if_id = getattr(record, "interface_id", None) or "interface-1"

            # ---------------------------------------------------------
            # 1. Interface Operational State (Interface Down)
            # ---------------------------------------------------------
            if record.interface_oper_status and str(record.interface_oper_status).upper() in ("DOWN", "2", "LOWER_LAYER_DOWN"):
                msg = self.create_message(
                    message_type=MessageType.TELEMETRY_ANOMALY,
                    device_id=dev,
                    metric="interface_oper_status",
                    value=record.interface_oper_status,
                    unit="state",
                    evidence={
                        "observed": record.interface_oper_status,
                        "interface_id": if_id,
                        "admin_status": record.interface_admin_status,
                        "severity": "CRITICAL",
                        "metric_type": "interface_state",
                        "telemetry_origin": origin,
                    },
                    confidence=0.99,
                    findings=[
                        f"Interface {if_id} on {dev} operational state is DOWN "
                        f"(admin-status: {record.interface_admin_status or 'UP'}). Physical link or peer disabled."
                    ],
                )
                anomalies.append(msg)

            # ---------------------------------------------------------
            # 2. Control Plane CPU Utilization
            # ---------------------------------------------------------
            if record.cpu_utilization_pct is not None:
                cpu = record.cpu_utilization_pct
                if cpu >= self.CPU_CRIT_PCT:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="cpu_utilization_pct",
                        value=cpu,
                        unit="%",
                        evidence={
                            "observed": cpu,
                            "baseline": 25.0,
                            "threshold": self.CPU_CRIT_PCT,
                            "severity": "CRITICAL",
                            "metric_type": "hardware_resource",
                            "telemetry_origin": origin,
                        },
                        confidence=min(0.96, 0.75 + (cpu / 100.0) * 0.22),
                        findings=[
                            f"Control plane CPU saturation on {dev}: {cpu}% (CRITICAL threshold: {self.CPU_CRIT_PCT}%)"
                        ],
                    )
                    anomalies.append(msg)
                elif cpu >= self.CPU_WARN_PCT:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="cpu_utilization_pct",
                        value=cpu,
                        unit="%",
                        evidence={
                            "observed": cpu,
                            "baseline": 25.0,
                            "threshold": self.CPU_WARN_PCT,
                            "severity": "WARNING",
                            "metric_type": "hardware_resource",
                            "telemetry_origin": origin,
                        },
                        confidence=0.72,
                        findings=[
                            f"Elevated CPU utilization on {dev}: {cpu}% (threshold: {self.CPU_WARN_PCT}%)"
                        ],
                    )
                    anomalies.append(msg)

            # ---------------------------------------------------------
            # 3. Memory Pressure Utilization
            # ---------------------------------------------------------
            if record.memory_utilization_pct is not None:
                mem = record.memory_utilization_pct
                if mem >= self.MEM_CRIT_PCT:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="memory_utilization_pct",
                        value=mem,
                        unit="%",
                        evidence={
                            "observed": mem,
                            "baseline": 45.0,
                            "threshold": self.MEM_CRIT_PCT,
                            "severity": "CRITICAL",
                            "metric_type": "memory_resource",
                            "telemetry_origin": origin,
                        },
                        confidence=0.93,
                        findings=[
                            f"Critical memory exhaustion on {dev}: {mem}% allocated (exhaustion threshold: {self.MEM_CRIT_PCT}%)"
                        ],
                    )
                    anomalies.append(msg)
                elif mem >= self.MEM_WARN_PCT:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="memory_utilization_pct",
                        value=mem,
                        unit="%",
                        evidence={
                            "observed": mem,
                            "baseline": 45.0,
                            "threshold": self.MEM_WARN_PCT,
                            "severity": "WARNING",
                            "metric_type": "memory_resource",
                            "telemetry_origin": origin,
                        },
                        confidence=0.75,
                        findings=[
                            f"Elevated memory pressure on {dev}: {mem}%"
                        ],
                    )
                    anomalies.append(msg)

            # ---------------------------------------------------------
            # 4. Interface CRC / Physical Errors (Layer 1 indicator)
            # ---------------------------------------------------------
            if record.interface_crc_errors is not None and record.interface_crc_errors > 0:
                crc = record.interface_crc_errors
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
                            "interface_id": if_id,
                            "baseline": 0,
                            "threshold": self.CRC_WARN_SEC,
                            "severity": severity,
                            "metric_type": "physical_interface",
                            "telemetry_origin": origin,
                        },
                        confidence=min(0.97, 0.82 + (crc / 1000.0) * 0.15),
                        findings=[
                            f"Physical interface integrity degradation on {dev} ({if_id}): {crc} CRC errors/sec ({severity})"
                        ],
                    )
                    anomalies.append(msg)

            # ---------------------------------------------------------
            # 5. Interface Link Flapping
            # ---------------------------------------------------------
            if record.interface_flaps is not None and record.interface_flaps >= self.FLAP_CRIT:
                flaps = record.interface_flaps
                msg = self.create_message(
                    message_type=MessageType.TELEMETRY_ANOMALY,
                    device_id=dev,
                    metric="interface_flaps",
                    value=flaps,
                    unit="flaps/window",
                    evidence={
                        "observed": flaps,
                        "interface_id": if_id,
                        "baseline": 0,
                        "threshold": self.FLAP_CRIT,
                        "severity": "CRITICAL",
                        "metric_type": "link_flapping",
                        "telemetry_origin": origin,
                    },
                    confidence=0.91,
                    findings=[
                        f"Unstable physical link on {dev} ({if_id}): {flaps} interface flaps detected"
                    ],
                )
                anomalies.append(msg)

            # ---------------------------------------------------------
            # 6. Overall Device Operational Status (DOWN / DEGRADED)
            # ---------------------------------------------------------
            if record.device_status and record.device_status.upper() in ["DOWN", "DEGRADED", "FLAPPING", "AUTH_REJECTED"]:
                msg = self.create_message(
                    message_type=MessageType.TELEMETRY_ANOMALY,
                    device_id=dev,
                    metric="device_status",
                    value=record.device_status,
                    unit="status",
                    evidence={
                        "observed": record.device_status,
                        "baseline": "UP",
                        "severity": "CRITICAL" if record.device_status.upper() in ("DOWN", "AUTH_REJECTED") else "WARNING",
                        "metric_type": "node_state",
                        "telemetry_origin": origin,
                    },
                    confidence=0.98,
                    findings=[
                        f"Device {dev} operational state is {record.device_status}"
                    ],
                )
                anomalies.append(msg)

        self.findings_history.extend(anomalies)
        self.set_status("COMPLETE", f"Found {len(anomalies)} infrastructure anomalies")
        return anomalies

    def handle_query(self, query: AgentMessage, telemetry: List[TelemetryRecord]) -> AgentMessage:
        """
        Responds to query from Fault Correlation Agent checking for physical L1/L2
        cable faults, interface status, memory pressure, or CPU exhaustion.
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
                evidence={"error": "DEVICE_NOT_FOUND"},
            )

        rec = matching_records[-1]
        crc = rec.interface_crc_errors or 0
        flaps = rec.interface_flaps or 0
        cpu = rec.cpu_utilization_pct or 0.0
        mem = rec.memory_utilization_pct or 0.0
        if_oper = (rec.interface_oper_status or "").upper()
        dev_stat = (rec.device_status or "").upper()

        has_physical_fault = crc > self.CRC_WARN_SEC or flaps > 1
        has_cpu_exhaustion = cpu > self.CPU_CRIT_PCT
        has_memory_pressure = mem > self.MEM_CRIT_PCT
        is_if_down = if_oper == "DOWN" or dev_stat == "DOWN"

        findings = []
        if has_physical_fault:
            findings.append(
                f"CONFIRMED PHYSICAL FAULT: {target_device} has {crc} CRC errors/sec and {flaps} flaps. "
                "Points to defective SFP transceiver or damaged patch cable."
            )
        elif is_if_down:
            findings.append(
                f"CONFIRMED INTERFACE DOWN: {target_device} operational state is DOWN. "
                f"Interface '{rec.interface_id or 'default'}' is offline."
            )
        elif has_cpu_exhaustion:
            findings.append(
                f"CONFIRMED CPU EXHAUSTION: {target_device} CPU at {cpu}%. "
                "Control plane unresponsive; packet drop is CPU-induced rather than cable issue."
            )
        elif has_memory_pressure:
            findings.append(
                f"CONFIRMED MEMORY PRESSURE: {target_device} RAM allocation at {mem}%. "
                "Buffers depleted due to system memory saturation."
            )
        else:
            findings.append(
                f"Infrastructure health on {target_device} is nominal (CPU: {cpu}%, RAM: {mem}%, CRC: {crc}, Status: {rec.device_status})."
            )

        resp = self.create_message(
            message_type=MessageType.QUERY_RESPONSE,
            device_id=target_device,
            metric="infrastructure_verification",
            value={
                "has_physical_fault": has_physical_fault,
                "has_interface_down": is_if_down,
                "has_cpu_exhaustion": has_cpu_exhaustion,
                "has_memory_pressure": has_memory_pressure,
                "crc_errors": crc,
                "cpu_utilization_pct": cpu,
                "memory_utilization_pct": mem,
            },
            evidence={
                "cpu_utilization_pct": cpu,
                "memory_utilization_pct": mem,
                "interface_crc_errors": crc,
                "interface_flaps": flaps,
                "interface_oper_status": rec.interface_oper_status,
                "device_status": rec.device_status,
                "telemetry_origin": getattr(rec, "telemetry_origin", "SIMULATED_SCENARIO"),
            },
            confidence=0.95,
            findings=findings,
            target_agent_id=query.agent_id,
            correlation_id=query.correlation_id,
        )
        self.set_status("COMPLETE", "Query answered")
        return resp
