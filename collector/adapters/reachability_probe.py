"""
Active TCP Reachability Probe for Collector.
Measures physical TCP connection handshake latency and packet loss.
Clearly labeled as TCP connection latency (NOT ICMP ping).
"""

import asyncio
import time
from typing import List, Tuple
from datetime import datetime, timezone

from collector.schema import TelemetryRecord
from collector.config import LocalDeviceConfig


async def probe_tcp_reachability(device: LocalDeviceConfig) -> Tuple[List[TelemetryRecord], List[str], List[str]]:
    """
    Executes an active non-blocking TCP handshake probe against device:port.
    Returns: (records, metrics_available, metrics_unsupported)
    """
    host = device.host
    port = device.port or 80
    timeout_sec = max(device.timeout_sec, 0.5)

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
            "transport": "TCP",
            "probe_note": "Accurate TCP handshake latency. Not ICMP ping.",
        },
    )

    available = ["latency_ms", "packet_loss_pct", "device_status"]
    unsupported = ["cpu_utilization_pct", "queue_drops_per_sec", "interface_crc_errors", "bandwidth_mbps"]

    return [record], available, unsupported
