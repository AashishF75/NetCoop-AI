"""
Collector Hub for NetCoop AI.
Manages collector enrollment, secure session tokens, heartbeats,
device inventories, live telemetry ingestion, and dispatch to MultiAgentOrchestrator.
"""

import os
import json
import uuid
import secrets
import asyncio
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field

from app.protocol.schema import TelemetryRecord, CanonicalDiagnosticReport
from app.integrations.models import validate_target_host

_env_data_dir = os.environ.get("NETCOOP_DATA_DIR")
DATA_DIR = Path(_env_data_dir) if _env_data_dir else Path(__file__).resolve().parent.parent.parent / "data"
COLLECTORS_FILE = DATA_DIR / "collectors.json"
DEVICES_FILE = DATA_DIR / "registered_devices.json"


class CollectorStatus(str, Enum):
    PENDING_PAIRING = "PENDING_PAIRING"
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    REVOKED = "REVOKED"


class DeviceConnectionStatus(str, Enum):
    STREAMING_LIVE = "STREAMING_LIVE"
    STALE_TELEMETRY = "STALE_TELEMETRY"
    CONFIGURED_OFFLINE = "CONFIGURED_OFFLINE"
    UNREACHABLE = "UNREACHABLE"
    AUTH_REJECTED = "AUTH_REJECTED"


class RegisteredDeviceModel(BaseModel):
    device_id: str
    name: str
    device_type: str = "router"
    ip: str
    port: int = 80
    protocol: str = "TCP_PROBE"
    collector_id: str
    status: DeviceConnectionStatus = DeviceConnectionStatus.CONFIGURED_OFFLINE
    last_telemetry_at: Optional[str] = None
    last_error: Optional[str] = None
    metrics_available: List[str] = Field(default_factory=list)
    metrics_unsupported: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CollectorModel(BaseModel):
    collector_id: str
    name: str
    enrollment_token: str
    session_token: Optional[str] = None
    status: CollectorStatus = CollectorStatus.PENDING_PAIRING
    hostname: Optional[str] = None
    local_ip: Optional[str] = None
    default_gateway: Optional[str] = None
    os_type: Optional[str] = None
    collector_version: str = "1.0.0"
    last_heartbeat_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    registered_devices: List[str] = Field(default_factory=list)


class EnrollmentTokenResponse(BaseModel):
    collector_id: str
    name: str
    enrollment_token: str
    expires_at: str
    pairing_command_windows: str
    pairing_command_linux: str


class CollectorRegisterRequest(BaseModel):
    collector_id: str
    enrollment_token: str
    hostname: str
    local_ip: str
    default_gateway: Optional[str] = None
    os_type: str
    collector_version: str = "1.0.0"


class CollectorHeartbeatRequest(BaseModel):
    collector_id: str
    session_token: str
    active_device_count: int = 0
    default_gateway: Optional[str] = None


class TelemetryPushRequest(BaseModel):
    collector_id: str
    session_token: str
    device_id: str
    records: List[TelemetryRecord]
    metrics_available: Optional[List[str]] = None
    metrics_unsupported: Optional[List[str]] = None


class DeviceRegisterRequest(BaseModel):
    device_id: str
    name: str
    device_type: str = "router"
    ip: str
    port: int = 80
    protocol: str = "TCP_PROBE"


