"""
Connectivity Analysis Agent.
Analyzes wireless RF health (RSSI, SNR, 802.11 retries), DNS resolution latencies,
DHCP allocation pools, link adjacency, and service-layer reachability.
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
            role="RF, L2/L3 Adjacency & Core Services Monitor",
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
        self.set_status("ANALYZING", "Evaluating Wi-Fi RF signal, DNS resolver, and DHCP pools")
        anomalies: List[AgentMessage] = []

        for record in telemetry:
            dev = record.device_id

            # 1. Wi-Fi RF Signal Degradation (RSSI / SNR / Retries)
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
                            "metric_type": "wireless_rf"
                        },
                        confidence=conf,
                        findings=[
                            f"Severe Wi-Fi signal attenuation on {dev}: RSSI {rssi} dBm (crit < {self.RSSI_CRIT_DBM}), "
                            f"SNR {snr} dB, frame retries {retries}%"
                        ]
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
                            "metric_type": "wireless_rf"
                        },
                        confidence=0.74,
                        findings=[
                            f"Marginal Wi-Fi coverage on {dev}: RSSI {rssi} dBm"
                        ]
                    )
                    anomalies.append(msg)

            # 2. DNS Resolution Latency & Timeout
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
                            "metric_type": "core_service_dns"
                        },
                        confidence=min(0.98, 0.85 + (dns_ms / 5000.0) * 0.12),
                        findings=[
                            f"Critical DNS resolution timeout on {dev}: {dns_ms} ms (baseline: 15 ms, timeout > {self.DNS_CRIT_MS} ms)"
                        ]
                    )
                    anomalies.append(msg)

            # 3. DHCP Pool Exhaustion
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
                        "metric_type": "core_service_dhcp"
                    },
                    confidence=0.96,
                    findings=[
                        f"DHCP pool exhaustion on {dev}: {dhcp_pct}% allocated (no available client leases)"
                    ]
                )
                anomalies.append(msg)

        self.findings_history.extend(anomalies)
        self.set_status("COMPLETE", f"Found {len(anomalies)} connectivity/RF anomalies")
        return anomalies

    def handle_query(self, query: AgentMessage, telemetry: List[TelemetryRecord]) -> AgentMessage:
        """
        Responds to query from Fault Correlation Agent checking for RF attenuation
        or DNS/DHCP service-layer failures.
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
                evidence={"error": "DEVICE_NOT_FOUND"}
            )

        rec = matching_records[-1]
        has_rf_issue = (rec.wifi_rssi_dbm is not None and rec.wifi_rssi_dbm <= self.RSSI_CRIT_DBM) or \
                       ((rec.wifi_retry_pct or 0) >= self.WIFI_RETRY_CRIT_PCT)
        has_dns_issue = (rec.dns_response_ms is not None and rec.dns_response_ms >= self.DNS_CRIT_MS)
        has_dhcp_issue = (rec.dhcp_pool_utilization_pct is not None and rec.dhcp_pool_utilization_pct >= self.DHCP_POOL_CRIT_PCT)

        findings = []
        if has_rf_issue:
            findings.append(
                f"CONFIRMED RF FAULT: {target_device} experiencing wireless edge degradation "
                f"(RSSI: {rec.wifi_rssi_dbm} dBm, Retries: {rec.wifi_retry_pct}%). Upstream wired path is unaffected."
            )
        elif has_dns_issue or has_dhcp_issue:
            findings.append(
                f"CONFIRMED SERVICE FAULT: {target_device} DNS latency: {rec.dns_response_ms} ms, "
                f"DHCP pool: {rec.dhcp_pool_utilization_pct}%. IP transport layer is operational."
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
                "rssi_dbm": rec.wifi_rssi_dbm,
                "dns_response_ms": rec.dns_response_ms,
            },
            evidence={
                "wifi_rssi_dbm": rec.wifi_rssi_dbm,
                "wifi_retry_pct": rec.wifi_retry_pct,
                "dns_response_ms": rec.dns_response_ms,
                "dhcp_pool_utilization_pct": rec.dhcp_pool_utilization_pct,
            },
            confidence=0.95,
            findings=findings,
            target_agent_id=query.agent_id,
            correlation_id=query.correlation_id,
        )
        self.set_status("COMPLETE", "Query answered")
        return resp
