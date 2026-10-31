"""
RESTCONF & Network Device REST API Telemetry Adapter.
Integrates with Cisco IOS-XE RESTCONF, OpenConfig, Arista eAPI, and custom network REST endpoints.
"""

import time
from typing import List, Dict, Any, Optional
import httpx

from app.protocol.schema import TelemetryRecord
from app.integrations.models import (
    NetworkSourceConfig,
    ConnectionTestResult,
    ConnectionStatus,
    AuthType,
)
from app.integrations.adapters.base import BaseTelemetryAdapter


class RestApiAdapter(BaseTelemetryAdapter):
    """
    Adapter for querying RESTCONF or HTTP/JSON network device endpoints.
    """

    def _build_url(self) -> str:
        protocol = "https" if self.config.port in [443, 8443] else "http"
        host = self.config.host
        port = f":{self.config.port}" if self.config.port not in [80, 443] else ""
        path = self.config.endpoint_path or ""
        if path and not path.startswith("/"):
            path = "/" + path
        return f"{protocol}://{host}{port}{path}"

    def _build_client_kwargs(self) -> Dict[str, Any]:
        headers = {
            "Accept": "application/yang-data+json, application/json",
            "User-Agent": "NetCoopAI-Integration-Agent/2.0",
        }
        kwargs: Dict[str, Any] = {
            "headers": headers,
            "timeout": max(self.config.timeout_sec, 1.0),
            "verify": False,  # Common in internal lab / router self-signed certs
        }

        if self.config.auth_type == AuthType.BEARER_TOKEN and self.config.bearer_token:
            headers["Authorization"] = f"Bearer {self.config.bearer_token}"
        elif self.config.auth_type == AuthType.API_KEY and self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        elif self.config.auth_type == AuthType.BASIC_AUTH and self.config.username:
            kwargs["auth"] = (self.config.username, self.config.password or "")

        return kwargs

    async def test_connection(self) -> ConnectionTestResult:
        """
        Tests reachability of the RESTCONF / HTTP endpoint.
        """
        url = self._build_url()
        kwargs = self._build_client_kwargs()
        t0 = time.perf_counter()

        try:
            async with httpx.AsyncClient(**kwargs) as client:
                resp = await client.get(url)
                lat = (time.perf_counter() - t0) * 1000.0

                if resp.status_code in [200, 201, 204]:
                    return ConnectionTestResult(
                        source_id=self.config.id,
                        source_name=self.config.name,
                        source_type=self.config.source_type,
                        success=True,
                        status=ConnectionStatus.CONNECTED,
                        latency_ms=round(lat, 2),
                        message=f"REST endpoint responded HTTP {resp.status_code} in {lat:.1f}ms.",
                        details={"status_code": resp.status_code, "url": url},
                    )
                elif resp.status_code in [401, 403]:
                    return ConnectionTestResult(
                        source_id=self.config.id,
                        source_name=self.config.name,
                        source_type=self.config.source_type,
                        success=False,
                        status=ConnectionStatus.ERROR,
                        latency_ms=round(lat, 2),
                        message=f"Authentication required or denied (HTTP {resp.status_code}). Verify credentials.",
                        details={"status_code": resp.status_code},
                    )
                else:
                    return ConnectionTestResult(
                        source_id=self.config.id,
                        source_name=self.config.name,
                        source_type=self.config.source_type,
                        success=False,
                        status=ConnectionStatus.DEGRADED,
                        latency_ms=round(lat, 2),
                        message=f"Endpoint returned unexpected HTTP status {resp.status_code}.",
                        details={"status_code": resp.status_code},
                    )
        except httpx.ConnectError as e:
            return ConnectionTestResult(
                source_id=self.config.id,
                source_name=self.config.name,
                source_type=self.config.source_type,
                success=False,
                status=ConnectionStatus.DISCONNECTED,
                message=f"Cannot reach REST target {url}: Connection refused or unreachable.",
            )
        except httpx.TimeoutException:
            return ConnectionTestResult(
                source_id=self.config.id,
                source_name=self.config.name,
                source_type=self.config.source_type,
                success=False,
                status=ConnectionStatus.DISCONNECTED,
                message=f"Connection to {url} timed out after {self.config.timeout_sec}s.",
            )
        except Exception as e:
            return ConnectionTestResult(
                source_id=self.config.id,
                source_name=self.config.name,
                source_type=self.config.source_type,
                success=False,
                status=ConnectionStatus.ERROR,
                message=f"REST query failed: {type(e).__name__}: {str(e)}",
            )

    async def collect_telemetry(self) -> List[TelemetryRecord]:
        """
        Fetches live JSON data from RESTCONF / REST endpoint and parses into TelemetryRecord items.
        """
        url = self._build_url()
        kwargs = self._build_client_kwargs()
        device_id = self.config.name or self.config.host
        records: List[TelemetryRecord] = []

        try:
            async with httpx.AsyncClient(**kwargs) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return records
                data = resp.json()

                # Recursive search or dictionary extraction of common telemetry fields
                records.extend(self._extract_metrics(data, device_id))
        except Exception:
            pass

        return records

    def _extract_metrics(self, data: Any, device_id: str) -> List[TelemetryRecord]:
        """
        Extracts metrics from standard YANG / RESTCONF or flat JSON telemetry structures.
        """
        records: List[TelemetryRecord] = []
        if isinstance(data, list):
            for item in data:
                records.extend(self._extract_metrics(item, device_id))
            return records

        if not isinstance(data, dict):
            return records

        # Direct schema match if data is already a list of telemetry records
        if "metric" in data and "value" in data:
            try:
                records.append(
                    self.build_record(
                        metric=str(data["metric"]),
                        value=float(data["value"]),
                        unit=str(data.get("unit", "")),
                        device_id=str(data.get("device_id", device_id)),
                        interface_id=data.get("interface_id"),
                    )
                )
                return records
            except (ValueError, TypeError):
                pass

        # Parse RESTCONF ietf-interfaces or device state fields
        for k, v in data.items():
            k_lower = k.lower().replace("-", "_")
            if isinstance(v, (int, float)):
                if "cpu" in k_lower:
                    records.append(self.build_record("cpu_utilization", float(v), "%", device_id))
                elif "loss" in k_lower:
                    records.append(self.build_record("packet_loss", float(v), "%", device_id))
                elif "latency" in k_lower or "rtt" in k_lower:
                    records.append(self.build_record("latency", float(v), "ms", device_id))
                elif "drop" in k_lower or "queue_drop" in k_lower:
                    records.append(self.build_record("queue_drops", float(v), "packets", device_id))
                elif "crc" in k_lower or "error" in k_lower:
                    records.append(self.build_record("crc_errors", float(v), "errors", device_id))
                elif "bandwidth" in k_lower or "utilization" in k_lower:
                    records.append(self.build_record("bandwidth_utilization", float(v), "%", device_id))
            elif isinstance(v, dict):
                records.extend(self._extract_metrics(v, device_id))
            elif isinstance(v, list):
                for item in v:
                    records.extend(self._extract_metrics(item, device_id))

        return records

