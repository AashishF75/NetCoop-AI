"""
Scenario Generator for NetCoop AI.
Generates reproducible network topology and telemetry datasets for the 8 hackathon benchmark scenarios:
1. Normal network
2. Link congestion
3. Weak Wi-Fi signal
4. Interface fault
5. DNS/DHCP failure
6. Missing telemetry
7. Incompatible agent messages
8. Conflicting diagnostic evidence
"""

from typing import Dict, Any, List, Tuple
import json
import csv
import io
from datetime import datetime, timezone

from app.protocol.schema import TelemetryRecord


def get_default_topology() -> Dict[str, Any]:
    """
    Returns standard NOC network topology nodes and edges for React Flow visualization.
    """
    nodes = [
        {
            "id": "Core-Router-01",
            "type": "router",
            "data": {"label": "Core Router 01", "role": "Core Gateway", "ip": "10.0.0.1", "device_type": "router"},
            "position": {"x": 450, "y": 40},
        },
        {
            "id": "Agg-Switch-01",
            "type": "switch",
            "data": {"label": "Aggregation Switch 01", "role": "Distribution Layer", "ip": "10.0.0.2", "device_type": "switch"},
            "position": {"x": 450, "y": 180},
        },
        {
            "id": "Edge-Switch-01",
            "type": "switch",
            "data": {"label": "Edge Switch 01", "role": "Wired Access Layer", "ip": "10.0.1.1", "device_type": "switch"},
            "position": {"x": 220, "y": 320},
        },
        {
            "id": "Edge-Switch-02",
            "type": "switch",
            "data": {"label": "Edge Switch 02", "role": "Wired Access Layer", "ip": "10.0.2.1", "device_type": "switch"},
            "position": {"x": 680, "y": 320},
        },
        {
            "id": "AP-01",
            "type": "ap",
            "data": {"label": "Access Point 01", "role": "Enterprise Wi-Fi", "ip": "10.0.3.10", "device_type": "ap"},
            "position": {"x": 100, "y": 460},
        },
        {
            "id": "AP-02",
            "type": "ap",
            "data": {"label": "Access Point 02", "role": "Enterprise Wi-Fi", "ip": "10.0.3.20", "device_type": "ap"},
            "position": {"x": 340, "y": 460},
        },
        {
            "id": "DNS-Server-01",
            "type": "server",
            "data": {"label": "DNS / DHCP Server", "role": "Core Infrastructure Services", "ip": "10.0.0.53", "device_type": "server"},
            "position": {"x": 580, "y": 460},
        },
        {
            "id": "Database-Server-01",
            "type": "server",
            "data": {"label": "Production DB Server", "role": "Primary Database Host", "ip": "10.0.0.60", "device_type": "server"},
            "position": {"x": 800, "y": 460},
        },
    ]

    edges = [
        {"id": "e-core-agg", "source": "Core-Router-01", "target": "Agg-Switch-01", "label": "Trunk 10G", "animated": True},
        {"id": "e-agg-edge1", "source": "Agg-Switch-01", "target": "Edge-Switch-01", "label": "1G Uplink", "animated": False},
        {"id": "e-agg-edge2", "source": "Agg-Switch-01", "target": "Edge-Switch-02", "label": "1G Uplink", "animated": False},
        {"id": "e-edge1-ap1", "source": "Edge-Switch-01", "target": "AP-01", "label": "PoE+ 1G", "animated": False},
        {"id": "e-edge1-ap2", "source": "Edge-Switch-01", "target": "AP-02", "label": "PoE+ 1G", "animated": False},
        {"id": "e-edge2-dns", "source": "Edge-Switch-02", "target": "DNS-Server-01", "label": "1G SFP", "animated": False},
        {"id": "e-edge2-db", "source": "Edge-Switch-02", "target": "Database-Server-01", "label": "10G SFP+", "animated": False},
    ]

    return {"nodes": nodes, "edges": edges}


