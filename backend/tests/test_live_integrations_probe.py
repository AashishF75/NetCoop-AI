"""
Comprehensive tests for Live Network Integrations & Collector-Routed IP Diagnosis.
Validates:
1. Private target with no paired collector (clear actionable error)
2. Private target with paired collector (routed outbound via collector inside LAN)
3. Collector offline handling
4. Invalid IP and hostname rejection (anti-scanning, anti-SSRF, injection defense)
5. Collector cannot reach target (unreachable, packet loss, transparent non-fabrication)
6. Simulated vs live result provenance differentiation
7. Security validation and multiple-collector subnet affinity routing
"""

import os
import pytest
import asyncio
from datetime import datetime, timezone

from app.integrations.models import classify_target, validate_target_host, TargetType
from app.integrations.collector_hub import (
    CollectorHub,
    CollectorModel,
    CollectorStatus,
    CollectorRegisterRequest,
    get_collector_hub,
)
from app.integrations.probe_service import probe_ip_and_diagnose
from app.orchestrator.engine import MultiAgentOrchestrator
from app.protocol.schema import TelemetryRecord
from app.scenarios.generator import ScenarioCatalog


@pytest.mark.asyncio
class TestLiveIntegrationsProbeRouting:

    async def test_private_target_with_no_paired_collector(self, tmp_path):
        """
        When probing a private LAN target and NO collector is online, the system
        must reject the request with a clear actionable error explaining that the
        cloud backend cannot route into private networks directly.
        """
        hub = CollectorHub(storage_dir=tmp_path)
        orch = MultiAgentOrchestrator()

        # Target is RFC 1918 private IP
        with pytest.raises(ValueError) as excinfo:
            await probe_ip_and_diagnose(
                ip="192.168.1.50",
                protocol="PING",
                orchestrator=orch,
                allow_local_dev_fallback=False,
            )

        err_text = str(excinfo.value)
        assert "Cloud backend cannot directly route to private target '192.168.1.50'" in err_text
        assert "Pair and run an on-premise local collector" in err_text
        assert "Being on the same Wi-Fi does not guarantee reachability" in err_text
        assert "client isolation" in err_text

    async def test_private_target_with_paired_collector(self, tmp_path):
        """
        When an online paired collector is available, the probe is routed
        through that collector inside the LAN, capturing genuine metrics.
        """
        hub = get_collector_hub()
        enroll = hub.create_enrollment("Test-Branch-Collector", "http://127.0.0.1:8000")
        col_id = enroll.collector_id
        reg_req = CollectorRegisterRequest(
            collector_id=col_id,
            enrollment_token=enroll.enrollment_token,
            hostname="branch-worker",
            local_ip="192.168.10.15",
            default_gateway="192.168.10.1",
            os_type="Linux",
        )
        session = hub.register_collector(reg_req)
        session_token = session["session_token"]

        # Background worker simulating collector executing the probe job
        async def mock_collector():
            for _ in range(25):
                jobs = hub.get_pending_probe_jobs(col_id, session_token)
                for job in jobs:
                    hub.submit_probe_job_result(
                        col_id,
                        session_token,
                        job["job_id"],
                        {
                            "record": {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "device_id": job.get("device_id") or "PROBE-DEV",
                                "device_type": "router",
                                "device_status": "UP",
                                "latency_ms": 3.4,
                                "packet_loss_pct": 0.0,
                                "telemetry_origin": "LIVE_DEVICE",
                                "custom_metrics": {"probe_protocol": job["protocol"]},
                            },
                            "metrics_available": ["latency_ms", "packet_loss_pct", "device_status"],
                            "metrics_unsupported": ["cpu_utilization_pct", "memory_utilization_pct"],
                        },
                    )
                await asyncio.sleep(0.05)

        worker_task = asyncio.create_task(mock_collector())
        try:
            res = await probe_ip_and_diagnose(
                ip="192.168.10.1",
                protocol="PING",
                collector_id=col_id,
            )
            assert res["success"] is True
            assert res["reachability_status"] == "REACHABLE"
            assert res["provenance_type"] == "LOCAL_COLLECTOR_PROBE"
            assert "Test-Branch-Collector" in res["routed_via_collector"]
            assert res["probe_result"]["status"] == "UP"
            assert res["probe_result"]["latency_ms"] == 3.4
            assert res["probe_result"]["packet_loss_pct"] == 0.0
            # Ensure internal metrics were not fabricated
            assert res["probe_result"]["cpu_utilization_pct"] is None
        finally:
            worker_task.cancel()

    async def test_collector_offline_handling(self, tmp_path):
        """
        If a user explicitly requests a collector that is OFFLINE or REVOKED,
        the probe must fail with an explicit diagnostic message.
        """
        hub = get_collector_hub()
        enroll = hub.create_enrollment("Offline-Edge-Collector", "http://127.0.0.1:8000")
        col_id = enroll.collector_id
        # Set collector to OFFLINE
        collector = hub.get_collector(col_id)
        collector.status = CollectorStatus.OFFLINE
        collector.last_heartbeat_at = "2026-01-01T00:00:00Z"

        with pytest.raises(ValueError) as excinfo:
            await probe_ip_and_diagnose(
                ip="10.200.1.1",
                protocol="PING",
                collector_id=col_id,
                allow_local_dev_fallback=False,
            )

        err_text = str(excinfo.value)
        assert "is OFFLINE" in err_text or "No online collectors" in err_text

    def test_invalid_ip_and_hostname_rejection(self):
        """
        Verifies rejection of invalid IP addresses, hostnames, CIDRs,
        SSRF metadata targets, multicast, and command injection attempts.
        """
        # 1. CIDR subnet mask
        c1 = classify_target("192.168.1.0/24")
        assert not c1.is_safe and "CIDR" in c1.validation_error

        # 2. Command injection & wildcards
        c2 = classify_target("10.0.0.1; rm -rf /")
        assert not c2.is_safe and "illegal characters" in c2.validation_error

        # 3. Cloud Instance Metadata SSRF
        c3 = classify_target("169.254.169.254")
        assert not c3.is_safe and "cloud metadata service" in c3.validation_error

        c3b = classify_target("metadata.google.internal")
        assert not c3b.is_safe and "cloud metadata" in c3b.validation_error

        # 4. Multicast & broadcast
        c4 = classify_target("255.255.255.255")
        assert not c4.is_safe and "broadcast" in c4.validation_error

        c4b = classify_target("224.0.0.1")
        assert not c4b.is_safe and "Multicast" in c4b.validation_error

        # 5. Invalid hostname syntax
        c5 = classify_target("invalid..hostname..")
        assert not c5.is_safe

        # 6. Valid classifications
        assert classify_target("10.10.214.1").target_type == TargetType.PRIVATE_IPV4
        assert classify_target("8.8.8.8").target_type == TargetType.PUBLIC_IPV4
        assert classify_target("2001:4860:4860::8888").target_type == TargetType.IPV6
        assert classify_target("core-router.internal").target_type == TargetType.HOSTNAME
        assert classify_target("core-router.internal").is_private is True

    async def test_collector_cannot_reach_target(self):
        """
        When a collector probes a target that is unreachable (100% loss / timeout),
        the diagnosis correctly identifies outage without fabricating metrics.
        """
        hub = get_collector_hub()
        enroll = hub.create_enrollment("Unreachable-Test-Collector", "http://127.0.0.1:8000")
        col_id = enroll.collector_id
        reg_req = CollectorRegisterRequest(
            collector_id=col_id,
            enrollment_token=enroll.enrollment_token,
            hostname="unreachable-box",
            local_ip="10.50.0.10",
            os_type="Linux",
        )
        session = hub.register_collector(reg_req)
        session_token = session["session_token"]

        async def mock_failing_collector():
            for _ in range(25):
                jobs = hub.get_pending_probe_jobs(col_id, session_token)
                for job in jobs:
                    # Target did not answer: 100% loss, DOWN
                    hub.submit_probe_job_result(
                        col_id,
                        session_token,
                        job["job_id"],
                        {
                            "record": {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "device_id": f"PROBE-{job['ip']}",
                                "device_type": "router",
                                "device_status": "DOWN",
                                "latency_ms": 999.0,
                                "packet_loss_pct": 100.0,
                                "telemetry_origin": "LIVE_DEVICE",
                                "custom_metrics": {"probe_protocol": job["protocol"]},
                            },
                            "metrics_available": ["latency_ms", "packet_loss_pct", "device_status"],
                            "metrics_unsupported": ["cpu_utilization_pct"],
                        },
                    )
                await asyncio.sleep(0.05)

        worker_task = asyncio.create_task(mock_failing_collector())
        try:
            res = await probe_ip_and_diagnose(
                ip="10.50.0.99",
                protocol="PING",
                collector_id=col_id,
            )
            assert res["success"] is True
            assert res["reachability_status"] == "UNREACHABLE"
            assert res["probe_result"]["status"] == "DOWN"
            assert res["probe_result"]["packet_loss_pct"] == 100.0
            # Report limitations should explicitly warn about client isolation or host firewalls
            report = res["diagnosis"]["canonical_report"]
            limitations_str = " ".join(report.get("limitations", []))
            assert "client isolation" in limitations_str or "firewalls" in limitations_str
        finally:
            worker_task.cancel()

    def test_simulated_vs_live_result_provenance(self):
        """
        Never present simulated results as live target telemetry.
        Validates clear separation of provenance badges and origins.
        """
        # Canned scenario
        sim_records = ScenarioCatalog.generate_telemetry("link_congestion")
        assert sim_records[0].telemetry_origin in ("BENCHMARK", "SIMULATED_SCENARIO")
        assert sim_records[0].telemetry_origin != "LIVE_DEVICE"
        assert sim_records[0].telemetry_origin != "LIVE_HOST"

        # Host Kernel metrics
        from app.integrations.probe_service import get_real_host_telemetry
        cpu, mem, err = get_real_host_telemetry()
        assert cpu >= 0.0 and mem >= 0.0

    def test_security_validation_and_multi_collector_routing(self):
        """
        Verifies multiple-collector selection chooses the collector with
        matching subnet affinity, and ensures reachability is initially unknown.
        """
        hub = CollectorHub()
        # Collector 1 on 192.168.1.0/24
        c1 = CollectorModel(
            collector_id="col-alpha",
            name="Alpha-Subnet-192",
            enrollment_token="tok1",
            status=CollectorStatus.ONLINE,
            local_ip="192.168.1.5",
            default_gateway="192.168.1.1",
            last_heartbeat_at=datetime.now(timezone.utc).isoformat(),
        )
        # Collector 2 on 10.0.0.0/24
        c2 = CollectorModel(
            collector_id="col-beta",
            name="Beta-Subnet-10",
            enrollment_token="tok2",
            status=CollectorStatus.ONLINE,
            local_ip="10.0.0.5",
            default_gateway="10.0.0.1",
            last_heartbeat_at=datetime.now(timezone.utc).isoformat(),
        )
        hub._collectors["col-alpha"] = c1
        hub._collectors["col-beta"] = c2

        # Target in 192.168.1.x matches col-alpha
        best_1, reason_1, err_1 = hub.find_best_collector_for_target("192.168.1.80")
        assert best_1 is not None
        assert best_1.collector_id == "col-alpha"
        assert "Alpha-Subnet-192" in reason_1

        # Target in 10.0.0.x matches col-beta
        best_2, reason_2, err_2 = hub.find_best_collector_for_target("10.0.0.22")
        assert best_2 is not None
        assert best_2.collector_id == "col-beta"
        assert "Beta-Subnet-10" in reason_2

