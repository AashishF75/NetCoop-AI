"""
Network Integrations Manager for NetCoop AI.
Maintains persistent source registries, executes real connection tests,
polls live telemetry from network devices, and dispatches to the Multi-Agent Orchestrator.
"""

import os
import json
import uuid
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.protocol.schema import TelemetryRecord, CanonicalDiagnosticReport
from app.integrations.models import (
    SourceType,
    AuthType,
    ConnectionStatus,
    NetworkSourceConfig,
    NetworkSourcePublic,
    ConnectionTestResult,
    SourceCreateRequest,
    SourceUpdateRequest,
)
from app.integrations.adapters.base import BaseTelemetryAdapter
from app.integrations.adapters.ping_probe import PingProbeAdapter
from app.integrations.adapters.server_metrics import ServerMetricsAdapter
from app.integrations.adapters.rest_adapter import RestApiAdapter
from app.integrations.adapters.snmp_adapter import SnmpAdapter
from app.integrations.adapters.syslog_adapter import SyslogAdapter
from app.integrations.adapters.csv_json_adapter import FileImportAdapter

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "integrations.json"


def _create_default_sources() -> List[NetworkSourceConfig]:
    """
    Seeds initial network source templates.
    Includes active localhost probes and enterprise hardware templates.
    """
    return [
        NetworkSourceConfig(
            id="src-local-ping",
            name="Core Backend Socket Probe",
            source_type=SourceType.PING_PROBE,
            host="127.0.0.1",
            port=8000,
            polling_interval_sec=15,
            timeout_sec=2.0,
            enabled=True,
            status=ConnectionStatus.UNKNOWN,
            metrics_supported=["latency", "jitter", "packet_loss"],
        ),
        NetworkSourceConfig(
            id="src-server-host",
            name="Host Appliance Resource Monitor",
            source_type=SourceType.SERVER_HOST,
            host="127.0.0.1",
            port=80,
            polling_interval_sec=30,
            timeout_sec=2.0,
            enabled=True,
            status=ConnectionStatus.UNKNOWN,
            metrics_supported=["cpu_utilization", "memory_utilization"],
        ),
        NetworkSourceConfig(
            id="src-cisco-restconf",
            name="Cisco IOS-XE Core Router (Template)",
            source_type=SourceType.REST_API,
            host="10.0.0.1",
            port=443,
            endpoint_path="/restconf/data/ietf-interfaces:interfaces-state",
            auth_type=AuthType.BASIC_AUTH,
            username="admin",
            password="",
            polling_interval_sec=30,
            timeout_sec=3.0,
            enabled=False,
            status=ConnectionStatus.DISCONNECTED,
            metrics_supported=["bandwidth_utilization", "queue_drops", "crc_errors"],
        ),
        NetworkSourceConfig(
            id="src-snmp-switch",
            name="Aggregation Switch SNMP Agent (Template)",
            source_type=SourceType.SNMP,
            host="10.0.0.10",
            port=161,
            auth_type=AuthType.COMMUNITY_STRING,
            community_string="public",
            polling_interval_sec=60,
            timeout_sec=2.0,
            enabled=False,
            status=ConnectionStatus.DISCONNECTED,
            metrics_supported=["latency", "crc_errors"],
        ),
        NetworkSourceConfig(
            id="src-syslog-collector",
            name="Central Syslog Ingestion Collector",
            source_type=SourceType.SYSLOG,
            host="127.0.0.1",
            port=514,
            polling_interval_sec=30,
            timeout_sec=1.0,
            enabled=True,
            status=ConnectionStatus.CONNECTED,
            metrics_supported=["interface_flaps", "crc_errors", "cpu_utilization", "queue_drops"],
        ),
    ]


