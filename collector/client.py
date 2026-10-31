"""
Outbound Backend Client for Collector.
Connects outbound to NetCoop AI Cloud Backend via HTTPS.
Does NOT require any inbound ports on the router/firewall.
"""

import socket
import platform
import httpx
from typing import List, Dict, Any, Optional

from collector.schema import TelemetryRecord
from collector.config import detect_default_gateway


class CollectorBackendClient:
    """
    Handles secure outbound communication from local collector to deployed backend.
    """

    def __init__(self, backend_url: str):
        self.backend_url = backend_url.rstrip("/")

    async def register(self, collector_id: str, enrollment_token: str) -> Dict[str, Any]:
        """
        Pairs collector with cloud backend using enrollment token.
        Returns session_token.
        """
        local_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass

        gateway_ip = detect_default_gateway()

        payload = {
            "collector_id": collector_id,
            "enrollment_token": enrollment_token,
            "hostname": platform.node() or "Collector-Host",
            "local_ip": local_ip,
            "os_type": f"{platform.system()} {platform.release()}",
            "collector_version": "1.0.0",
            "default_gateway": gateway_ip,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self.backend_url}/api/collectors/register", json=payload)
            if resp.status_code != 200:
                err = resp.json().get("detail", resp.text)
                raise ConnectionError(f"Pairing failed ({resp.status_code}): {err}")
            return resp.json()

    async def heartbeat(self, collector_id: str, session_token: str, active_devices: int = 0) -> bool:
        """
        Pushes periodic keepalive heartbeat with dynamically detected default gateway.
        """
        gateway_ip = detect_default_gateway()
        payload = {
            "collector_id": collector_id,
            "session_token": session_token,
            "active_device_count": active_devices,
            "default_gateway": gateway_ip,
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{self.backend_url}/api/collectors/heartbeat", json=payload)
            return resp.status_code == 200

    async def fetch_pending_probe_jobs(self, collector_id: str, session_token: str) -> List[Dict[str, Any]]:
        """
        Polls backend for on-demand IP probe jobs dispatched to this collector.
        """
        try:
            headers = {"x-session-token": session_token}
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.backend_url}/api/collectors/{collector_id}/probe-jobs",
                    headers=headers,
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return []

    async def push_probe_job_result(
        self,
        collector_id: str,
        session_token: str,
        job_id: str,
        result_payload: Dict[str, Any],
    ) -> bool:
        """
        Submits the executed on-demand probe result back to the cloud backend.
        """
        try:
            headers = {"x-session-token": session_token}
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    f"{self.backend_url}/api/collectors/{collector_id}/probe-jobs/{job_id}/result",
                    headers=headers,
                    json=result_payload,
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def push_telemetry(
        self,
        collector_id: str,
        session_token: str,
        device_id: str,
        records: List[TelemetryRecord],
        metrics_available: Optional[List[str]] = None,
        metrics_unsupported: Optional[List[str]] = None,
    ) -> bool:
        """
        Streams normalized device telemetry batch up to backend.
        """
        payload = {
            "collector_id": collector_id,
            "session_token": session_token,
            "device_id": device_id,
            "records": [r.model_dump() for r in records],
            "metrics_available": metrics_available or [],
            "metrics_unsupported": metrics_unsupported or [],
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(f"{self.backend_url}/api/collectors/telemetry", json=payload)
            return resp.status_code == 200

    async def fetch_devices(self, collector_id: str) -> List[Dict[str, Any]]:
        """
        Fetches devices registered to this collector from the cloud backend.
        """
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(f"{self.backend_url}/api/collectors/{collector_id}/devices")
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return []
