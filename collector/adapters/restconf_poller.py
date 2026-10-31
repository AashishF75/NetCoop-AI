"""
Cisco IOS-XE & OpenConfig RESTCONF Interface Poller.
Queries RFC 8040 RESTCONF interfaces-state endpoints over HTTPS/HTTP.
"""

import time
import httpx
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timezone

from collector.schema import TelemetryRecord
from collector.config import LocalDeviceConfig


async def poll_restconf_device(device: LocalDeviceConfig) -> Tuple[List[TelemetryRecord], List[str], List[str]]:
    """
    Queries Cisco IOS-XE or OpenConfig RESTCONF interfaces-state.
    Returns: (records, metrics_available, metrics_unsupported)
    """
    protocol = "https" if device.port in [443, 8443] else "http"
    port_str = f":{device.port}" if device.port not in [80, 443] else ""
    endpoint = device.rest_endpoint or "/restconf/data/ietf-interfaces:interfaces-state"
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    url = f"{protocol}://{device.host}{port_str}{endpoint}"

    headers = {
        "Accept": "application/yang-data+json, application/json",
        "User-Agent": "NetCoopAI-Collector/1.0",
    }
    auth = None
    if device.username and device.password:
        auth = (device.username, device.password)
    elif device.api_key:
        headers["X-API-Key"] = device.api_key

    timeout_sec = max(device.timeout_sec, 1.0)
    t0 = time.perf_counter()

    available_metrics = ["latency_ms", "packet_loss_pct", "device_status"]
    unsupported_metrics = ["wifi_rssi_dbm", "wifi_snr_db"]

    try:
        async with httpx.AsyncClient(headers=headers, auth=auth, verify=False, timeout=timeout_sec) as client:
            resp = await client.get(url)
            lat_ms = (time.perf_counter() - t0) * 1000.0

            if resp.status_code == 200:
                data = resp.json()
                oper_status = "UP"
                crc_errors = 0
                queue_drops = 0.0
                bandwidth_mbps = None

                # Parse ietf-interfaces:interfaces-state
                if "ietf-interfaces:interfaces-state" in data:
                    ifaces = data["ietf-interfaces:interfaces-state"].get("interface", [])
                    if ifaces:
                        first = ifaces[0]
                        st = first.get("oper-status", "up")
                        oper_status = "UP" if st == "up" else "DOWN"
                        stats = first.get("statistics", {})
                        crc_errors = int(stats.get("in-errors", 0))
                        queue_drops = float(stats.get("in-discards", 0))
                        available_metrics.extend(["interface_crc_errors", "queue_drops_per_sec"])

                record = TelemetryRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    device_id=device.device_id,
                    device_type=device.device_type,
                    device_status=oper_status,
                    latency_ms=round(lat_ms, 2),
                    packet_loss_pct=0.0 if oper_status == "UP" else 100.0,
                    interface_crc_errors=crc_errors,
                    queue_drops_per_sec=queue_drops,
                    telemetry_origin="LIVE_DEVICE",
                    custom_metrics={
                        "protocol": "RESTCONF",
                        "endpoint": endpoint,
                        "http_status": resp.status_code,
                    },
                )
                return [record], available_metrics, unsupported_metrics

            elif resp.status_code in [401, 403]:
                record = TelemetryRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    device_id=device.device_id,
                    device_type=device.device_type,
                    device_status="AUTH_REJECTED",
                    packet_loss_pct=100.0,
                    telemetry_origin="LIVE_DEVICE",
                    custom_metrics={"http_status": resp.status_code, "auth_error": "Authentication rejected by router"},
                )
                return [record], [], ["interface_crc_errors", "queue_drops_per_sec", "bandwidth_mbps"]
            else:
                record = TelemetryRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    device_id=device.device_id,
                    device_type=device.device_type,
                    device_status="DEGRADED",
                    latency_ms=round(lat_ms, 2),
                    packet_loss_pct=0.0,
                    telemetry_origin="LIVE_DEVICE",
                    custom_metrics={"http_status": resp.status_code},
                )
                return [record], ["latency_ms", "device_status"], unsupported_metrics

    except Exception as e:
        record = TelemetryRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            device_id=device.device_id,
            device_type=device.device_type,
            device_status="DOWN",
            packet_loss_pct=100.0,
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={"error": str(e)},
        )
        return [record], [], ["interface_crc_errors", "queue_drops_per_sec", "bandwidth_mbps"]
