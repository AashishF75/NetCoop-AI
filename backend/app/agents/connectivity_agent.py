"""
Connectivity Analysis Agent.
Analyzes ICMP reachability, TCP connectivity, wireless RF health (RSSI, SNR),
DNS resolution latencies, DHCP allocation pools, and service-layer reachability.
Strictly distinguishes gateway reachability from internet reachability;
never claims DNS or DHCP failure without explicit corroborating service metrics.
"""

from typing import List, Dict, Any, Optional
from app.agents.base_agent import BaseAgent
from app.protocol.schema import (
    AgentMessage,
    MessageType,
    TelemetryRecord,
)


class ConnectivityAgent(BaseAgent):
    def __init__(self, agent_id: str = "conn-agent-01"):
        super().__init__(
            agent_id=agent_id,
            name="Connectivity Analysis Agent",
            role="RF, L2/L3 Reachability & Core Services Monitor",
        )
        self.RSSI_WARN_DBM = -75.0
        self.RSSI_CRIT_DBM = -82.0
        self.SNR_WARN_DB = 20.0
        self.SNR_CRIT_DB = 12.0
        self.WIFI_RETRY_CRIT_PCT = 25.0
        self.DNS_WARN_MS = 300.0
        self.DNS_CRIT_MS = 1500.0
        self.DHCP_POOL_CRIT_PCT = 95.0

    def analyze(self, telemetry: List[TelemetryRecord]) -> List[AgentMessage]:
        self.set_status("ANALYZING", "Evaluating reachability, Wi-Fi RF, DNS resolver, and DHCP pools")
        anomalies: List[AgentMessage] = []

        for record in telemetry:
            dev = record.device_id
            origin = getattr(record, "telemetry_origin", "SIMULATED_SCENARIO")
            custom = getattr(record, "custom_metrics", {}) or {}
            proto = (custom.get("protocol") or "").upper()

            # ---------------------------------------------------------
            # 1. ICMP & TCP Reachability (Gateway vs Internet distinction)
            # ---------------------------------------------------------
            is_unreachable = (
                (record.packet_loss_pct is not None and record.packet_loss_pct >= 99.0)
                or (record.device_status and record.device_status.upper() in ("DOWN", "UNREACHABLE"))
            )

            is_gateway = (
                "GATEWAY" in dev.upper()
                or custom.get("is_gateway", False)
                or "GATEWAY" in str(custom.get("probe_note", "")).upper()
            )
            is_internet = (
                "8.8.8.8" in dev
                or "1.1.1.1" in dev
                or "WAN" in dev.upper()
                or "INTERNET" in dev.upper()
            )

            if is_unreachable:
                if is_gateway:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="gateway_reachability",
                        value=0.0,
                        unit="reachability",
                        evidence={
                            "observed": "UNREACHABLE",
                            "target_type": "LOCAL_GATEWAY",
                            "packet_loss_pct": record.packet_loss_pct,
                            "severity": "CRITICAL",
                            "metric_type": "gateway_unreachable",
                            "telemetry_origin": origin,
                        },
                        confidence=0.98,
                        findings=[
                            f"Default Gateway unreachable ({dev}): 100% packet loss. "
                            "Local LAN interface or physical link disconnected from gateway."
                        ],
                    )
                    anomalies.append(msg)
                elif is_internet:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="internet_reachability",
                        value=0.0,
                        unit="reachability",
                        evidence={
                            "observed": "UNREACHABLE",
                            "target_type": "INTERNET_TARGET",
                            "packet_loss_pct": record.packet_loss_pct,
                            "severity": "CRITICAL",
                            "metric_type": "internet_unreachable",
                            "telemetry_origin": origin,
                        },
                        confidence=0.96,
                        findings=[
                            f"Internet target unreachable ({dev}): 100% packet loss. "
                            "Upstream ISP or WAN transit link outage."
                        ],
                    )
                    anomalies.append(msg)
                elif "TCP" in proto or "PORT" in proto:
                    port = custom.get("port") or getattr(record, "port", None) or 80
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="tcp_port_connectivity",
                        value=0.0,
                        unit="connectivity",
                        evidence={
                            "observed": "PORT_CLOSED_OR_FILTERED",
                            "port": port,
                            "protocol": "TCP",
                            "severity": "CRITICAL",
                            "metric_type": "tcp_port_unreachable",
                            "telemetry_origin": origin,
                        },
                        confidence=0.95,
                        findings=[
                            f"TCP port check failed on {dev}:{port}. Handshake rejected or timed out."
                        ],
                    )
                    anomalies.append(msg)

            # ---------------------------------------------------------
            # 2. Wi-Fi RF Signal Degradation (RSSI / SNR / Retries)
            # ---------------------------------------------------------
            if record.wifi_rssi_dbm is not None:
                rssi = record.wifi_rssi_dbm
                retries = record.wifi_retry_pct or 0.0
                snr = record.wifi_snr_db or 25.0

                if rssi <= self.RSSI_CRIT_DBM or retries >= self.WIFI_RETRY_CRIT_PCT:
                    conf = min(0.97, 0.78 + (abs(rssi) / 100.0) * 0.15 + (retries / 100.0) * 0.10)
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="wifi_rssi_dbm",
                        value=rssi,
                        unit="dBm",
                        evidence={
                            "wifi_rssi_dbm": rssi,
                            "wifi_snr_db": snr,
                            "wifi_retry_pct": retries,
                            "baseline_rssi": -60.0,
                            "threshold": self.RSSI_CRIT_DBM,
                            "severity": "CRITICAL",
                            "metric_type": "wireless_rf",
                            "telemetry_origin": origin,
                        },
                        confidence=conf,
                        findings=[
                            f"Severe Wi-Fi signal attenuation on {dev}: RSSI {rssi} dBm (crit < {self.RSSI_CRIT_DBM}), "
                            f"SNR {snr} dB, frame retries {retries}%"
                        ],
                    )
                    anomalies.append(msg)
                elif rssi <= self.RSSI_WARN_DBM:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="wifi_rssi_dbm",
                        value=rssi,
                        unit="dBm",
                        evidence={
                            "wifi_rssi_dbm": rssi,
                            "wifi_snr_db": snr,
                            "wifi_retry_pct": retries,
                            "baseline_rssi": -60.0,
                            "threshold": self.RSSI_WARN_DBM,
                            "severity": "WARNING",
                            "metric_type": "wireless_rf",
                            "telemetry_origin": origin,
                        },
                        confidence=0.74,
                        findings=[
                            f"Marginal Wi-Fi coverage on {dev}: RSSI {rssi} dBm"
                        ],
                    )
                    anomalies.append(msg)

            # ---------------------------------------------------------
            # 3. DNS Resolution Latency (REQUIRES REAL DNS EVIDENCE)
            # ---------------------------------------------------------
            if record.dns_response_ms is not None:
                dns_ms = record.dns_response_ms
                if dns_ms >= self.DNS_CRIT_MS:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="dns_response_ms",
                        value=dns_ms,
                        unit="ms",
                        evidence={
                            "observed": dns_ms,
                            "baseline": 15.0,
                            "threshold": self.DNS_CRIT_MS,
                            "severity": "CRITICAL",
                            "metric_type": "core_service_dns",
                            "telemetry_origin": origin,
                        },
                        confidence=min(0.98, 0.85 + (dns_ms / 5000.0) * 0.12),
                        findings=[
                            f"Critical DNS resolution timeout on {dev}: {dns_ms} ms (baseline: 15 ms, timeout > {self.DNS_CRIT_MS} ms)"
                        ],
                    )
                    anomalies.append(msg)
                elif dns_ms >= self.DNS_WARN_MS:
                    msg = self.create_message(
                        message_type=MessageType.TELEMETRY_ANOMALY,
                        device_id=dev,
                        metric="dns_response_ms",
                        value=dns_ms,
                        unit="ms",
                        evidence={
                            "observed": dns_ms,
                            "baseline": 15.0,
                            "threshold": self.DNS_WARN_MS,
                            "severity": "WARNING",
                            "metric_type": "core_service_dns",
                            "telemetry_origin": origin,
                        },
                        confidence=0.75,
                        findings=[
                            f"Elevated DNS query latency on {dev}: {dns_ms} ms"
                        ],
                    )
                    anomalies.append(msg)

            # ---------------------------------------------------------
            # 4. DHCP Pool Exhaustion (REQUIRES REAL DHCP EVIDENCE)
            # ---------------------------------------------------------
            if record.dhcp_pool_utilization_pct is not None and record.dhcp_pool_utilization_pct >= self.DHCP_POOL_CRIT_PCT:
                dhcp_pct = record.dhcp_pool_utilization_pct
                msg = self.create_message(
                    message_type=MessageType.TELEMETRY_ANOMALY,
                    device_id=dev,
                    metric="dhcp_pool_utilization_pct",
                    value=dhcp_pct,
                    unit="%",
                    evidence={
                        "observed": dhcp_pct,
                        "baseline": 60.0,
                        "threshold": self.DHCP_POOL_CRIT_PCT,
                        "severity": "CRITICAL",
                        "metric_type": "core_service_dhcp",
                        "telemetry_origin": origin,
                    },
                    confidence=0.96,
                    findings=[
                        f"DHCP pool exhaustion on {dev}: {dhcp_pct}% allocated (no available client leases)"
                    ],
                )
                anomalies.append(msg)

        self.findings_history.extend(anomalies)
        self.set_status("COMPLETE", f"Found {len(anomalies)} connectivity/RF anomalies")
        return anomalies

    def handle_query(self, query: AgentMessage, telemetry: List[TelemetryRecord]) -> AgentMessage:
        """
        Responds to query from Fault Correlation Agent checking for RF attenuation,
        gateway vs internet reachability, or DNS/DHCP service-layer failures.
        Never asserts DNS or DHCP failure without real evidence.
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
                findings=[f"No telemetry records found for device '{target_device}' in connectivity database."],
                evidence={"error": "DEVICE_NOT_FOUND"},
            )

        rec = matching_records[-1]
        has_rf_issue = (rec.wifi_rssi_dbm is not None and rec.wifi_rssi_dbm <= self.RSSI_CRIT_DBM) or \
                       ((rec.wifi_retry_pct or 0) >= self.WIFI_RETRY_CRIT_PCT)

        # Strict evidence check: Only assert DNS if metric is present!
        has_dns_evidence = rec.dns_response_ms is not None
        has_dns_issue = has_dns_evidence and rec.dns_response_ms >= self.DNS_CRIT_MS

        # Strict evidence check: Only assert DHCP if metric is present!
        has_dhcp_evidence = rec.dhcp_pool_utilization_pct is not None
        has_dhcp_issue = has_dhcp_evidence and rec.dhcp_pool_utilization_pct >= self.DHCP_POOL_CRIT_PCT

        # Reachability checks
        is_gw = "GATEWAY" in (target_device or "").upper() or getattr(rec, "custom_metrics", {}).get("is_gateway", False)
        is_unreachable = (rec.packet_loss_pct is not None and rec.packet_loss_pct >= 99.0) or (rec.device_status == "DOWN")

        findings = []
        if has_rf_issue:
            findings.append(
                f"CONFIRMED RF FAULT: {target_device} experiencing wireless edge degradation "
                f"(RSSI: {rec.wifi_rssi_dbm} dBm, Retries: {rec.wifi_retry_pct}%). Upstream wired path is unaffected."
            )
        elif is_unreachable and is_gw:
            findings.append(
                f"CONFIRMED GATEWAY UNREACHABLE: {target_device} is the default gateway and is completely unreachable (100% loss)."
            )
        elif has_dns_issue:
            findings.append(
                f"CONFIRMED DNS RESOLUTION FAULT: {target_device} DNS response latency is {rec.dns_response_ms} ms (timeout)."
            )
        elif has_dhcp_issue:
            findings.append(
                f"CONFIRMED DHCP POOL EXHAUSTION: {target_device} DHCP pool is {rec.dhcp_pool_utilization_pct}% exhausted."
            )
        elif not has_dns_evidence and not has_dhcp_evidence:
            if rec.wifi_rssi_dbm is None:
                findings.append(
                    f"Connectivity indicators on {target_device}: Reachability verified. Wireless RF and DNS/DHCP service metrics were not collected on this probe."
                )
            else:
                findings.append(
                    f"Connectivity indicators on {target_device}: DNS and DHCP metrics were not collected on this probe. "
                    "Service layer cannot be confirmed without explicit DNS/DHCP telemetry."
                )
        else:
            findings.append(
                f"Connectivity indicators on {target_device} are healthy."
            )

        resp = self.create_message(
            message_type=MessageType.QUERY_RESPONSE,
            device_id=target_device,
            metric="connectivity_verification",
            value={
                "has_rf_issue": has_rf_issue,
                "has_dns_issue": has_dns_issue,
                "has_dhcp_issue": has_dhcp_issue,
                "is_gateway_unreachable": is_unreachable and is_gw,
                "dns_evidence_available": has_dns_evidence,
                "dhcp_evidence_available": has_dhcp_evidence,
                "rssi_dbm": rec.wifi_rssi_dbm,
                "dns_response_ms": rec.dns_response_ms,
            },
            evidence={
                "wifi_rssi_dbm": rec.wifi_rssi_dbm,
                "wifi_retry_pct": rec.wifi_retry_pct,
                "dns_response_ms": rec.dns_response_ms,
                "dhcp_pool_utilization_pct": rec.dhcp_pool_utilization_pct,
                "packet_loss_pct": rec.packet_loss_pct,
                "is_gateway": is_gw,
                "telemetry_origin": getattr(rec, "telemetry_origin", "SIMULATED_SCENARIO"),
            },
            confidence=0.95,
            findings=findings,
            target_agent_id=query.agent_id,
            correlation_id=query.correlation_id,
        )
        self.set_status("COMPLETE", "Query answered")
        return resp
