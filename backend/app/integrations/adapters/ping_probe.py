"""
Active Network Socket & Ping Probe Telemetry Adapter.
Performs real asynchronous non-blocking TCP/socket reachability, latency, jitter,
and packet loss measurements against routers, switches, gateways, or services.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.protocol.schema import TelemetryRecord
from app.integrations.models import NetworkSourceConfig, ConnectionTestResult, ConnectionStatus
from app.integrations.adapters.base import BaseTelemetryAdapter


class PingProbeAdapter(BaseTelemetryAdapter):
    """
    Active socket probe measuring actual network latency, jitter, and reachability.
    """

    async def _single_probe(self, host: str, port: int, timeout_sec: float) -> Optional[float]:
        """
        Executes a single non-blocking connection attempt, returning round-trip time in milliseconds.
        """
        t0 = time.perf_counter()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout_sec,
            )
            rtt_ms = (time.perf_counter() - t0) * 1000.0
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return max(rtt_ms, 0.05)
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return None

    async def _run_probe_burst(self, count: int = 3) -> Dict[str, Any]:
        """
        Runs a burst of probes to calculate latency, jitter, and packet loss.
        """
        host = self.config.host
        port = self.config.port or 80
        timeout_sec = max(self.config.timeout_sec, 0.5)

        rtts: List[float] = []
        lost_count = 0

        for _ in range(count):
            rtt = await self._single_probe(host, port, timeout_sec)
            if rtt is not None:
                rtts.append(rtt)
            else:
                lost_count += 1
            if count > 1:
                await asyncio.sleep(0.05)

        loss_pct = (lost_count / count) * 100.0
        avg_latency = statistics.mean(rtts) if rtts else None
        min_latency = min(rtts) if rtts else None
        max_latency = max(rtts) if rtts else None
        jitter = statistics.stdev(rtts) if len(rtts) > 1 else (0.0 if rtts else None)

        return {
            "loss_pct": loss_pct,
            "avg_latency": avg_latency,
            "min_latency": min_latency,
            "max_latency": max_latency,
            "jitter": jitter,
            "successful_probes": len(rtts),
            "total_probes": count,
        }

    async def test_connection(self) -> ConnectionTestResult:
        """
        Performs live reachability test and measures physical connection metrics.
        """
        burst = await self._run_probe_burst(count=3)
        host = self.config.host
        port = self.config.port or 80

        if burst["successful_probes"] == 0:
            return ConnectionTestResult(
                source_id=self.config.id,
                source_name=self.config.name,
                source_type=self.config.source_type,
                success=False,
                status=ConnectionStatus.DISCONNECTED,
                packet_loss_pct=100.0,
                message=f"Connection failed: Host {host}:{port} timed out or refused connection.",
                details=burst,
            )

        loss = burst["loss_pct"]
        lat = burst["avg_latency"]
        jitter = burst["jitter"] or 0.0

        if loss > 0.0 or (lat is not None and lat > 200.0):
            status = ConnectionStatus.DEGRADED
            msg = f"Connection established with degradation: avg latency {lat:.2f}ms, packet loss {loss:.1f}%."
        else:
            status = ConnectionStatus.CONNECTED
            msg = f"Connection verified: Host {host}:{port} responded in {lat:.2f}ms (jitter: {jitter:.2f}ms, 0% loss)."

        return ConnectionTestResult(
            source_id=self.config.id,
            source_name=self.config.name,
            source_type=self.config.source_type,
            success=True,
            status=status,
            latency_ms=round(lat, 2) if lat is not None else None,
            jitter_ms=round(jitter, 2),
            packet_loss_pct=round(loss, 1),
            message=msg,
            details=burst,
        )

    async def collect_telemetry(self) -> List[TelemetryRecord]:
        """
        Collects real live latency, jitter, and packet loss metrics into a canonical snapshot.
        """
        burst = await self._run_probe_burst(count=3)
        device_id = self.config.name or self.config.host
        loss = burst["loss_pct"]
        lat = burst["avg_latency"]
        jitter = burst["jitter"] or 0.0

        status_str = "DOWN" if loss >= 100.0 else ("DEGRADED" if loss > 0.0 or (lat and lat > 200.0) else "UP")

        record = self.build_record(
            device_id=device_id,
            device_type="router",
            device_status=status_str,
            latency_ms=round(lat, 2) if lat is not None else 999.0,
            jitter_ms=round(jitter, 2),
            packet_loss_pct=round(loss, 1),
            origin="LIVE",
        )
        return [record]
