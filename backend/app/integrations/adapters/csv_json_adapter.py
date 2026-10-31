"""
CSV / JSON Telemetry Import Adapter.
Parses externally provided CSV or JSON telemetry dumps and normalizes them
with telemetry_origin='CUSTOM_IMPORT'.
"""

import csv
import io
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.protocol.schema import TelemetryRecord
from app.integrations.models import (
    NetworkSourceConfig,
    ConnectionTestResult,
    ConnectionStatus,
)
from app.integrations.adapters.base import BaseTelemetryAdapter


class FileImportAdapter(BaseTelemetryAdapter):
    """
    Adapter for imported CSV or JSON telemetry files.
    """

    def __init__(self, config: NetworkSourceConfig, content: Optional[str] = None):
        super().__init__(config)
        self.raw_content = content or ""

    def set_content(self, content: str) -> None:
        self.raw_content = content

    async def test_connection(self) -> ConnectionTestResult:
        if not self.raw_content:
            return ConnectionTestResult(
                source_id=self.config.id,
                source_name=self.config.name,
                source_type=self.config.source_type,
                success=True,
                status=ConnectionStatus.CONNECTED,
                message="File import channel ready for CSV or JSON payloads.",
            )

        try:
            records = await self.collect_telemetry()
            return ConnectionTestResult(
                source_id=self.config.id,
                source_name=self.config.name,
                source_type=self.config.source_type,
                success=True,
                status=ConnectionStatus.CONNECTED,
                message=f"Successfully parsed {len(records)} telemetry records from content.",
                details={"record_count": len(records)},
            )
        except Exception as e:
            return ConnectionTestResult(
                source_id=self.config.id,
                source_name=self.config.name,
                source_type=self.config.source_type,
                success=False,
                status=ConnectionStatus.ERROR,
                message=f"Parse failure: {str(e)}",
            )

    async def collect_telemetry(self) -> List[TelemetryRecord]:
        records: List[TelemetryRecord] = []
        if not self.raw_content.strip():
            return records

        text = self.raw_content.strip()

        # Try JSON first
        if text.startswith("[") or text.startswith("{"):
            try:
                parsed = json.loads(text)
                items = parsed if isinstance(parsed, list) else [parsed]
                for item in items:
                    rec = TelemetryRecord(
                        device_id=str(item.get("device_id", "Unknown-Device")),
                        timestamp=str(item.get("timestamp", datetime.now(timezone.utc).isoformat())),
                        device_type=str(item.get("device_type", "router")),
                        device_status=str(item.get("device_status", "UP")),
                        interface_id=item.get("interface_id"),
                        latency_ms=float(item["latency_ms"]) if "latency_ms" in item else None,
                        jitter_ms=float(item["jitter_ms"]) if "jitter_ms" in item else None,
                        packet_loss_pct=float(item["packet_loss_pct"]) if "packet_loss_pct" in item else None,
                        cpu_utilization_pct=float(item["cpu_utilization_pct"]) if "cpu_utilization_pct" in item else None,
                        memory_utilization_pct=float(item["memory_utilization_pct"]) if "memory_utilization_pct" in item else None,
                        interface_crc_errors=int(item.get("interface_crc_errors", 0)),
                        telemetry_origin="CUSTOM_IMPORT",
                        source_id=self.config.id,
                    )
                    records.append(rec)
                return records
            except Exception:
                pass

        # Try CSV
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            try:
                dev = row.get("device_id", "Unknown-Device")
                rec = TelemetryRecord(
                    device_id=dev,
                    timestamp=row.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    device_type=row.get("device_type", "router"),
                    device_status=row.get("device_status", "UP"),
                    interface_id=row.get("interface_id"),
                    latency_ms=float(row["latency_ms"]) if "latency_ms" in row and row["latency_ms"] else None,
                    jitter_ms=float(row["jitter_ms"]) if "jitter_ms" in row and row["jitter_ms"] else None,
                    packet_loss_pct=float(row["packet_loss_pct"]) if "packet_loss_pct" in row and row["packet_loss_pct"] else None,
                    cpu_utilization_pct=float(row["cpu_utilization_pct"]) if "cpu_utilization_pct" in row and row["cpu_utilization_pct"] else None,
                    memory_utilization_pct=float(row["memory_utilization_pct"]) if "memory_utilization_pct" in row and row["memory_utilization_pct"] else None,
                    interface_crc_errors=int(row["interface_crc_errors"]) if "interface_crc_errors" in row and row["interface_crc_errors"] else 0,
                    telemetry_origin="CUSTOM_IMPORT",
                    source_id=self.config.id,
                )
                records.append(rec)
            except Exception:
                pass

        return records
