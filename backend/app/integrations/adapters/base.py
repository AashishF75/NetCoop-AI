"""
Abstract Base Adapter for network telemetry ingestion.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.protocol.schema import TelemetryRecord
from app.integrations.models import NetworkSourceConfig, ConnectionTestResult


class BaseTelemetryAdapter(ABC):
    """
    Abstract base class for all live network telemetry adapters.
    Guarantees consistent normalized TelemetryRecord output and test probes.
    """

    def __init__(self, config: NetworkSourceConfig):
        self.config = config

    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        """
        Executes a live probe against the configured target.
        Must return an accurate ConnectionTestResult reflecting real connectivity.
        """
        pass

    @abstractmethod
    async def collect_telemetry(self) -> List[TelemetryRecord]:
        """
        Queries the device or service, parses real counters, and normalizes
        into canonical TelemetryRecord objects with telemetry_origin='LIVE'.
        """
        pass

    def build_record(
        self,
        device_id: Optional[str] = None,
        device_type: str = "router",
        device_status: str = "UP",
        interface_id: Optional[str] = None,
        latency_ms: Optional[float] = None,
        jitter_ms: Optional[float] = None,
        packet_loss_pct: Optional[float] = None,
        cpu_utilization_pct: Optional[float] = None,
        memory_utilization_pct: Optional[float] = None,
        utilization_pct: Optional[float] = None,
        queue_drops_per_sec: Optional[float] = None,
        interface_crc_errors: Optional[int] = 0,
        interface_flaps: Optional[int] = 0,
        wifi_rssi_dbm: Optional[float] = None,
        wifi_snr_db: Optional[float] = None,
        dns_response_ms: Optional[float] = None,
        dhcp_response_ms: Optional[float] = None,
        dhcp_pool_utilization_pct: Optional[float] = None,
        origin: str = "LIVE",
        custom_metrics: Optional[Dict[str, Any]] = None,
    ) -> TelemetryRecord:
        """
        Constructs a canonical TelemetryRecord matching the exact Pydantic schema.
        """
        return TelemetryRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            device_id=device_id or self.config.name or self.config.host,
            device_type=device_type,
            device_status=device_status,
            interface_id=interface_id,
            latency_ms=latency_ms,
            jitter_ms=jitter_ms,
            packet_loss_pct=packet_loss_pct,
            cpu_utilization_pct=cpu_utilization_pct,
            memory_utilization_pct=memory_utilization_pct,
            utilization_pct=utilization_pct,
            queue_drops_per_sec=queue_drops_per_sec,
            interface_crc_errors=interface_crc_errors,
            interface_flaps=interface_flaps,
            wifi_rssi_dbm=wifi_rssi_dbm,
            wifi_snr_db=wifi_snr_db,
            dns_response_ms=dns_response_ms,
            dhcp_response_ms=dhcp_response_ms,
            dhcp_pool_utilization_pct=dhcp_pool_utilization_pct,
            telemetry_origin=origin,
            source_id=self.config.id,
            custom_metrics=custom_metrics or {},
        )
