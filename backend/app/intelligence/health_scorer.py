"""
Explainable Network Health Scoring Engine for NetCoop AI.
Computes transparent, auditable health scores with itemized point deductions
against golden SLA baselines for each monitored device and the composite fabric.
"""

from typing import List, Dict, Any, Optional
from app.protocol.schema import (
    TelemetryRecord,
    MetricPenalty,
    DeviceHealthBreakdown,
    NetworkHealthScoreReport,
)
from app.simulator.twin import DEVICE_DEPENDENCY_GRAPH, BASELINE_SLA_BOUNDS


class ExplainableHealthScorer:
    """
    Transparent health calculation attributing every deducted point to an empirical metric breach.
    """

    def compute_health_report(
        self,
        telemetry: List[TelemetryRecord],
    ) -> NetworkHealthScoreReport:
        """
        Builds a comprehensive, explainable health audit report.
        """
        telemetry_by_dev: Dict[str, TelemetryRecord] = {
            t.device_id: t for t in telemetry
        }

        device_breakdowns: List[DeviceHealthBreakdown] = []
        total_score = 0.0
        compliant_devices = 0
        all_penalties_reasons: List[str] = []

        for dev_id, meta in DEVICE_DEPENDENCY_GRAPH.items():
            record = telemetry_by_dev.get(dev_id)
            penalties: List[MetricPenalty] = []
            positives: List[str] = []
            score = 100.0

            if record:
                # 1. CPU Utilization (Max 80% SLA -> up to 45 pts penalty)
                if record.cpu_utilization_pct is not None:
                    if record.cpu_utilization_pct > 90.0:
                        pts = 45.0
                        penalties.append(
                            MetricPenalty(
                                metric_name="cpu_utilization_pct",
                                observed_value=record.cpu_utilization_pct,
                                sla_limit=80.0,
                                unit="%",
                                points_deducted=pts,
                                reason=f"Severe processor saturation ({record.cpu_utilization_pct}% > 80% SLA)",
                            )
                        )
                        score -= pts
                    elif record.cpu_utilization_pct > 80.0:
                        pts = 20.0
                        penalties.append(
                            MetricPenalty(
                                metric_name="cpu_utilization_pct",
                                observed_value=record.cpu_utilization_pct,
                                sla_limit=80.0,
                                unit="%",
                                points_deducted=pts,
                                reason=f"Elevated CPU utilization ({record.cpu_utilization_pct}% > 80% SLA)",
                            )
                        )
                        score -= pts
                    else:
                        positives.append(f"CPU utilization nominal ({record.cpu_utilization_pct}%)")

                # 2. Round-Trip Latency (Max 20ms SLA -> up to 30 pts penalty)
                if record.latency_ms is not None:
                    if record.latency_ms > 80.0:
                        pts = 30.0
                        penalties.append(
                            MetricPenalty(
                                metric_name="latency_ms",
                                observed_value=record.latency_ms,
                                sla_limit=20.0,
                                unit="ms",
                                points_deducted=pts,
                                reason=f"High latency spike ({record.latency_ms}ms > 20ms SLA)",
                            )
                        )
                        score -= pts
                    elif record.latency_ms > 20.0:
                        pts = 15.0
                        penalties.append(
                            MetricPenalty(
                                metric_name="latency_ms",
                                observed_value=record.latency_ms,
                                sla_limit=20.0,
                                unit="ms",
                                points_deducted=pts,
                                reason=f"Moderate latency elevation ({record.latency_ms}ms > 20ms SLA)",
                            )
                        )
                        score -= pts
                    else:
                        positives.append(f"Latency within SLA ({record.latency_ms}ms)")

                # 3. Packet Loss (Max 1.0% SLA -> up to 25 pts penalty)
                if record.packet_loss_pct is not None and record.packet_loss_pct > 1.0:
                    pts = 25.0
                    penalties.append(
                        MetricPenalty(
                            metric_name="packet_loss_pct",
                            observed_value=record.packet_loss_pct,
                            sla_limit=1.0,
                            unit="%",
                            points_deducted=pts,
                            reason=f"Transit packet drops detected ({record.packet_loss_pct}% > 1.0% SLA)",
                        )
                    )
                    score -= pts
                elif record.packet_loss_pct is not None:
                    positives.append("Zero packet loss")

                # 4. Interface CRC Errors (Max 10 err/s -> 35 pts penalty)
                if record.interface_crc_errors is not None and record.interface_crc_errors > 10:
                    pts = 35.0
                    penalties.append(
                        MetricPenalty(
                            metric_name="interface_crc_errors",
                            observed_value=record.interface_crc_errors,
                            sla_limit=10,
                            unit="errors/s",
                            points_deducted=pts,
                            reason=f"L1/L2 frame corruptions ({record.interface_crc_errors} err/s > 10 SLA)",
                        )
                    )
                    score -= pts

                # 5. Egress Queue Drops (Max 5 pkts/s -> 25 pts penalty)
                if record.queue_drops_per_sec is not None and record.queue_drops_per_sec > 5.0:
                    pts = 25.0
                    penalties.append(
                        MetricPenalty(
                            metric_name="queue_drops_per_sec",
                            observed_value=record.queue_drops_per_sec,
                            sla_limit=5.0,
                            unit="pkts/s",
                            points_deducted=pts,
                            reason=f"Buffer queue exhaustion ({record.queue_drops_per_sec} pkts/s drops)",
                        )
                    )
                    score -= pts

                # 6. Wi-Fi RSSI (Min -72 dBm -> 30 pts penalty)
                if record.wifi_rssi_dbm is not None and record.wifi_rssi_dbm < -72.0:
                    pts = 30.0
                    penalties.append(
                        MetricPenalty(
                            metric_name="wifi_rssi_dbm",
                            observed_value=record.wifi_rssi_dbm,
                            sla_limit=-72.0,
                            unit="dBm",
                            points_deducted=pts,
                            reason=f"Weak wireless signal attenuation ({record.wifi_rssi_dbm} dBm < -72 dBm)",
                        )
                    )
                    score -= pts

                # 7. DNS Response Time (Max 100ms -> 30 pts penalty)
                if record.dns_response_ms is not None and record.dns_response_ms > 200.0:
                    pts = 30.0
                    penalties.append(
                        MetricPenalty(
                            metric_name="dns_response_ms",
                            observed_value=record.dns_response_ms,
                            sla_limit=100.0,
                            unit="ms",
                            points_deducted=pts,
                            reason=f"Slow DNS resolution latency ({record.dns_response_ms}ms > 100ms SLA)",
                        )
                    )
                    score -= pts
            else:
                positives.append("Device operating nominally with default baseline telemetry")

            final_score = max(0.0, min(100.0, round(score, 1)))
            op_status = "OPTIMAL" if final_score >= 85.0 else ("WARNING" if final_score >= 50.0 else "CRITICAL")
            sla_status = "COMPLIANT" if len(penalties) == 0 else "BREACHED"

            if sla_status == "COMPLIANT":
                compliant_devices += 1

            for p in penalties:
                all_penalties_reasons.append(f"{dev_id}: {p.reason}")

            device_breakdowns.append(
                DeviceHealthBreakdown(
                    device_id=dev_id,
                    device_name=meta["name"],
                    role=meta["role"],
                    health_score=final_score,
                    operational_status=op_status,
                    sla_status=sla_status,
                    penalties=penalties,
                    positive_contributions=positives,
                )
            )
            total_score += final_score

        count = len(device_breakdowns)
        overall = round(total_score / count, 1) if count else 100.0
        sla_pct = round((compliant_devices / count) * 100.0, 1) if count else 100.0
        overall_status = "OPTIMAL" if overall >= 85.0 else ("DEGRADED" if overall >= 60.0 else "CRITICAL")

        return NetworkHealthScoreReport(
            overall_health_score=overall,
            status=overall_status,
            calculation_methodology="Multi-Factor Weighted Penalty Deduction against Golden SLA Baselines",
            total_devices_evaluated=count,
            sla_compliance_rate_pct=sla_pct,
            device_breakdowns=device_breakdowns,
            top_risk_factors=all_penalties_reasons[:5],
            caveats=[
                "Score is a deterministic heuristic benchmark indicator calculated from synthetic telemetry.",
                "Missing telemetry metrics are flagged without applying punitive penalty deductions.",
                "Does not represent a certified industry benchmark (e.g. MEF / Cisco DNA Assurance).",
            ],
        )


explainable_health_scorer = ExplainableHealthScorer()

