"""
Network Digital Twin Engine for NetCoop AI.
Provides deterministic modeling of the simulated network environment, device dependencies,
health scoring, and SLA compliance tracking.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.protocol.schema import (
    DigitalTwinDevice,
    DigitalTwinSnapshot,
    DeviceOperationalStatus,
    SLAStatus,
    TelemetryRecord,
)
from app.scenarios.generator import get_default_topology


DEVICE_DEPENDENCY_GRAPH = {
    "Core-Router-01": {
        "name": "Core Router 01",
        "device_type": "router",
        "role": "Core Gateway",
        "ip": "10.0.0.1",
        "upstream": [],
        "downstream": ["Agg-Switch-01"],
    },
    "Agg-Switch-01": {
        "name": "Aggregation Switch 01",
        "device_type": "switch",
        "role": "Distribution Layer",
        "ip": "10.0.0.2",
        "upstream": ["Core-Router-01"],
        "downstream": ["Edge-Switch-01", "Edge-Switch-02"],
    },
    "Edge-Switch-01": {
        "name": "Edge Switch 01",
        "device_type": "switch",
        "role": "Wired Access Layer",
        "ip": "10.0.1.1",
        "upstream": ["Agg-Switch-01"],
        "downstream": ["AP-01", "AP-02"],
    },
    "Edge-Switch-02": {
        "name": "Edge Switch 02",
        "device_type": "switch",
        "role": "Server Farm Access Layer",
        "ip": "10.0.2.1",
        "upstream": ["Agg-Switch-01"],
        "downstream": ["DNS-Server-01", "Database-Server-01"],
    },
    "AP-01": {
        "name": "Access Point 01",
        "device_type": "ap",
        "role": "Enterprise Wi-Fi",
        "ip": "10.0.3.10",
        "upstream": ["Edge-Switch-01"],
        "downstream": [],
    },
    "AP-02": {
        "name": "Access Point 02",
        "device_type": "ap",
        "role": "Enterprise Wi-Fi",
        "ip": "10.0.3.20",
        "upstream": ["Edge-Switch-01"],
        "downstream": [],
    },
    "DNS-Server-01": {
        "name": "DNS / DHCP Server",
        "device_type": "server",
        "role": "Core Infrastructure Services",
        "ip": "10.0.0.53",
        "upstream": ["Edge-Switch-02"],
        "downstream": [],
    },
    "Database-Server-01": {
        "name": "Production DB Server",
        "device_type": "server",
        "role": "Primary Database Host",
        "ip": "10.0.0.60",
        "upstream": ["Edge-Switch-02"],
        "downstream": [],
    },
}

BASELINE_SLA_BOUNDS = {
    "latency_ms": {"baseline": 5.0, "max_sla": 20.0, "unit": "ms"},
    "packet_loss_pct": {"baseline": 0.0, "max_sla": 1.0, "unit": "%"},
    "cpu_utilization_pct": {"baseline": 25.0, "max_sla": 80.0, "unit": "%"},
    "utilization_pct": {"baseline": 35.0, "max_sla": 85.0, "unit": "%"},
    "queue_drops_per_sec": {"baseline": 0.0, "max_sla": 5.0, "unit": "pkts/s"},
    "interface_crc_errors": {"baseline": 0, "max_sla": 10, "unit": "errors/s"},
    "wifi_rssi_dbm": {"baseline": -55.0, "min_sla": -72.0, "unit": "dBm"},
    "wifi_retry_pct": {"baseline": 3.0, "max_sla": 15.0, "unit": "%"},
    "dns_response_ms": {"baseline": 12.0, "max_sla": 100.0, "unit": "ms"},
    "dhcp_pool_utilization_pct": {"baseline": 45.0, "max_sla": 85.0, "unit": "%"},
}


class DigitalTwinEngine:
    """
    Constructs and updates the Network Digital Twin based on current telemetry,
    topological dependencies, and diagnostic findings.
    """

    def __init__(self):
        self.cached_snapshot: Optional[DigitalTwinSnapshot] = None

    def build_snapshot(
        self,
        telemetry: List[TelemetryRecord],
        implicated_devices: Optional[List[str]] = None,
        fault_propagation_paths: Optional[List[List[str]]] = None,
        root_cause: Optional[str] = None,
    ) -> DigitalTwinSnapshot:
        """
        Builds a comprehensive DigitalTwinSnapshot using telemetry records.
        """
        implicated_set = set(implicated_devices or [])
        paths = fault_propagation_paths or []

        # Index telemetry by device_id
        telemetry_by_device: Dict[str, TelemetryRecord] = {
            t.device_id: t for t in telemetry
        }

        devices: List[DigitalTwinDevice] = []
        total_health = 0.0
        sla_compliant_count = 0
        active_incidents = 0

        for dev_id, meta in DEVICE_DEPENDENCY_GRAPH.items():
            record = telemetry_by_device.get(dev_id)
            anomalies: List[str] = []
            health = 100.0
            sla_status = SLAStatus.COMPLIANT

            current_telem: Dict[str, Any] = {}
            if record:
                current_telem = {
                    "latency_ms": record.latency_ms,
                    "jitter_ms": record.jitter_ms,
                    "packet_loss_pct": record.packet_loss_pct,
                    "cpu_utilization_pct": record.cpu_utilization_pct,
                    "utilization_pct": record.utilization_pct,
                    "queue_drops_per_sec": record.queue_drops_per_sec,
                    "interface_crc_errors": record.interface_crc_errors,
                    "wifi_rssi_dbm": record.wifi_rssi_dbm,
                    "wifi_retry_pct": record.wifi_retry_pct,
                    "dns_response_ms": record.dns_response_ms,
                    "dhcp_pool_utilization_pct": record.dhcp_pool_utilization_pct,
                }

                # Check CPU
                if record.cpu_utilization_pct is not None:
                    if record.cpu_utilization_pct > 90.0:
                        anomalies.append(f"Critical CPU saturation: {record.cpu_utilization_pct}%")
                        health -= 45.0
                        sla_status = SLAStatus.BREACHED
                    elif record.cpu_utilization_pct > 80.0:
                        anomalies.append(f"Elevated CPU utilization: {record.cpu_utilization_pct}%")
                        health -= 20.0
                        if sla_status != SLAStatus.BREACHED:
                            sla_status = SLAStatus.AT_RISK

                # Check Latency
                if record.latency_ms is not None:
                    if record.latency_ms > 80.0:
                        anomalies.append(f"High round-trip latency: {record.latency_ms} ms")
                        health -= 30.0
                        sla_status = SLAStatus.BREACHED
                    elif record.latency_ms > 20.0:
                        anomalies.append(f"Elevated latency: {record.latency_ms} ms")
                        health -= 15.0
                        if sla_status != SLAStatus.BREACHED:
                            sla_status = SLAStatus.AT_RISK

                # Check Packet Loss
                if record.packet_loss_pct is not None and record.packet_loss_pct > 1.0:
                    anomalies.append(f"Packet loss detected: {record.packet_loss_pct}%")
                    health -= 25.0
                    sla_status = SLAStatus.BREACHED

                # Check Link Utilization
                if record.utilization_pct is not None and record.utilization_pct > 90.0:
                    anomalies.append(f"Link bandwidth near capacity: {record.utilization_pct}%")
                    health -= 30.0
                    sla_status = SLAStatus.BREACHED

                # Check Queue Drops
                if record.queue_drops_per_sec is not None and record.queue_drops_per_sec > 10.0:
                    anomalies.append(f"Egress queue drops: {record.queue_drops_per_sec} pkts/s")
                    health -= 25.0
                    sla_status = SLAStatus.BREACHED

                # Check Interface CRC Errors
                if record.interface_crc_errors is not None and record.interface_crc_errors > 20:
                    anomalies.append(f"Interface CRC errors: {record.interface_crc_errors} err/s")
                    health -= 40.0
                    sla_status = SLAStatus.BREACHED

                # Check Wi-Fi RSSI
                if record.wifi_rssi_dbm is not None and record.wifi_rssi_dbm < -75.0:
                    anomalies.append(f"Weak wireless RSSI: {record.wifi_rssi_dbm} dBm")
                    health -= 35.0
                    sla_status = SLAStatus.BREACHED

                # Check DNS
                if record.dns_response_ms is not None and record.dns_response_ms > 500.0:
                    anomalies.append(f"Slow DNS resolution: {record.dns_response_ms} ms")
                    health -= 35.0
                    sla_status = SLAStatus.BREACHED
            else:
                # Default nominal telemetry for unrepresented devices in sparse scenarios
                current_telem = {
                    "latency_ms": 3.2,
                    "jitter_ms": 0.4,
                    "packet_loss_pct": 0.0,
                    "cpu_utilization_pct": 18.0,
                    "utilization_pct": 24.0,
                    "queue_drops_per_sec": 0.0,
                    "interface_crc_errors": 0,
                }

            health = max(0.0, min(100.0, round(health, 1)))

            # Operational status based on health
            if health >= 85.0:
                op_status = DeviceOperationalStatus.OPTIMAL
            elif health >= 50.0:
                op_status = DeviceOperationalStatus.WARNING
            else:
                op_status = DeviceOperationalStatus.CRITICAL

            if sla_status == SLAStatus.COMPLIANT:
                sla_compliant_count += 1
            else:
                active_incidents += 1

            # Determine propagation role
            propagation_role = "NORMAL"
            is_implicated = dev_id in implicated_set
            if is_implicated:
                if paths and paths[0] and paths[0][0] == dev_id:
                    propagation_role = "ROOT_CAUSE"
                elif paths and any(dev_id in path[1:-1] for path in paths if len(path) > 2):
                    propagation_role = "TRANSIT_DEGRADED"
                else:
                    propagation_role = "AFFECTED_LEAF"

            twin_dev = DigitalTwinDevice(
                device_id=dev_id,
                name=meta["name"],
                device_type=meta["device_type"],
                role=meta["role"],
                ip=meta["ip"],
                status=op_status,
                health_score=health,
                sla_status=sla_status,
                upstream_dependencies=meta["upstream"],
                downstream_dependencies=meta["downstream"],
                current_telemetry=current_telem,
                baseline_sla=BASELINE_SLA_BOUNDS,
                active_anomalies=anomalies,
                implicated_in_fault=is_implicated,
                fault_propagation_role=propagation_role,
            )
            devices.append(twin_dev)
            total_health += health

        net_health_index = round(total_health / len(devices), 1) if devices else 100.0
        sla_pct = round((sla_compliant_count / len(devices)) * 100.0, 1) if devices else 100.0

        snapshot = DigitalTwinSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment_mode="BENCHMARK_DIGITAL_TWIN_SIMULATION",
            devices=devices,
            network_health_index=net_health_index,
            sla_compliance_pct=sla_pct,
            active_incidents_count=active_incidents,
            fault_propagation_paths=paths,
        )

        self.cached_snapshot = snapshot
        return snapshot

    def get_cached_or_default(self) -> DigitalTwinSnapshot:
        """Returns the cached snapshot or builds an initial default snapshot."""
        if self.cached_snapshot:
            return self.cached_snapshot
        return self.build_snapshot([])


digital_twin_engine = DigitalTwinEngine()