class ScenarioCatalog:
    """
    Catalog of all 8 standardized evaluation benchmark scenarios.
    """

    @staticmethod
    def get_scenario_metadata() -> List[Dict[str, Any]]:
        return [
            {
                "id": "normal_network",
                "name": "Scenario 1: Normal Network",
                "category": "Baseline",
                "severity": "NORMAL",
                "description": "All telemetry within operational SLAs. Latencies < 5ms, 0% loss, CPU < 30%.",
                "expected_root_cause": "Normal Network Operation (All Telemetry Within SLA Baselines)",
            },
            {
                "id": "link_congestion",
                "name": "Scenario 2: Egress Link Congestion",
                "category": "Performance",
                "severity": "HIGH",
                "description": "Core-to-Agg trunk overloaded (98% utilization, 84 pkts/s queue drops, 142ms latency).",
                "expected_root_cause": "Egress Link Buffer Congestion",
            },
            {
                "id": "weak_wifi_signal",
                "name": "Scenario 3: Weak Wi-Fi RF Signal",
                "category": "Wireless / RF",
                "severity": "MEDIUM",
                "description": "AP-02 client signal at -86 dBm RSSI, 9 dB SNR, with 42% frame retries.",
                "expected_root_cause": "Wireless RF Path Loss / Edge Signal Attenuation",
            },
            {
                "id": "interface_fault",
                "name": "Scenario 4: Physical Interface & Transceiver Fault",
                "category": "Hardware / Layer 1",
                "severity": "CRITICAL",
                "description": "Edge-Switch-01 interface experiencing 1,450 CRC errors/sec and 6 link flaps.",
                "expected_root_cause": "Physical Link / Transceiver Integrity Fault",
            },
            {
                "id": "dns_dhcp_failure",
                "name": "Scenario 5: Core Services (DNS / DHCP) Failure",
                "category": "Infrastructure Services",
                "severity": "HIGH",
                "description": "DNS resolver latency > 3200ms (timeout) and DHCP address pool 100% exhausted.",
                "expected_root_cause": "Core Network Services Failure (DNS/DHCP)",
            },
            {
                "id": "missing_telemetry",
                "name": "Scenario 6: Missing Telemetry & Insufficient Evidence",
                "category": "Robustness",
                "severity": "WARNING",
                "description": "Critical telemetry dimensions (CPU, queue drops, CRC errors) omitted from records.",
                "expected_root_cause": "Inconclusive Diagnosis due to Missing Telemetry Dimensions",
            },
            {
                "id": "incompatible_agent_messages",
                "name": "Scenario 7: Incompatible Schema & Protocol Validation",
                "category": "Interoperability",
                "severity": "ERROR",
                "description": "Incoming payload with obsolete schema version 0.8.2 and invalid metric unit names.",
                "expected_root_cause": "Protocol Interoperability Rejection (Schema Version Mismatch)",
            },
            {
                "id": "conflicting_evidence",
                "name": "Scenario 8: Conflicting Evidence & Competing Hypotheses",
                "category": "Synthesis & Conflict Resolution",
                "severity": "CRITICAL",
                "description": "Latency spike mimics congestion, but link utilization is 14% and router CPU is 99.4%.",
                "expected_root_cause": "Control Plane Processor Saturation",
            },
        ]

    @classmethod
    def generate_telemetry(cls, scenario_id: str) -> List[TelemetryRecord]:
        now = datetime.now(timezone.utc).isoformat()

        # -------------------------------------------------------------
        # 1. NORMAL NETWORK
        # -------------------------------------------------------------
        if scenario_id == "normal_network":
            return [
                TelemetryRecord(
                    device_id="Core-Router-01",
                    device_type="router",
                    device_status="UP",
                    latency_ms=2.1,
                    jitter_ms=0.4,
                    packet_loss_pct=0.0,
                    throughput_mbps=240.0,
                    bandwidth_mbps=10000.0,
                    utilization_pct=2.4,
                    queue_drops_per_sec=0.0,
                    cpu_utilization_pct=18.5,
                    memory_utilization_pct=34.0,
                    interface_crc_errors=0,
                    interface_flaps=0,
                    dns_response_ms=12.0,
                ),
                TelemetryRecord(
                    device_id="Agg-Switch-01",
                    device_type="switch",
                    device_status="UP",
                    latency_ms=2.8,
                    jitter_ms=0.6,
                    packet_loss_pct=0.0,
                    throughput_mbps=320.0,
                    bandwidth_mbps=10000.0,
                    utilization_pct=3.2,
                    queue_drops_per_sec=0.0,
                    cpu_utilization_pct=22.0,
                    memory_utilization_pct=38.0,
                    interface_crc_errors=0,
                    interface_flaps=0,
                ),
                TelemetryRecord(
                    device_id="Edge-Switch-01",
                    device_type="switch",
                    device_status="UP",
                    latency_ms=3.5,
                    jitter_ms=0.8,
                    packet_loss_pct=0.0,
                    throughput_mbps=85.0,
                    bandwidth_mbps=1000.0,
                    utilization_pct=8.5,
                    queue_drops_per_sec=0.0,
                    cpu_utilization_pct=15.0,
                    memory_utilization_pct=29.0,
                    interface_crc_errors=0,
                    interface_flaps=0,
                ),
                TelemetryRecord(
                    device_id="AP-01",
                    device_type="ap",
                    device_status="UP",
                    latency_ms=6.2,
                    jitter_ms=1.5,
                    packet_loss_pct=0.0,
                    wifi_rssi_dbm=-58.0,
                    wifi_snr_db=32.0,
                    wifi_retry_pct=2.1,
                    cpu_utilization_pct=24.0,
                ),
                TelemetryRecord(
                    device_id="DNS-Server-01",
                    device_type="server",
                    device_status="UP",
                    latency_ms=4.1,
                    jitter_ms=0.5,
                    packet_loss_pct=0.0,
                    dns_response_ms=14.0,
                    dhcp_response_ms=8.0,
                    dhcp_pool_utilization_pct=42.0,
                    cpu_utilization_pct=19.0,
                    memory_utilization_pct=45.0,
                ),
            ]

        # -------------------------------------------------------------
        # 2. LINK CONGESTION
        # -------------------------------------------------------------
        elif scenario_id == "link_congestion":
            return [
                TelemetryRecord(
                    device_id="Core-Router-01",
                    device_type="router",
                    device_status="UP",
                    latency_ms=142.5,
                    jitter_ms=38.2,
                    packet_loss_pct=6.8,
                    throughput_mbps=982.0,
                    bandwidth_mbps=1000.0,
                    utilization_pct=98.2,
                    queue_drops_per_sec=84.5,
                    cpu_utilization_pct=34.0,
                    memory_utilization_pct=42.0,
                    interface_crc_errors=0,
                    interface_flaps=0,
                ),
                TelemetryRecord(
                    device_id="Agg-Switch-01",
                    device_type="switch",
                    device_status="UP",
                    latency_ms=138.0,
                    jitter_ms=35.0,
                    packet_loss_pct=5.9,
                    throughput_mbps=976.0,
                    bandwidth_mbps=1000.0,
                    utilization_pct=97.6,
                    queue_drops_per_sec=79.0,
                    cpu_utilization_pct=31.0,
                    interface_crc_errors=0,
                    interface_flaps=0,
                ),
                TelemetryRecord(
                    device_id="Edge-Switch-01",
                    device_type="switch",
                    device_status="UP",
                    latency_ms=145.0,
                    jitter_ms=39.0,
                    packet_loss_pct=6.5,
                    throughput_mbps=45.0,
                    bandwidth_mbps=1000.0,
                    utilization_pct=4.5,
                    queue_drops_per_sec=0.0,
                    cpu_utilization_pct=16.0,
                    interface_crc_errors=0,
                ),
                TelemetryRecord(
                    device_id="DNS-Server-01",
                    device_type="server",
                    device_status="UP",
                    latency_ms=140.0,
                    dns_response_ms=145.0,
                    dhcp_pool_utilization_pct=43.0,
                    cpu_utilization_pct=20.0,
                ),
            ]

        # -------------------------------------------------------------
        # 3. WEAK WI-FI SIGNAL
        # -------------------------------------------------------------
        elif scenario_id == "weak_wifi_signal":
            return [
                TelemetryRecord(
                    device_id="Core-Router-01",
                    device_type="router",
                    device_status="UP",
                    latency_ms=2.3,
                    packet_loss_pct=0.0,
                    utilization_pct=4.0,
                    queue_drops_per_sec=0.0,
                    cpu_utilization_pct=19.0,
                    interface_crc_errors=0,
                ),
                TelemetryRecord(
                    device_id="Agg-Switch-01",
                    device_type="switch",
                    device_status="UP",
                    latency_ms=2.9,
                    packet_loss_pct=0.0,
                    utilization_pct=5.1,
                    queue_drops_per_sec=0.0,
                    cpu_utilization_pct=21.0,
                    interface_crc_errors=0,
                ),
                TelemetryRecord(
                    device_id="Edge-Switch-01",
                    device_type="switch",
                    device_status="UP",
                    latency_ms=3.4,
                    packet_loss_pct=0.0,
                    utilization_pct=8.0,
                    queue_drops_per_sec=0.0,
                    cpu_utilization_pct=15.0,
                    interface_crc_errors=0,
                ),
                TelemetryRecord(
                    device_id="AP-01",
                    device_type="ap",
                    device_status="UP",
                    latency_ms=6.0,
                    packet_loss_pct=0.0,
                    wifi_rssi_dbm=-61.0,
                    wifi_snr_db=30.0,
                    wifi_retry_pct=3.0,
                ),
                TelemetryRecord(
                    device_id="AP-02",
                    device_type="ap",
                    device_status="DEGRADED",
                    latency_ms=118.0,
                    jitter_ms=45.0,
                    packet_loss_pct=8.4,
                    wifi_rssi_dbm=-86.5,
                    wifi_snr_db=9.2,
                    wifi_retry_pct=42.0,
                    cpu_utilization_pct=28.0,
                    queue_drops_per_sec=0.0,
                    interface_crc_errors=0,
                ),
            ]

        # -------------------------------------------------------------
        # 4. INTERFACE FAULT (Physical Layer 1)
        # -------------------------------------------------------------
        elif scenario_id == "interface_fault":
            return [
                TelemetryRecord(
                    device_id="Core-Router-01",
                    device_type="router",
                    device_status="UP",
                    latency_ms=3.1,
                    packet_loss_pct=0.0,
                    utilization_pct=12.0,
                    queue_drops_per_sec=0.0,
                    cpu_utilization_pct=22.0,
                    interface_crc_errors=0,
                ),
                TelemetryRecord(
                    device_id="Agg-Switch-01",
                    device_type="switch",
                    device_status="UP",
                    latency_ms=4.0,
                    packet_loss_pct=0.0,
                    utilization_pct=14.0,
                    queue_drops_per_sec=0.0,
                    cpu_utilization_pct=25.0,
                    interface_crc_errors=0,
                ),
                TelemetryRecord(
                    device_id="Edge-Switch-01",
                    device_type="switch",
                    device_status="FLAPPING",
                    latency_ms=88.0,
                    jitter_ms=22.0,
                    packet_loss_pct=14.5,
                    throughput_mbps=180.0,
                    bandwidth_mbps=1000.0,
                    utilization_pct=18.0,
                    queue_drops_per_sec=0.0,  # Zero queue drops proves non-congestion!
                    cpu_utilization_pct=24.0,
                    interface_crc_errors=1450,  # High CRC errors!
                    interface_flaps=6,          # Flapping link
                ),
            ]

        # -------------------------------------------------------------
        # 5. DNS / DHCP FAILURE
        # -------------------------------------------------------------
        elif scenario_id == "dns_dhcp_failure":
            return [
                TelemetryRecord(
                    device_id="Core-Router-01",
                    device_type="router",
                    device_status="UP",
                    latency_ms=2.5,
                    packet_loss_pct=0.0,
                    utilization_pct=5.0,
                    queue_drops_per_sec=0.0,
                    cpu_utilization_pct=18.0,
                    interface_crc_errors=0,
                ),
                TelemetryRecord(
                    device_id="Agg-Switch-01",
                    device_type="switch",
                    device_status="UP",
                    latency_ms=3.0,
                    packet_loss_pct=0.0,
                    utilization_pct=6.0,
                    queue_drops_per_sec=0.0,
                    cpu_utilization_pct=20.0,
                    interface_crc_errors=0,
                ),
                TelemetryRecord(
                    device_id="DNS-Server-01",
                    device_type="server",
                    device_status="DEGRADED",
                    latency_ms=4.0,  # Ping to server is fast!
                    packet_loss_pct=0.0,
                    dns_response_ms=3250.0,  # DNS query timed out!
                    dhcp_response_ms=2800.0,
                    dhcp_pool_utilization_pct=100.0, # Exhausted!
                    cpu_utilization_pct=88.0,
                    memory_utilization_pct=92.0,
                ),
            ]

        # -------------------------------------------------------------
        # 6. MISSING TELEMETRY (Insufficient Evidence)
        # -------------------------------------------------------------
        elif scenario_id == "missing_telemetry":
            return [
                TelemetryRecord(
                    device_id="Core-Router-01",
                    device_type="router",
                    device_status="UP",
                    latency_ms=18.0,
                    packet_loss_pct=3.5,
                    # Missing CPU, queue drops, and CRC errors!
                    cpu_utilization_pct=None,
                    queue_drops_per_sec=None,
                    interface_crc_errors=None,
                    utilization_pct=None,
                ),
                TelemetryRecord(
                    device_id="Agg-Switch-01",
                    device_type="switch",
                    device_status="UP",
                    latency_ms=22.0,
                    packet_loss_pct=4.1,
                    cpu_utilization_pct=None,
                    queue_drops_per_sec=None,
                    interface_crc_errors=None,
                    utilization_pct=None,
                ),
            ]

        # -------------------------------------------------------------
        # 7. INCOMPATIBLE AGENT MESSAGES (Schema mismatch & malformed payload)
        # -------------------------------------------------------------
        elif scenario_id == "incompatible_agent_messages":
            # Valid telemetry records for context, but triggers protocol mismatch when evaluated
            return [
                TelemetryRecord(
                    device_id="Core-Router-01",
                    device_type="router",
                    device_status="UP",
                    latency_ms=15.0,
                    packet_loss_pct=1.0,
                    cpu_utilization_pct=30.0,
                ),
            ]

        # -------------------------------------------------------------
        # 8. CONFLICTING EVIDENCE (Latency vs CPU vs Link Utilization)
        # -------------------------------------------------------------
        elif scenario_id == "conflicting_evidence":
            return [
                TelemetryRecord(
                    device_id="Core-Router-01",
                    device_type="router",
                    device_status="DEGRADED",
                    latency_ms=115.0,          # Latency is high, mimicking congestion
                    packet_loss_pct=4.2,       # Loss is high
                    throughput_mbps=42.0,      # Low throughput
                    bandwidth_mbps=1000.0,
                    utilization_pct=14.0,      # BUT utilization is very low!
                    queue_drops_per_sec=0.0,   # ZERO queue drops!
                    cpu_utilization_pct=99.4,  # BUT CPU is 99.4% (Crypto storm / route churn!)
                    memory_utilization_pct=88.0,
                    interface_crc_errors=0,    # Zero CRC errors (rules out physical cable!)
                    interface_flaps=0,
                ),
                TelemetryRecord(
                    device_id="Agg-Switch-01",
                    device_type="switch",
                    device_status="UP",
                    latency_ms=8.0,
                    packet_loss_pct=0.0,
                    utilization_pct=12.0,
                    queue_drops_per_sec=0.0,
                    cpu_utilization_pct=21.0,
                    interface_crc_errors=0,
                ),
            ]

        # Default fallback
        return cls.generate_telemetry("normal_network")

    @classmethod
    def export_csv(cls, scenario_id: str) -> str:
        """Exports scenario records to standard CSV format."""
        records = cls.generate_telemetry(scenario_id)
        output = io.StringIO()
        fieldnames = [
            "device_id", "device_type", "device_status",
            "latency_ms", "jitter_ms", "packet_loss_pct",
            "throughput_mbps", "bandwidth_mbps", "utilization_pct",
            "queue_drops_per_sec", "cpu_utilization_pct", "memory_utilization_pct",
            "interface_crc_errors", "interface_flaps",
            "wifi_rssi_dbm", "wifi_snr_db", "wifi_retry_pct",
            "dns_response_ms", "dhcp_pool_utilization_pct"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            d = r.model_dump()
            row = {k: ("" if d.get(k) is None else d.get(k)) for k in fieldnames}
            writer.writerow(row)
        return output.getvalue()

    @classmethod
    def export_json(cls, scenario_id: str) -> str:
        """Exports scenario records to standard JSON format."""
        records = cls.generate_telemetry(scenario_id)
        return json.dumps([r.model_dump() for r in records], indent=2)
