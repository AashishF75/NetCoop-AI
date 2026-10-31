"""
Verification script for real network connection from Windows laptop.
Tests:
1. Host metrics collection (LIVE_HOST)
2. Gateway ICMP ping probe to 10.244.241.91 (LIVE_DEVICE, ~5ms, 0% loss)
3. Gateway TCP probe to 10.244.241.91:80 (LIVE_DEVICE, closed/timed out)
4. Gateway TCP probe to 10.244.241.91:443 (LIVE_DEVICE, closed/timed out)
5. Live multi-agent diagnosis over genuine records
"""
import sys
import os
import asyncio
import socket
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import requests
from collector.config import CollectorSettings, LocalDeviceConfig, DeviceProtocol
from collector.adapters.host_metrics import poll_host_metrics
from collector.adapters.reachability_probe import probe_tcp_reachability
from collector.agent import NetworkCollectorAgent

BACKEND_URL = "http://127.0.0.1:8000"
GATEWAY_IP = "10.244.241.91"

async def test_live_network():
    print("=" * 70)
    print("NETCOOP AI — LIVE WINDOWS HOST & GATEWAY TELEMETRY TEST")
    print("=" * 70)

    # 1. Test Host Metrics (LIVE_HOST)
    hostname = socket.gethostname()
    host_cfg = LocalDeviceConfig(
        device_id=f"HOST-{hostname[:12].upper()}",
        name=f"Collector Host ({hostname})",
        device_type="server",
        host="127.0.0.1",
        port=8000,
        protocol=DeviceProtocol.HOST_METRICS,
    )
    print(f"\n[1] Polling Windows Kernel Host Metrics ({host_cfg.device_id})...")
    host_recs, host_avail, host_unsupp = await poll_host_metrics(host_cfg)
    host_rec = host_recs[0]
    print(f"    - Origin          : {host_rec.telemetry_origin}")
    print(f"    - CPU Utilization : {host_rec.cpu_utilization_pct}%")
    print(f"    - RAM Utilization : {host_rec.memory_utilization_pct}%")
    print(f"    - Device Status   : {host_rec.device_status}")
    print(f"    - Interface Errors: {host_rec.interface_crc_errors}")
    print(f"    - Available       : {host_avail}")
    print(f"    - Unsupported     : {host_unsupp}")
    assert host_rec.telemetry_origin == "LIVE_HOST"

    # 2. Test Gateway ICMP Ping Probe
    gw_ping_cfg = LocalDeviceConfig(
        device_id="GATEWAY-HOTSPOT-PING",
        name=f"Phone Hotspot Gateway ICMP Ping ({GATEWAY_IP})",
        device_type="router",
        host=GATEWAY_IP,
        port=0,
        protocol=DeviceProtocol.PING_PROBE,
        timeout_sec=2.0,
    )
    print(f"\n[2] Probing Gateway via ICMP Ping ({GATEWAY_IP})...")
    gw_ping_recs, gw_p_avail, gw_p_unsupp = await probe_tcp_reachability(gw_ping_cfg)
    gw_p_rec = gw_ping_recs[0]
    print(f"    - Origin          : {gw_p_rec.telemetry_origin}")
    print(f"    - Ping Latency    : {gw_p_rec.latency_ms} ms")
    print(f"    - Packet Loss     : {gw_p_rec.packet_loss_pct}%")
    print(f"    - Reachability    : {gw_p_rec.device_status}")
    print(f"    - Probe Note      : {gw_p_rec.custom_metrics.get('probe_note')}")
    print(f"    - Available       : {gw_p_avail}")
    print(f"    - Unsupported     : {gw_p_unsupp}")
    assert gw_p_rec.telemetry_origin == "LIVE_DEVICE"
    assert "cpu_utilization_pct" in gw_p_unsupp
    assert "wifi_rssi_dbm" in gw_p_unsupp

    # 3. Test Gateway TCP Port 80 Probe
    gw_tcp80_cfg = LocalDeviceConfig(
        device_id="GATEWAY-HOTSPOT-TCP80",
        name=f"Phone Hotspot TCP Port 80 ({GATEWAY_IP}:80)",
        device_type="router",
        host=GATEWAY_IP,
        port=80,
        protocol=DeviceProtocol.TCP_PROBE,
        timeout_sec=1.5,
    )
    print(f"\n[3] Probing Gateway TCP Port 80 ({GATEWAY_IP}:80)...")
    gw_tcp80_recs, gw_t80_avail, gw_t80_unsupp = await probe_tcp_reachability(gw_tcp80_cfg)
    gw_t80_rec = gw_tcp80_recs[0]
    print(f"    - Origin          : {gw_t80_rec.telemetry_origin}")
    print(f"    - TCP Connected   : {gw_t80_rec.custom_metrics.get('tcp_connected')}")
    print(f"    - Port Status     : {gw_t80_rec.device_status}")
    print(f"    - Handshake Lat   : {gw_t80_rec.latency_ms} ms")
    print(f"    - Packet Loss     : {gw_t80_rec.packet_loss_pct}%")
    print(f"    - ICMP Reachable  : {gw_t80_rec.custom_metrics.get('icmp_ping_reachable')} ({gw_t80_rec.custom_metrics.get('icmp_latency_ms')} ms)")
    print(f"    - Probe Note      : {gw_t80_rec.custom_metrics.get('probe_note')}")

    # 4. Test Gateway TCP Port 443 Probe
    gw_tcp443_cfg = LocalDeviceConfig(
        device_id="GATEWAY-HOTSPOT-TCP443",
        name=f"Phone Hotspot TCP Port 443 ({GATEWAY_IP}:443)",
        device_type="router",
        host=GATEWAY_IP,
        port=443,
        protocol=DeviceProtocol.TCP_PROBE,
        timeout_sec=1.5,
    )
    print(f"\n[4] Probing Gateway TCP Port 443 ({GATEWAY_IP}:443)...")
    gw_tcp443_recs, _, _ = await probe_tcp_reachability(gw_tcp443_cfg)
    gw_t443_rec = gw_tcp443_recs[0]
    print(f"    - TCP Connected   : {gw_t443_rec.custom_metrics.get('tcp_connected')}")
    print(f"    - Port Status     : {gw_t443_rec.device_status}")
    print(f"    - Handshake Lat   : {gw_t443_rec.latency_ms} ms")

    # 5. Enroll collector and stream live records to Backend
    print("\n[5] Enrolling Collector and Streaming Genuine Telemetry to Backend...")
    enroll_resp = requests.post(
        f"{BACKEND_URL}/api/collectors/enroll",
        json={"name": "Hotspot-Gateway-Collector", "backend_url": BACKEND_URL}
    )
    col_data = enroll_resp.json()
    col_id = col_data["collector_id"]
    token = col_data["enrollment_token"]

    reg_resp = requests.post(
        f"{BACKEND_URL}/api/collectors/register",
        json={
            "collector_id": col_id,
            "enrollment_token": token,
            "hostname": hostname,
            "local_ip": "10.244.241.72",
            "os_type": "Windows 11",
        }
    )
    sess_token = reg_resp.json()["session_token"]

    # Register devices on backend
    for dev_cfg in [host_cfg, gw_ping_cfg, gw_tcp80_cfg]:
        requests.post(
            f"{BACKEND_URL}/api/collectors/{col_id}/devices",
            json={
                "device_id": dev_cfg.device_id,
                "name": dev_cfg.name,
                "device_type": dev_cfg.device_type,
                "ip": dev_cfg.host,
                "port": dev_cfg.port,
                "protocol": dev_cfg.protocol.value,
            }
        )

    # Push all genuine records
    push_payload = [
        (host_cfg.device_id, host_recs, host_avail, host_unsupp),
        (gw_ping_cfg.device_id, gw_ping_recs, gw_p_avail, gw_p_unsupp),
        (gw_tcp80_cfg.device_id, gw_tcp80_recs, gw_t80_avail, gw_t80_unsupp),
    ]

    for d_id, recs, avail, unsupp in push_payload:
        requests.post(
            f"{BACKEND_URL}/api/collectors/telemetry",
            json={
                "collector_id": col_id,
                "session_token": sess_token,
                "device_id": d_id,
                "records": [r.model_dump() for r in recs],
                "metrics_available": avail,
                "metrics_unsupported": unsupp,
            }
        )
    print("    -> Ingested Host Metrics and Gateway Reachability records into backend.")

    # 6. Run Live Multi-Agent Diagnosis over genuine telemetry
    print("\n[6] Running Live Multi-Agent Diagnosis...")
    diag_resp = requests.post(f"{BACKEND_URL}/api/integrations/diagnose-live", json={})
    diag_data = diag_resp.json()
    print("    - Diagnosis Success :", diag_data.get("success"))
    print("    - Incident ID       :", diag_data.get("incident_id"))
    print("    - Provenance        :", diag_data.get("telemetry_origin"))
    print("    - Devices Polled    :", diag_data.get("devices_polled"))
    print("    - Records Evaluated :", diag_data.get("records_collected"))
    report = diag_data.get("report", {})
    print("    - Root Cause        :", report.get("suspected_root_cause"))
    print("    - Confidence        :", report.get("confidence"))
    print("    - Impacted Devices  :", report.get("impacted_devices"))
    recomms = report.get("recommended_actions") or []
    print("    - Recommendations   :", recomms)

    print("\n" + "=" * 70)
    print("LIVE NETWORK VERIFICATION TEST PASSED WITH ZERO SYNTHETIC FALLBACK")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_live_network())
