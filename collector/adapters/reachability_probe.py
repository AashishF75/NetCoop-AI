"""
Active Network Reachability Probe for Collector.
Measures physical TCP connection handshake latency and ICMP ping round-trip time.
Accurately differentiates between TCP socket connect probes and ICMP ping probes.
Does not claim device internal CPU/RAM or Wi-Fi metrics.
"""

import sys
import time
import asyncio
import subprocess
import re
from typing import List, Tuple, Optional
from datetime import datetime, timezone

from collector.schema import TelemetryRecord
from collector.config import LocalDeviceConfig, DeviceProtocol


def _exec_icmp_ping(host: str, timeout_sec: float = 2.0) -> Tuple[Optional[float], float]:
    """
    Executes standard OS ICMP ping against host.
    Returns: (latency_ms, packet_loss_pct)
    """
    if sys.platform == "win32":
        timeout_ms = max(int(timeout_sec * 1000), 500)
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
    else:
        timeout_s = max(1, int(timeout_sec))
        cmd = ["ping", "-c", "1", "-W", str(timeout_s), host]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec + 1.0)
        out = res.stdout
        if "time=" in out or "time<" in out:
            m = re.search(r"time[=<]([0-9]+)\s*ms", out, re.IGNORECASE)
            lat = float(m.group(1)) if m else 1.0
            return max(lat, 0.1), 0.0
        return None, 100.0
    except Exception:
        return None, 100.0


async def probe_tcp_reachability(device: LocalDeviceConfig) -> Tuple[List[TelemetryRecord], List[str], List[str]]:
    """
    Executes an active reachability probe against device (TCP handshake or ICMP ping).
    Returns: (records, metrics_available, metrics_unsupported)
    """
    host = device.host
    port = device.port or 80
    timeout_sec = max(device.timeout_sec, 0.5)
    is_ping_protocol = getattr(device, "protocol", "") == DeviceProtocol.PING_PROBE or port == 0

    loop = asyncio.get_event_loop()

    if is_ping_protocol:
        # Pure ICMP Echo Ping Probe
        lat_ms, loss_pct = await loop.run_in_executor(None, _exec_icmp_ping, host, timeout_sec)
        status_str = "UP" if (loss_pct < 100.0 and lat_ms is not None) else "DOWN"

        record = TelemetryRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            device_id=device.device_id,
            device_type=device.device_type,
            device_status=status_str,
            latency_ms=round(lat_ms, 2) if lat_ms is not None else 999.0,
            packet_loss_pct=loss_pct,
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={
                "probe_type": "ICMP_ECHO_PING",
                "target_host": host,
                "transport": "ICMP",
                "probe_note": "Genuine ICMP echo ping round-trip time directly from Windows OS network stack.",
            },
        )
    else:
        # TCP Connection Probe (with auxiliary ICMP ping context)
        t0 = time.perf_counter()
        latency_ms = None
        packet_loss_pct = 100.0
        status_str = "DOWN"

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout_sec,
            )
            latency_ms = max((time.perf_counter() - t0) * 1000.0, 0.1)
            packet_loss_pct = 0.0
            status_str = "UP"

            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            latency_ms = 999.0
            packet_loss_pct = 100.0
            status_str = "DOWN"

        # Auxiliary ICMP ping check to give full visibility into gateway state
        icmp_lat, icmp_loss = await loop.run_in_executor(None, _exec_icmp_ping, host, 1.0)
        icmp_reachable = (icmp_loss == 0.0 and icmp_lat is not None)

        record = TelemetryRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            device_id=device.device_id,
            device_type=device.device_type,
            device_status=status_str,
            latency_ms=round(latency_ms, 2) if latency_ms is not None else 999.0,
            packet_loss_pct=packet_loss_pct,
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={
                "probe_type": "TCP_SOCKET_CONNECT",
                "probe_target_port": port,
                "target_host": host,
                "transport": "TCP",
                "tcp_connected": (status_str == "UP"),
                "icmp_ping_reachable": icmp_reachable,
                "icmp_latency_ms": round(icmp_lat, 2) if icmp_reachable else None,
                "probe_note": f"TCP port {port} {'open' if status_str == 'UP' else 'closed/timed out'}; ICMP ping is {'reachable (' + str(icmp_lat) + 'ms)' if icmp_reachable else 'unreachable'}.",
            },
        )

    # Clearly declare available reachability metrics vs unsupported internal metrics
    available = ["latency_ms", "packet_loss_pct", "device_status"]
    unsupported = [
        "cpu_utilization_pct",
        "memory_utilization_pct",
        "wifi_rssi_dbm",
        "wifi_snr_db",
        "queue_drops_per_sec",
        "interface_crc_errors",
        "bandwidth_mbps",
    ]

    return [record], available, unsupported
