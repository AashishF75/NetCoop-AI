"""
Autonomous schema definition for the standalone on-premise collector.
Seamlessly binds to backend canonical schema if present, or provides standalone fallback.
"""

from typing import Optional
from datetime import datetime

try:
    from app.protocol.schema import TelemetryRecord
except ImportError:
    try:
        from backend.app.protocol.schema import TelemetryRecord
    except ImportError:
        from pydantic import BaseModel, Field

        class TelemetryRecord(BaseModel):
            timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
            device_id: str
            device_type: str = "router"
            device_status: str = "UP"
            latency_ms: Optional[float] = None
            packet_loss_pct: Optional[float] = None
            jitter_ms: Optional[float] = None
            cpu_utilization_pct: Optional[float] = None
            memory_utilization_pct: Optional[float] = None
            interface_status: Optional[str] = None
            crc_errors_delta: Optional[int] = None
            wlan_rssi_dbm: Optional[int] = None
            wlan_snr_db: Optional[int] = None
            wlan_channel_utilization_pct: Optional[float] = None
            wlan_connected_clients: Optional[int] = None
            dns_lookup_time_ms: Optional[float] = None
            dns_failure_rate_pct: Optional[float] = None
            dhcp_ack_time_ms: Optional[float] = None
            dhcp_failure_rate_pct: Optional[float] = None
            throughput_in_mbps: Optional[float] = None
            throughput_out_mbps: Optional[float] = None
            telemetry_origin: str = "LIVE_DEVICE"

