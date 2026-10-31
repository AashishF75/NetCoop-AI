"""
Proactive Fault Prediction and Telemetry Trend Analysis Engine for NetCoop AI.
Analyzes multi-point telemetry time-series to detect metric drift, calculate time-to-breach,
and generate preventive warnings prior to catastrophic SLA breaches.
"""

from typing import List, Dict, Any, Optional, Tuple
import uuid
from datetime import datetime, timezone

from app.protocol.schema import (
    TelemetryRecord,
    ProactiveRiskWarning,
    RiskSeverity,
)
from app.simulator.twin import BASELINE_SLA_BOUNDS


class ProactivePredictor:
    """
    Evaluates telemetry time-series or multi-interval samples to identify creeping degradation.
    """

    def analyze_trends(
        self,
        telemetry_history: List[List[TelemetryRecord]],
        current_telemetry: Optional[List[TelemetryRecord]] = None,
    ) -> List[ProactiveRiskWarning]:
        """
        Analyzes historical telemetry snapshots (ordered oldest to newest).
        If history has fewer than 2 snapshots and no drift is observable, reports insufficient data.
        """
        warnings: List[ProactiveRiskWarning] = []

        if not telemetry_history or len(telemetry_history) < 2:
            # Check if current telemetry has borderline/creeping values that warrant watch
            if current_telemetry:
                return self._evaluate_near_threshold_risks(current_telemetry)
            return []

        # Map history by device_id -> metric -> list of values
        device_series: Dict[str, Dict[str, List[float]]] = {}
        for snapshot in telemetry_history:
            for record in snapshot:
                dev = record.device_id
                if dev not in device_series:
                    device_series[dev] = {
                        "cpu_utilization_pct": [],
                        "latency_ms": [],
                        "packet_loss_pct": [],
                        "utilization_pct": [],
                        "queue_drops_per_sec": [],
                        "interface_crc_errors": [],
                        "wifi_rssi_dbm": [],
                    }
                if record.cpu_utilization_pct is not None:
                    device_series[dev]["cpu_utilization_pct"].append(float(record.cpu_utilization_pct))
                if record.latency_ms is not None:
                    device_series[dev]["latency_ms"].append(float(record.latency_ms))
                if record.packet_loss_pct is not None:
                    device_series[dev]["packet_loss_pct"].append(float(record.packet_loss_pct))
                if record.utilization_pct is not None:
                    device_series[dev]["utilization_pct"].append(float(record.utilization_pct))
                if record.queue_drops_per_sec is not None:
                    device_series[dev]["queue_drops_per_sec"].append(float(record.queue_drops_per_sec))
                if record.interface_crc_errors is not None:
                    device_series[dev]["interface_crc_errors"].append(float(record.interface_crc_errors))
                if record.wifi_rssi_dbm is not None:
                    device_series[dev]["wifi_rssi_dbm"].append(float(record.wifi_rssi_dbm))

        # Evaluate slopes and projected values
        for dev, metrics in device_series.items():
            # CPU Trend Check (SLA: 80%)
            cpu_vals = metrics["cpu_utilization_pct"]
            if len(cpu_vals) >= 2:
                rate = round((cpu_vals[-1] - cpu_vals[0]) / max(1, len(cpu_vals) - 1), 2)
                curr = cpu_vals[-1]
                if rate > 2.5 and curr < 90.0:  # Creeping CPU
                    proj = round(min(100.0, curr + (rate * 10)), 1)
                    time_to_breach = round(max(1.0, (80.0 - curr) / rate), 1) if curr < 80.0 else 0.5
                    warnings.append(
                        ProactiveRiskWarning(
                            warning_id=f"WARN-CPU-{uuid.uuid4().hex[:6].upper()}",
                            device_id=dev,
                            metric="cpu_utilization_pct",
                            current_value=curr,
                            projected_value_10m=proj,
                            threshold_limit=80.0,
                            unit="%",
                            drift_rate_per_min=rate,
                            severity=RiskSeverity.HIGH if proj >= 90.0 else RiskSeverity.MEDIUM,
                            time_to_breach_minutes=time_to_breach,
                            title=f"Creeping CPU Saturation on {dev} (+{rate}%/interval)",
                            expected_impact=f"If trend persists, host CPU will saturate within ~{time_to_breach} mins, triggering control-plane drops.",
                            preventive_remediation="Isolate noisy telemetry polling daemons and enforce CoPP punt rate limiting.",
                            confidence=0.88,
                            evidence={"historical_samples": cpu_vals, "drift_slope": rate},
                        )
                    )

            # Latency Trend Check (SLA: 20ms)
            lat_vals = metrics["latency_ms"]
            if len(lat_vals) >= 2:
                rate = round((lat_vals[-1] - lat_vals[0]) / max(1, len(lat_vals) - 1), 2)
                curr = lat_vals[-1]
                if rate > 3.0 and curr < 80.0:
                    proj = round(curr + (rate * 10), 1)
                    time_to_breach = round(max(1.0, (20.0 - curr) / rate), 1) if curr < 20.0 else 0.5
                    warnings.append(
                        ProactiveRiskWarning(
                            warning_id=f"WARN-LAT-{uuid.uuid4().hex[:6].upper()}",
                            device_id=dev,
                            metric="latency_ms",
                            current_value=curr,
                            projected_value_10m=proj,
                            threshold_limit=20.0,
                            unit="ms",
                            drift_rate_per_min=rate,
                            severity=RiskSeverity.HIGH if proj >= 80.0 else RiskSeverity.MEDIUM,
                            time_to_breach_minutes=time_to_breach,
                            title=f"Upward Latency Drift on {dev} (+{rate}ms/interval)",
                            expected_impact=f"Round-trip latency projected to reach {proj}ms in 10 mins, risking voice/video SLA breach.",
                            preventive_remediation="Apply WRED buffer congestion avoidance and inspect trunk link queue depths.",
                            confidence=0.85,
                            evidence={"historical_samples": lat_vals, "drift_slope": rate},
                        )
                    )

            # Link Utilization Trend Check (SLA: 85%)
            util_vals = metrics["utilization_pct"]
            if len(util_vals) >= 2:
                rate = round((util_vals[-1] - util_vals[0]) / max(1, len(util_vals) - 1), 2)
                curr = util_vals[-1]
                if rate > 4.0 and curr < 90.0:
                    proj = round(min(100.0, curr + (rate * 10)), 1)
                    time_to_breach = round(max(1.0, (85.0 - curr) / rate), 1) if curr < 85.0 else 0.5
                    warnings.append(
                        ProactiveRiskWarning(
                            warning_id=f"WARN-UTIL-{uuid.uuid4().hex[:6].upper()}",
                            device_id=dev,
                            metric="utilization_pct",
                            current_value=curr,
                            projected_value_10m=proj,
                            threshold_limit=85.0,
                            unit="%",
                            drift_rate_per_min=rate,
                            severity=RiskSeverity.HIGH if proj >= 95.0 else RiskSeverity.MEDIUM,
                            time_to_breach_minutes=time_to_breach,
                            title=f"Bandwidth Growth Pressure on {dev} (+{rate}%/interval)",
                            expected_impact=f"Trunk link will reach 100% capacity within ~{time_to_breach} mins, inducing tail drops.",
                            preventive_remediation="Activate secondary ECMP deflection route to relieve primary trunk.",
                            confidence=0.90,
                            evidence={"historical_samples": util_vals, "drift_slope": rate},
                        )
                    )

            # Interface CRC Error Accumulation Check
            crc_vals = metrics["interface_crc_errors"]
            if len(crc_vals) >= 2:
                rate = round((crc_vals[-1] - crc_vals[0]) / max(1, len(crc_vals) - 1), 2)
                curr = crc_vals[-1]
                if rate > 5.0:
                    proj = round(curr + (rate * 10), 1)
                    warnings.append(
                        ProactiveRiskWarning(
                            warning_id=f"WARN-CRC-{uuid.uuid4().hex[:6].upper()}",
                            device_id=dev,
                            metric="interface_crc_errors",
                            current_value=curr,
                            projected_value_10m=proj,
                            threshold_limit=10.0,
                            unit="errors/s",
                            drift_rate_per_min=rate,
                            severity=RiskSeverity.HIGH if proj > 100 else RiskSeverity.MEDIUM,
                            time_to_breach_minutes=1.5,
                            title=f"Accelerating CRC Discards on {dev} (+{rate} err/interval)",
                            expected_impact="Optical signal degradation or dirty fiber patch causing frame corruptions.",
                            preventive_remediation="Check optical DDM Rx power levels and prepare LACP member link eviction.",
                            confidence=0.92,
                            evidence={"historical_samples": crc_vals, "drift_slope": rate},
                        )
                    )

        return warnings

    def _evaluate_near_threshold_risks(self, records: List[TelemetryRecord]) -> List[ProactiveRiskWarning]:
        """
        In single-sample telemetry, identifies devices operating at near-threshold borderline limits.
        """
        warnings: List[ProactiveRiskWarning] = []
        for r in records:
            # CPU > 65% but < 85% (Approaching threshold)
            if r.cpu_utilization_pct is not None and 65.0 <= r.cpu_utilization_pct <= 85.0:
                warnings.append(
                    ProactiveRiskWarning(
                        warning_id=f"WARN-CPU-{uuid.uuid4().hex[:6].upper()}",
                        device_id=r.device_id,
                        metric="cpu_utilization_pct",
                        current_value=r.cpu_utilization_pct,
                        projected_value_10m=round(min(100.0, r.cpu_utilization_pct + 12.0), 1),
                        threshold_limit=80.0,
                        unit="%",
                        drift_rate_per_min=1.2,
                        severity=RiskSeverity.MEDIUM,
                        time_to_breach_minutes=round(max(1.0, (80.0 - r.cpu_utilization_pct) / 1.2), 1) if r.cpu_utilization_pct < 80.0 else 0.5,
                        title=f"Creeping Processor Load on {r.device_id}",
                        expected_impact="CPU growth will trigger control-plane throttling and packet queue starvation.",
                        preventive_remediation="Activate Control-Plane Policing (CoPP) and enable BGP routing thread affinity.",
                        confidence=0.82,
                        evidence={"current_value": r.cpu_utilization_pct},
                    )
                )

            # Interface CRC Errors > 100 (Physical link degradation risk)
            if r.interface_crc_errors is not None and r.interface_crc_errors > 100:
                warnings.append(
                    ProactiveRiskWarning(
                        warning_id=f"WARN-CRC-{uuid.uuid4().hex[:6].upper()}",
                        device_id=r.device_id,
                        metric="interface_crc_errors",
                        current_value=float(r.interface_crc_errors),
                        projected_value_10m=round(float(r.interface_crc_errors) * 1.5, 0),
                        threshold_limit=50.0,
                        unit="errors/sec",
                        drift_rate_per_min=15.0,
                        severity=RiskSeverity.HIGH,
                        time_to_breach_minutes=0.0,
                        title=f"Active Transceiver Frame Corruptions on {r.device_id}",
                        expected_impact="Physical frame discards will force end-to-end TCP retransmissions across all downstream leaves.",
                        preventive_remediation="Inspect SFP+ optical power levels via DDM and schedule non-disruptive transceiver swap.",
                        confidence=0.91,
                        evidence={"interface_crc_errors": r.interface_crc_errors},
                    )
                )

            # Latency between 35ms and 80ms
            if r.latency_ms is not None and 35.0 <= r.latency_ms <= 80.0:
                warnings.append(
                    ProactiveRiskWarning(
                        warning_id=f"WARN-LAT-{uuid.uuid4().hex[:6].upper()}",
                        device_id=r.device_id,
                        metric="latency_ms",
                        current_value=r.latency_ms,
                        projected_value_10m=round(r.latency_ms + 18.0, 1),
                        threshold_limit=50.0,
                        unit="ms",
                        drift_rate_per_min=1.8,
                        severity=RiskSeverity.MEDIUM,
                        time_to_breach_minutes=round(max(1.0, (50.0 - r.latency_ms) / 1.8), 1) if r.latency_ms < 50.0 else 0.5,
                        title=f"Sub-Critical Latency Elevation on {r.device_id}",
                        expected_impact="Elevated queuing delay threatens real-time VoIP and interactive session SLA compliance.",
                        preventive_remediation="Shift bulk replication flows to alternate backup path and enable Fair Queueing.",
                        confidence=0.84,
                        evidence={"latency_ms": r.latency_ms},
                    )
                )

            # Memory > 75% but < 85%
            if r.memory_utilization_pct is not None and 75.0 <= r.memory_utilization_pct < 85.0:
                warnings.append(
                    ProactiveRiskWarning(
                        warning_id=f"WARN-MEM-{uuid.uuid4().hex[:6].upper()}",
                        device_id=r.device_id,
                        metric="memory_utilization_pct",
                        current_value=r.memory_utilization_pct,
                        projected_value_10m=round(r.memory_utilization_pct + 4.5, 1),
                        threshold_limit=85.0,
                        unit="%",
                        drift_rate_per_min=0.45,
                        severity=RiskSeverity.LOW,
                        time_to_breach_minutes=22.0,
                        title=f"Elevated Memory Allocation on {r.device_id}",
                        expected_impact="Gradual memory growth may trigger OS kernel OOM-killer if buffer pools exhaust.",
                        preventive_remediation="Inspect dynamic routing table memory consumption and flush idle sessions.",
                        confidence=0.72,
                        evidence={"current_value": r.memory_utilization_pct},
                    )
                )

            # Wi-Fi RSSI between -70 dBm and -75 dBm
            if r.wifi_rssi_dbm is not None and -75.0 <= r.wifi_rssi_dbm <= -70.0:
                warnings.append(
                    ProactiveRiskWarning(
                        warning_id=f"WARN-RF-{uuid.uuid4().hex[:6].upper()}",
                        device_id=r.device_id,
                        metric="wifi_rssi_dbm",
                        current_value=r.wifi_rssi_dbm,
                        projected_value_10m=round(r.wifi_rssi_dbm - 3.0, 1),
                        threshold_limit=-75.0,
                        unit="dBm",
                        drift_rate_per_min=-0.3,
                        severity=RiskSeverity.LOW,
                        time_to_breach_minutes=15.0,
                        title=f"Marginal Wireless Signal Margin on {r.device_id}",
                        expected_impact="Client roaming sticky edge will begin dropping MCS negotiation rates.",
                        preventive_remediation="Trigger 802.11v BSS Transition to steer edge clients to nearest AP.",
                        confidence=0.75,
                        evidence={"current_value": r.wifi_rssi_dbm},
                    )
                )

        return warnings


proactive_predictor = ProactivePredictor()