class CollectorHub:
    """
    Central hub managing on-premise network collectors and live device inventories.
    """

    def __init__(self, storage_dir: Path = DATA_DIR):
        self.storage_dir = storage_dir
        self.collectors_file = storage_dir / "collectors.json"
        self.devices_file = storage_dir / "registered_devices.json"

        self._collectors: Dict[str, CollectorModel] = {}
        self._devices: Dict[str, RegisteredDeviceModel] = {}
        self._telemetry_cache: Dict[str, List[TelemetryRecord]] = {}
        self._pending_probe_jobs: Dict[str, List[Dict[str, Any]]] = {}
        self._completed_probe_jobs: Dict[str, Dict[str, Any]] = {}
        self._probe_job_events: Dict[str, asyncio.Event] = {}

        self._load_state()

    def _load_state(self) -> None:
        """Loads collectors and devices from persistent JSON storage."""
        if self.collectors_file.exists():
            try:
                with open(self.collectors_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        c = CollectorModel(**item)
                        self._collectors[c.collector_id] = c
            except Exception:
                pass

        if self.devices_file.exists():
            try:
                with open(self.devices_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        d = RegisteredDeviceModel(**item)
                        self._devices[d.device_id] = d
            except Exception:
                pass

    def _save_state(self) -> None:
        """Persists collectors and registered devices to disk."""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            with open(self.collectors_file, "w", encoding="utf-8") as f:
                json.dump([c.model_dump() for c in self._collectors.values()], f, indent=2)
            with open(self.devices_file, "w", encoding="utf-8") as f:
                json.dump([d.model_dump() for d in self._devices.values()], f, indent=2)
        except Exception:
            pass

    def create_enrollment(self, name: str, backend_base_url: str = "http://127.0.0.1:8000") -> EnrollmentTokenResponse:
        """
        Generates a secure cryptographic enrollment token for pairing a collector.
        """
        collector_id = f"col-{uuid.uuid4().hex[:6]}"
        token = f"nc_coll_{secrets.token_urlsafe(24)}"
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

        collector = CollectorModel(
            collector_id=collector_id,
            name=name.strip() or f"Collector-{collector_id}",
            enrollment_token=token,
            status=CollectorStatus.PENDING_PAIRING,
        )
        self._collectors[collector_id] = collector
        self._save_state()

        clean_backend = backend_base_url.rstrip("/")
        cmd_win = f"python -m collector.run --backend {clean_backend} --token {token}"
        cmd_linux = f"python3 -m collector.run --backend {clean_backend} --token {token}"

        return EnrollmentTokenResponse(
            collector_id=collector_id,
            name=collector.name,
            enrollment_token=token,
            expires_at=expires_at,
            pairing_command_windows=cmd_win,
            pairing_command_linux=cmd_linux,
        )

    def register_collector(self, req: CollectorRegisterRequest) -> Dict[str, Any]:
        """
        Validates enrollment token and establishes session credentials for the collector.
        """
        collector = self._collectors.get(req.collector_id)
        if not collector:
            # Fallback: locate collector by unique enrollment token
            for c in self._collectors.values():
                if c.enrollment_token == req.enrollment_token:
                    collector = c
                    break
        if not collector:
            raise ValueError(f"Unknown collector ID: '{req.collector_id}'")

        if collector.status == CollectorStatus.REVOKED:
            raise PermissionError("This collector has been revoked by NOC administrators.")

        if collector.enrollment_token != req.enrollment_token:
            raise PermissionError("Invalid enrollment token.")

        # Generate secure session token for subsequent authenticated requests
        session_token = f"nc_sess_{secrets.token_urlsafe(32)}"
        collector.session_token = session_token
        collector.status = CollectorStatus.ONLINE
        collector.hostname = req.hostname
        collector.local_ip = req.local_ip
        if req.default_gateway:
            collector.default_gateway = req.default_gateway
        collector.os_type = req.os_type
        collector.collector_version = req.collector_version
        collector.last_heartbeat_at = datetime.now(timezone.utc).isoformat()

        self._save_state()

        return {
            "success": True,
            "collector_id": collector.collector_id,
            "session_token": session_token,
            "heartbeat_interval_sec": 15,
            "message": "Collector successfully paired and authenticated.",
        }

    def heartbeat(self, req: CollectorHeartbeatRequest) -> Dict[str, Any]:
        """
        Receives periodic heartbeat and updates live status.
        """
        collector = self._collectors.get(req.collector_id)
        if not collector:
            raise ValueError("Unknown collector")

        if collector.status == CollectorStatus.REVOKED:
            raise PermissionError("Collector revoked.")

        if not collector.session_token or collector.session_token != req.session_token:
            raise PermissionError("Invalid session token. Re-authentication required.")

        collector.status = CollectorStatus.ONLINE
        if req.default_gateway:
            collector.default_gateway = req.default_gateway
        collector.last_heartbeat_at = datetime.now(timezone.utc).isoformat()
        self._save_state()

        return {"status": "ACK", "server_time": datetime.now(timezone.utc).isoformat()}

    def list_online_collectors(self) -> List[CollectorModel]:
        """Returns all enrolled collectors that are currently ONLINE, sorted by most recent activity."""
        online = [c for c in self.list_collectors() if c.status == CollectorStatus.ONLINE]
        return sorted(online, key=lambda c: c.last_heartbeat_at or "", reverse=True)

    def get_active_default_gateway(self) -> str:
        """
        Returns dynamically detected default gateway from the online collector,
        or dynamically discovers from local network stack.
        """
        for c in self.list_online_collectors():
            if c.default_gateway:
                return c.default_gateway
        from collector.config import detect_default_gateway
        gw = detect_default_gateway()
        return gw or "127.0.0.1"

    def queue_probe_job(self, collector_id: str, job_data: Dict[str, Any]) -> str:
        """
        Queues an on-demand probe job for an online local collector to execute inside LAN.
        """
        collector = self._collectors.get(collector_id)
        if not collector:
            raise ValueError(f"Unknown collector '{collector_id}'")

        job_id = job_data.get("job_id") or f"job-{uuid.uuid4().hex[:8]}"
        job_data["job_id"] = job_id
        job_data["queued_at"] = datetime.now(timezone.utc).isoformat()

        if collector_id not in self._pending_probe_jobs:
            self._pending_probe_jobs[collector_id] = []
        self._pending_probe_jobs[collector_id].append(job_data)
        self._probe_job_events[job_id] = asyncio.Event()
        return job_id

    def get_pending_probe_jobs(self, collector_id: str, session_token: str) -> List[Dict[str, Any]]:
        """
        Retrieves and clears pending probe jobs for an authenticated collector.
        """
        collector = self._collectors.get(collector_id)
        if not collector or collector.session_token != session_token:
            raise PermissionError("Invalid session token.")
        jobs = self._pending_probe_jobs.pop(collector_id, [])
        return jobs

    def submit_probe_job_result(self, collector_id: str, session_token: str, job_id: str, result: Dict[str, Any]) -> bool:
        """
        Receives probe execution results from the on-premise collector.
        """
        collector = self._collectors.get(collector_id)
        if not collector or collector.session_token != session_token:
            raise PermissionError("Invalid session token.")
        self._completed_probe_jobs[job_id] = result
        evt = self._probe_job_events.get(job_id)
        if evt:
            evt.set()
        return True

    async def await_probe_job_result(self, job_id: str, timeout_sec: float = 6.0) -> Optional[Dict[str, Any]]:
        """
        Awaits completion of a probe job dispatched to a local collector.
        """
        evt = self._probe_job_events.get(job_id)
        if not evt:
            return self._completed_probe_jobs.get(job_id)
        try:
            await asyncio.wait_for(evt.wait(), timeout=timeout_sec)
            return self._completed_probe_jobs.get(job_id)
        except asyncio.TimeoutError:
            return None
        finally:
            self._probe_job_events.pop(job_id, None)

    def revoke_collector(self, collector_id: str) -> bool:
        """
        Revokes a collector immediately, invalidating its session token.
        """
        collector = self._collectors.get(collector_id)
        if not collector:
            return False

        collector.status = CollectorStatus.REVOKED
        collector.session_token = None
        self._save_state()
        return True

    def list_collectors(self) -> List[CollectorModel]:
        """
        Lists all enrolled collectors, dynamically evaluating heartbeat timeouts.
        """
        now = datetime.now(timezone.utc)
        for c in self._collectors.values():
            if c.status == CollectorStatus.ONLINE and c.last_heartbeat_at:
                try:
                    last_hb = datetime.fromisoformat(c.last_heartbeat_at)
                    if (now - last_hb).total_seconds() > 45:
                        c.status = CollectorStatus.OFFLINE
                except Exception:
                    pass
        return list(self._collectors.values())

    def get_collector(self, collector_id: str) -> Optional[CollectorModel]:
        return self._collectors.get(collector_id)

    def register_device(self, collector_id: str, req: DeviceRegisterRequest) -> RegisteredDeviceModel:
        """
        Registers an allowable target device on a collector.
        Enforces strict anti-scanning IP validation (no CIDR subnet masks).
        """
        collector = self._collectors.get(collector_id)
        if not collector:
            raise ValueError(f"Collector '{collector_id}' not found.")

        clean_ip = validate_target_host(req.ip)

        device = RegisteredDeviceModel(
            device_id=req.device_id.strip(),
            name=req.name.strip() or req.device_id.strip(),
            device_type=req.device_type,
            ip=clean_ip,
            port=req.port,
            protocol=req.protocol,
            collector_id=collector_id,
            status=DeviceConnectionStatus.CONFIGURED_OFFLINE,
        )

        self._devices[device.device_id] = device
        if device.device_id not in collector.registered_devices:
            collector.registered_devices.append(device.device_id)

        self._save_state()
        return device

    def list_devices(self, collector_id: Optional[str] = None) -> List[RegisteredDeviceModel]:
        """
        Lists registered devices, updating stale flags if telemetry is older than 5 minutes.
        """
        now = datetime.now(timezone.utc)
        devices = (
            [d for d in self._devices.values() if d.collector_id == collector_id]
            if collector_id
            else list(self._devices.values())
        )

        for d in devices:
            if d.last_telemetry_at:
                try:
                    dt = datetime.fromisoformat(d.last_telemetry_at)
                    if (now - dt).total_seconds() > 300:
                        d.status = DeviceConnectionStatus.STALE_TELEMETRY
                except Exception:
                    pass

        return devices

    def delete_device(self, device_id: str) -> bool:
        """
        Removes a registered device.
        """
        if device_id in self._devices:
            dev = self._devices.pop(device_id)
            if dev.collector_id in self._collectors:
                col = self._collectors[dev.collector_id]
                if device_id in col.registered_devices:
                    col.registered_devices.remove(device_id)
            if device_id in self._telemetry_cache:
                del self._telemetry_cache[device_id]
            self._save_state()
            return True
        return False

    def ingest_telemetry(self, req: TelemetryPushRequest) -> int:
        """
        Ingests a batch of live telemetry records collected from an internal network device.
        """
        collector = self._collectors.get(req.collector_id)
        if not collector:
            raise ValueError(f"Unknown collector '{req.collector_id}'.")

        if collector.status == CollectorStatus.REVOKED:
            raise PermissionError("Collector revoked.")

        if not collector.session_token or collector.session_token != req.session_token:
            raise PermissionError("Invalid session token.")

        device = self._devices.get(req.device_id)
        if not device:
            # Register device on the fly if not explicitly registered yet
            device = RegisteredDeviceModel(
                device_id=req.device_id,
                name=req.device_id,
                ip=collector.local_ip or "127.0.0.1",
                collector_id=req.collector_id,
            )
            self._devices[device.device_id] = device
            if device.device_id not in collector.registered_devices:
                collector.registered_devices.append(device.device_id)

        now_iso = datetime.now(timezone.utc).isoformat()
        device.last_telemetry_at = now_iso
        device.status = DeviceConnectionStatus.STREAMING_LIVE

        if req.metrics_available:
            device.metrics_available = req.metrics_available
        if req.metrics_unsupported:
            device.metrics_unsupported = req.metrics_unsupported

        # Tag each record with appropriate live provenance (LIVE_HOST vs LIVE_DEVICE)
        for r in req.records:
            if getattr(r, "telemetry_origin", None) in ("LIVE_HOST", "LIVE_DEVICE"):
                pass  # Preserve genuine provenance
            elif getattr(device, "protocol", "") == "HOST_METRICS" or getattr(device, "device_type", "") == "server":
                r.telemetry_origin = "LIVE_HOST"
            else:
                r.telemetry_origin = "LIVE_DEVICE"
            r.source_id = f"col:{req.collector_id}:dev:{req.device_id}"

        self._telemetry_cache[req.device_id] = req.records
        self._save_state()

        return len(req.records)

    def get_live_telemetry_snapshot(self, max_age_seconds: int = 300) -> Tuple[List[TelemetryRecord], List[str]]:
        """
        Retrieves active live telemetry records from registered devices.
        Filters out stale telemetry.
        """
        now = datetime.now(timezone.utc)
        valid_records: List[TelemetryRecord] = []
        stale_devices: List[str] = []

        for dev_id, records in self._telemetry_cache.items():
            dev = self._devices.get(dev_id)
            if not dev or not dev.last_telemetry_at:
                continue

            try:
                last_time = datetime.fromisoformat(dev.last_telemetry_at)
                age = (now - last_time).total_seconds()
                if age <= max_age_seconds:
                    valid_records.extend(records)
                else:
                    stale_devices.append(dev.name or dev_id)
            except Exception:
                pass

        return valid_records, stale_devices

    def diagnose_live_devices(self) -> Dict[str, Any]:
        """
        Pulls real live telemetry from registered collector devices and feeds it
        into the MultiAgentOrchestrator.
        Guarantees NO synthetic fallback: if no telemetry is present or data is stale,
        returns an honest structured error.
        """
        valid_records, stale_devices = self.get_live_telemetry_snapshot(max_age_seconds=300)

        if not valid_records:
            if stale_devices:
                msg = f"Collector telemetry from {', '.join(stale_devices)} is stale (> 5 minutes old). Polling must be active."
            else:
                msg = "No live network telemetry received. Please pair a network collector agent and register target devices."

            return {
                "success": False,
                "error": msg,
                "telemetry_origin": "LIVE_DEVICE",
                "devices_polled": [],
                "records_collected": 0,
                "report": None,
            }

        # Run multi-agent diagnosis over genuine records
        from app.orchestrator.engine import MultiAgentOrchestrator
        orchestrator = MultiAgentOrchestrator()

        incident_id = f"INC-LIVE-DEV-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        diag_res = orchestrator.run_diagnosis(
            telemetry=valid_records,
            incident_id=incident_id,
            scenario_id="live_network_devices",
        )

        canon = diag_res.get("canonical_report", {})
        devices_polled = list({r.device_id for r in valid_records})

        return {
            "success": True,
            "incident_id": incident_id,
            "telemetry_origin": canon.get("telemetry_origin", "LIVE_DEVICE"),
            "devices_polled": devices_polled,
            "records_collected": len(valid_records),
            "stale_devices_ignored": stale_devices,
            "telemetry_sample": [r.model_dump() for r in valid_records[:10]],
            "report": canon,
            "investigation_result": diag_res,
        }


# Singleton instance
collector_hub = CollectorHub()


def get_collector_hub() -> CollectorHub:
    return collector_hub