class IntegrationManager:
    """
    Singleton manager for live network sources, health verification, and live diagnosis.
    """

    def __init__(self, storage_path: Path = DATA_FILE):
        self.storage_path = storage_path
        self._sources: Dict[str, NetworkSourceConfig] = {}
        self._adapters: Dict[str, BaseTelemetryAdapter] = {}
        self._load_sources()

    def _load_sources(self) -> None:
        """Loads sources from disk or initializes defaults."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        config = NetworkSourceConfig(**item)
                        self._sources[config.id] = config
                return
            except Exception:
                pass

        # Seed defaults
        defaults = _create_default_sources()
        for src in defaults:
            self._sources[src.id] = src
        self._save_sources()

    def _save_sources(self) -> None:
        """Persists sources to JSON storage."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = [src.model_dump() for src in self._sources.values()]
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def get_adapter(self, config: NetworkSourceConfig) -> BaseTelemetryAdapter:
        """
        Retrieves or creates the appropriate telemetry adapter for the given configuration.
        """
        if config.source_type == SourceType.PING_PROBE:
            return PingProbeAdapter(config)
        elif config.source_type == SourceType.SERVER_HOST:
            return ServerMetricsAdapter(config)
        elif config.source_type == SourceType.REST_API:
            return RestApiAdapter(config)
        elif config.source_type == SourceType.SNMP:
            return SnmpAdapter(config)
        elif config.source_type == SourceType.SYSLOG:
            if config.id not in self._adapters:
                self._adapters[config.id] = SyslogAdapter(config)
            return self._adapters[config.id]
        elif config.source_type in [SourceType.CSV_IMPORT, SourceType.JSON_IMPORT]:
            return FileImportAdapter(config)
        else:
            return PingProbeAdapter(config)

    def list_sources(self) -> List[NetworkSourcePublic]:
        """
        Returns all registered network sources with credentials strictly redacted.
        """
        return [src.to_public() for src in self._sources.values()]

    def get_source(self, source_id: str) -> Optional[NetworkSourceConfig]:
        return self._sources.get(source_id)

    def get_source_public(self, source_id: str) -> Optional[NetworkSourcePublic]:
        src = self._sources.get(source_id)
        return src.to_public() if src else None

    def create_source(self, req: SourceCreateRequest) -> NetworkSourcePublic:
        """
        Registers a new network source.
        """
        source_id = f"src-{uuid.uuid4().hex[:8]}"
        supported = ["latency", "packet_loss"]
        if req.source_type == SourceType.SERVER_HOST:
            supported = ["cpu_utilization", "memory_utilization"]
        elif req.source_type == SourceType.REST_API:
            supported = ["bandwidth_utilization", "queue_drops", "crc_errors", "cpu_utilization"]
        elif req.source_type == SourceType.SNMP:
            supported = ["latency", "crc_errors"]
        elif req.source_type == SourceType.SYSLOG:
            supported = ["interface_flaps", "crc_errors", "cpu_utilization"]

        default_port = 80
        if req.source_type == SourceType.SNMP:
            default_port = 161
        elif req.source_type == SourceType.REST_API:
            default_port = 443
        elif req.source_type == SourceType.SYSLOG:
            default_port = 514

        config = NetworkSourceConfig(
            id=source_id,
            name=req.name,
            source_type=req.source_type,
            host=req.host,
            port=req.port or default_port,
            endpoint_path=req.endpoint_path,
            auth_type=req.auth_type or AuthType.NONE,
            community_string=req.community_string,
            username=req.username,
            password=req.password,
            api_key=req.api_key,
            bearer_token=req.bearer_token,
            polling_interval_sec=req.polling_interval_sec or 30,
            timeout_sec=req.timeout_sec or 3.0,
            enabled=req.enabled if req.enabled is not None else True,
            metrics_supported=supported,
        )
        self._sources[source_id] = config
        self._save_sources()
        return config.to_public()

    def update_source(self, source_id: str, req: SourceUpdateRequest) -> Optional[NetworkSourcePublic]:
        """
        Updates an existing network source.
        """
        src = self._sources.get(source_id)
        if not src:
            return None

        if req.name is not None:
            src.name = req.name
        if req.host is not None:
            src.host = req.host
        if req.port is not None:
            src.port = req.port
        if req.endpoint_path is not None:
            src.endpoint_path = req.endpoint_path
        if req.auth_type is not None:
            src.auth_type = req.auth_type
        if req.community_string is not None:
            src.community_string = req.community_string
        if req.username is not None:
            src.username = req.username
        if req.password is not None:
            src.password = req.password
        if req.api_key is not None:
            src.api_key = req.api_key
        if req.bearer_token is not None:
            src.bearer_token = req.bearer_token
        if req.polling_interval_sec is not None:
            src.polling_interval_sec = req.polling_interval_sec
        if req.timeout_sec is not None:
            src.timeout_sec = req.timeout_sec
        if req.enabled is not None:
            src.enabled = req.enabled

        self._save_sources()
        return src.to_public()

    def delete_source(self, source_id: str) -> bool:
        """
        Removes a source from the registry.
        """
        if source_id in self._sources:
            del self._sources[source_id]
            if source_id in self._adapters:
                del self._adapters[source_id]
            self._save_sources()
            return True
        return False

    async def test_connection(self, source_id: str) -> ConnectionTestResult:
        """
        Executes a real probe for the specified source and records health.
        """
        src = self._sources.get(source_id)
        if not src:
            return ConnectionTestResult(
                source_id=source_id,
                source_name="Unknown",
                source_type=SourceType.PING_PROBE,
                success=False,
                status=ConnectionStatus.ERROR,
                message=f"Source ID '{source_id}' does not exist.",
            )

        adapter = self.get_adapter(src)
        result = await adapter.test_connection()

        # Update persisted state
        src.status = result.status
        src.last_tested_at = result.tested_at
        src.last_error = None if result.success else result.message
        self._save_sources()

        return result

    async def poll_source(self, source_id: str) -> List[TelemetryRecord]:
        """
        Collects real live telemetry from the specified source.
        """
        src = self._sources.get(source_id)
        if not src:
            return []

        adapter = self.get_adapter(src)
        records = await adapter.collect_telemetry()

        src.last_polled_at = datetime.now(timezone.utc).isoformat()
        if records:
            src.status = ConnectionStatus.CONNECTED
        self._save_sources()

        return records

    def ingest_syslog(self, messages: List[str], device_id: Optional[str] = None) -> int:
        """
        Ingests syslog messages into the active syslog adapter.
        """
        syslog_src = next(
            (s for s in self._sources.values() if s.source_type == SourceType.SYSLOG and s.enabled),
            None,
        )
        if not syslog_src:
            return 0

        adapter = self.get_adapter(syslog_src)
        if isinstance(adapter, SyslogAdapter):
            for m in messages:
                adapter.ingest_message(m)
            return len(messages)
        return 0

    async def run_live_diagnosis(
        self,
        source_ids: Optional[List[str]] = None,
        timeout_sec: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Polls active live network sources concurrently, compiles genuine telemetry,
        and feeds it into the multi-agent diagnostic engine.
        """
        # Determine targets
        if source_ids:
            targets = [self._sources[s] for s in source_ids if s in self._sources]
        else:
            targets = [s for s in self._sources.values() if s.enabled]

        if not targets:
            return {
                "success": False,
                "error": "No active live network sources are configured or enabled.",
                "telemetry_origin": "SIMULATED",
                "sources_polled": [],
                "records_collected": 0,
                "report": None,
            }

        # Poll all targets concurrently with timeout
        async def poll_single(src: NetworkSourceConfig) -> List[TelemetryRecord]:
            try:
                return await asyncio.wait_for(self.poll_source(src.id), timeout=timeout_sec)
            except Exception:
                return []

        results = await asyncio.gather(*[poll_single(src) for src in targets])
        all_records: List[TelemetryRecord] = []
        sources_polled: List[str] = []

        for src, recs in zip(targets, results):
            sources_polled.append(src.name)
            all_records.extend(recs)

        if not all_records:
            return {
                "success": False,
                "error": "No live telemetry could be gathered from connected sources. Verify device reachability.",
                "telemetry_origin": "SIMULATED",
                "sources_polled": sources_polled,
                "records_collected": 0,
                "report": None,
            }

        # Run MultiAgentOrchestrator
        from app.orchestrator.engine import MultiAgentOrchestrator
        orchestrator = MultiAgentOrchestrator()

        incident_id = f"INC-LIVE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        diag_res = orchestrator.run_diagnosis(
            telemetry=all_records,
            incident_id=incident_id,
            scenario_id="live_network",
        )

        canon = diag_res.get("canonical_report", {})
        return {
            "success": True,
            "incident_id": incident_id,
            "telemetry_origin": canon.get("telemetry_origin", "LIVE"),
            "sources_polled": sources_polled,
            "records_collected": len(all_records),
            "telemetry_sample": [r.model_dump() for r in all_records[:10]],
            "report": canon,
            "investigation_result": diag_res,
        }


# Singleton instance
_integration_manager = IntegrationManager()


def get_integration_manager() -> IntegrationManager:
    return _integration_manager
