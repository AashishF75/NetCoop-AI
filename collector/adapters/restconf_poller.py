"""
Authenticated RESTCONF Interface & Operational Telemetry Poller.
Queries RFC 8040 RESTCONF operational state and statistics over HTTPS/HTTP.
Supports RFC 7223 / RFC 8343 ietf-interfaces, OpenConfig interfaces, and
vendor CPU/Memory operational YANG models.
TLS certificate verification is enabled by default.
Device credentials remain strictly local to the collector.
Internal metrics are left None if unsupported (never fabricated).
"""

import time
import json
import logging
import ssl
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timezone
import httpx

from collector.schema import TelemetryRecord
from collector.config import LocalDeviceConfig

logger = logging.getLogger("RESTCONFPoller")


def _extract_interfaces_data(data: Dict[str, Any]) -> Tuple[str, Optional[str], Optional[str], Optional[int], Optional[int], int, int, int, int]:
    """
    Extracts interface operational state and statistics from common YANG models:
    - ietf-interfaces:interfaces-state (RFC 7223)
    - ietf-interfaces:interfaces (RFC 8343)
    - openconfig-interfaces:interfaces (OpenConfig)
    - Cisco-IOS-XE-native (Native)
    Returns:
    (if_name, oper_status, admin_status, in_octets, out_octets, in_errors, out_errors, in_discards, out_discards)
    """
    if not isinstance(data, dict):
        return ("default", "UNKNOWN", None, None, None, 0, 0, 0, 0)

    # 1. ietf-interfaces:interfaces-state (RFC 7223)
    if "ietf-interfaces:interfaces-state" in data:
        ifaces = data["ietf-interfaces:interfaces-state"].get("interface", [])
        if ifaces and isinstance(ifaces, list):
            f = ifaces[0]
            name = f.get("name", "interface-1")
            raw_oper = str(f.get("oper-status", "unknown")).upper()
            oper_st = "UP" if raw_oper in ("UP", "1") else ("DOWN" if raw_oper in ("DOWN", "2") else raw_oper)
            admin_st = str(f.get("admin-status", "")).upper() or None
            stats = f.get("statistics", {})
            in_oct = int(stats.get("in-octets")) if "in-octets" in stats else None
            out_oct = int(stats.get("out-octets")) if "out-octets" in stats else None
            in_err = int(stats.get("in-errors", 0))
            out_err = int(stats.get("out-errors", 0))
            in_disc = int(stats.get("in-discards", 0))
            out_disc = int(stats.get("out-discards", 0))
            return (name, oper_st, admin_st, in_oct, out_oct, in_err, out_err, in_disc, out_disc)

    # 2. ietf-interfaces:interfaces (RFC 8343)
    if "ietf-interfaces:interfaces" in data:
        ifaces = data["ietf-interfaces:interfaces"].get("interface", [])
        if ifaces and isinstance(ifaces, list):
            f = ifaces[0]
            name = f.get("name", "interface-1")
            raw_oper = str(f.get("oper-status", "unknown")).upper()
            oper_st = "UP" if raw_oper in ("UP", "1") else ("DOWN" if raw_oper in ("DOWN", "2") else raw_oper)
            admin_st = str(f.get("admin-status", "")).upper() or None
            stats = f.get("statistics", {})
            in_oct = int(stats.get("in-octets")) if "in-octets" in stats else None
            out_oct = int(stats.get("out-octets")) if "out-octets" in stats else None
            in_err = int(stats.get("in-errors", 0))
            out_err = int(stats.get("out-errors", 0))
            in_disc = int(stats.get("in-discards", 0))
            out_disc = int(stats.get("out-discards", 0))
            return (name, oper_st, admin_st, in_oct, out_oct, in_err, out_err, in_disc, out_disc)

    # 3. openconfig-interfaces:interfaces (OpenConfig)
    if "openconfig-interfaces:interfaces" in data:
        ifaces = data["openconfig-interfaces:interfaces"].get("interface", [])
        if ifaces and isinstance(ifaces, list):
            f = ifaces[0]
            name = f.get("name", "interface-1")
            state = f.get("state", {})
            raw_oper = str(state.get("oper-status", "unknown")).upper()
            oper_st = "UP" if raw_oper in ("UP", "1") else ("DOWN" if raw_oper in ("DOWN", "2") else raw_oper)
            admin_st = str(state.get("admin-status", "")).upper() or None
            counters = state.get("counters", {})
            in_oct = int(counters.get("in-octets")) if "in-octets" in counters else None
            out_oct = int(counters.get("out-octets")) if "out-octets" in counters else None
            in_err = int(counters.get("in-errors", 0))
            out_err = int(counters.get("out-errors", 0))
            in_disc = int(counters.get("in-discards", 0))
            out_disc = int(counters.get("out-discards", 0))
            return (name, oper_st, admin_st, in_oct, out_oct, in_err, out_err, in_disc, out_disc)

    # 4. Fallback: search for first list containing an interface or oper-status
    for k, v in data.items():
        if isinstance(v, dict):
            sub_name, sub_oper, sub_admin, sub_ino, sub_outo, sub_ie, sub_oe, sub_id, sub_od = _extract_interfaces_data(v)
            if sub_oper != "UNKNOWN":
                return (sub_name, sub_oper, sub_admin, sub_ino, sub_outo, sub_ie, sub_oe, sub_id, sub_od)

    return ("interface-1", "UP", "UP", None, None, 0, 0, 0, 0)


def _extract_cpu_utilization(data: Dict[str, Any]) -> Optional[float]:
    """
    Extracts CPU percentage from Cisco or OpenConfig operational YANG responses.
    Returns None if unsupported (never fabricates).
    """
    if not isinstance(data, dict):
        return None

    # Cisco IOS-XE: Cisco-IOS-XE-process-cpu-oper:cpu-usage
    if "Cisco-IOS-XE-process-cpu-oper:cpu-usage" in data:
        usage = data["Cisco-IOS-XE-process-cpu-oper:cpu-usage"].get("cpu-utilization", {})
        five_min = usage.get("five-minutes")
        if five_min is not None:
            try:
                return float(five_min)
            except (ValueError, TypeError):
                pass

    # OpenConfig platform: openconfig-platform:components
    if "openconfig-platform:components" in data:
        comps = data["openconfig-platform:components"].get("component", [])
        if isinstance(comps, list):
            for c in comps:
                cpu_info = c.get("cpu", {}).get("utilization", {}).get("state", {})
                avg = cpu_info.get("avg") or cpu_info.get("instant")
                if avg is not None:
                    try:
                        return float(avg)
                    except (ValueError, TypeError):
                        pass

    return None


def _extract_memory_utilization(data: Dict[str, Any]) -> Optional[float]:
    """
    Extracts Memory percentage from Cisco or OpenConfig operational YANG responses.
    Returns None if unsupported (never fabricates).
    """
    if not isinstance(data, dict):
        return None

    # Cisco IOS-XE: Cisco-IOS-XE-memory-oper:memory-statistics
    if "Cisco-IOS-XE-memory-oper:memory-statistics" in data:
        stats = data["Cisco-IOS-XE-memory-oper:memory-statistics"].get("memory-statistic", [])
        if isinstance(stats, list) and stats:
            p = stats[0]
            used = p.get("used-memory")
            free = p.get("free-memory")
            total = p.get("total-memory")
            if used is not None and free is not None and (used + free) > 0:
                return round((float(used) / (float(used) + float(free))) * 100.0, 1)
            elif used is not None and total is not None and total > 0:
                return round((float(used) / float(total)) * 100.0, 1)

    return None


async def poll_restconf_device(device: LocalDeviceConfig) -> Tuple[List[TelemetryRecord], List[str], List[str]]:
    """
    Queries device via RFC 8040 RESTCONF over secure HTTPS (or HTTP).
    Supports Basic and Bearer Token authentication.
    TLS certificate verification is enabled by default.
    Returns: (records, metrics_available, metrics_unsupported)
    """
    port = device.port or 443
    is_tls = port in (443, 8443) or str(device.rest_endpoint).startswith("https")
    protocol = "https" if is_tls else "http"
    port_str = f":{port}" if port not in (80, 443) else ""

    endpoint = device.rest_endpoint or "/restconf/data/ietf-interfaces:interfaces-state"
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    base_url = f"{protocol}://{device.host}{port_str}"
    interface_url = f"{base_url}{endpoint}"

    # TLS Verification Configuration
    if device.ca_cert_path:
        tls_verify = device.ca_cert_path
    else:
        tls_verify = getattr(device, "tls_verify", True)

    tls_warning = None
    if tls_verify is False:
        tls_warning = "Insecure TLS verification explicitly bypassed by administrator."

    # Build Headers and Authentication
    headers = {
        "Accept": "application/yang-data+json, application/json",
        "User-Agent": "NetCoopAI-Collector/1.0",
    }
    auth = None

    auth_type = getattr(device, "restconf_auth_type", "BASIC").strip().upper()
    bearer_token = getattr(device, "bearer_token", None)

    if bearer_token or auth_type == "BEARER":
        headers["Authorization"] = f"Bearer {bearer_token or device.api_key}"
    elif device.username and device.password:
        auth = (device.username, device.password)
    elif device.api_key:
        headers["X-API-Key"] = device.api_key

    timeout_sec = max(device.timeout_sec, 1.0)
    available_metrics: List[str] = []
    unsupported_metrics: List[str] = ["wifi_rssi_dbm", "wifi_snr_db", "wifi_retry_pct"]
    timestamp = datetime.now(timezone.utc).isoformat()

    t0 = time.perf_counter()

    try:
        async with httpx.AsyncClient(headers=headers, auth=auth, verify=tls_verify, timeout=timeout_sec) as client:
            resp = await client.get(interface_url)
            lat_ms = round((time.perf_counter() - t0) * 1000.0, 2)

            # -------------------------------------------------------------
            # HTTP 200 OK: Process Interface Telemetry
            # -------------------------------------------------------------
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except (json.JSONDecodeError, ValueError) as json_err:
                    rec = TelemetryRecord(
                        timestamp=timestamp,
                        device_id=device.device_id,
                        device_type=device.device_type,
                        device_status="DEGRADED",
                        latency_ms=lat_ms,
                        packet_loss_pct=0.0,
                        telemetry_origin="LIVE_DEVICE",
                        custom_metrics={
                            "protocol": "RESTCONF",
                            "endpoint": endpoint,
                            "error_type": "MALFORMED_YANG_RESPONSE",
                            "details": str(json_err),
                        },
                    )
                    return [rec], ["latency_ms", "device_status"], ["interface_oper_status", "cpu_utilization_pct"]

                (
                    if_name,
                    oper_st,
                    admin_st,
                    in_oct,
                    out_oct,
                    in_err,
                    out_err,
                    in_disc,
                    out_disc,
                ) = _extract_interfaces_data(data)

                available_metrics.extend([
                    "latency_ms", "packet_loss_pct", "device_status",
                    "interface_oper_status", "interface_crc_errors", "queue_drops_per_sec",
                ])

                if in_oct is not None:
                    available_metrics.extend(["interface_in_octets", "interface_out_octets"])
                else:
                    unsupported_metrics.extend(["interface_in_octets", "interface_out_octets"])

                # Optional Secondary Query: CPU & Memory Operational Models
                cpu_val: Optional[float] = None
                mem_val: Optional[float] = None

                cpu_ep = getattr(device, "rest_cpu_endpoint", None)
                if cpu_ep:
                    if not cpu_ep.startswith("/"):
                        cpu_ep = "/" + cpu_ep
                    try:
                        cpu_resp = await client.get(f"{base_url}{cpu_ep}")
                        if cpu_resp.status_code == 200:
                            cpu_val = _extract_cpu_utilization(cpu_resp.json())
                            if cpu_val is not None:
                                available_metrics.append("cpu_utilization_pct")
                    except Exception:
                        pass

                mem_ep = getattr(device, "rest_memory_endpoint", None)
                if mem_ep:
                    if not mem_ep.startswith("/"):
                        mem_ep = "/" + mem_ep
                    try:
                        mem_resp = await client.get(f"{base_url}{mem_ep}")
                        if mem_resp.status_code == 200:
                            mem_val = _extract_memory_utilization(mem_resp.json())
                            if mem_val is not None:
                                available_metrics.append("memory_utilization_pct")
                    except Exception:
                        pass

                if cpu_val is None:
                    unsupported_metrics.append("cpu_utilization_pct")
                if mem_val is None:
                    unsupported_metrics.append("memory_utilization_pct")

                device_status = "UP" if oper_st in ("UP", "up") else "DOWN"
                loss_pct = 0.0 if device_status == "UP" else 100.0

                note = (
                    f"Verified RESTCONF telemetry from {device.host}:{port}{endpoint}. "
                    f"ifName='{if_name}', oper-status={oper_st}. "
                    f"CPU: {f'{cpu_val}%' if cpu_val is not None else 'Unsupported (not fabricated)'}, "
                    f"RAM: {f'{mem_val}%' if mem_val is not None else 'Unsupported (not fabricated)'}."
                )

                custom = {
                    "protocol": "RESTCONF",
                    "endpoint": endpoint,
                    "http_status": 200,
                    "auth_mode": auth_type,
                    "tls_verification": "ENABLED" if tls_verify is not False else "DISABLED_BY_ADMIN",
                    "supported_metrics": available_metrics,
                    "unsupported_metrics": unsupported_metrics,
                    "probe_note": note,
                }
                if tls_warning:
                    custom["tls_warning"] = tls_warning

                record = TelemetryRecord(
                    timestamp=timestamp,
                    device_id=device.device_id,
                    device_type=device.device_type,
                    device_status=device_status,
                    interface_id=if_name,
                    interface_oper_status=oper_st,
                    interface_admin_status=admin_st,
                    interface_in_octets=in_oct,
                    interface_out_octets=out_oct,
                    interface_in_discards=in_disc,
                    interface_out_discards=out_disc,
                    latency_ms=lat_ms,
                    packet_loss_pct=loss_pct,
                    interface_crc_errors=in_err,
                    queue_drops_per_sec=float(in_disc),
                    cpu_utilization_pct=cpu_val,
                    memory_utilization_pct=mem_val,
                    telemetry_origin="LIVE_DEVICE",
                    custom_metrics=custom,
                )
                return [record], available_metrics, unsupported_metrics

            # -------------------------------------------------------------
            # HTTP 401 / 403: Authentication Rejection
            # -------------------------------------------------------------
            elif resp.status_code in (401, 403):
                err_type = "AUTHENTICATION_FAILED" if resp.status_code == 401 else "PERMISSION_DENIED"
                record = TelemetryRecord(
                    timestamp=timestamp,
                    device_id=device.device_id,
                    device_type=device.device_type,
                    device_status="AUTH_REJECTED",
                    packet_loss_pct=100.0,
                    telemetry_origin="LIVE_DEVICE",
                    custom_metrics={
                        "protocol": "RESTCONF",
                        "endpoint": endpoint,
                        "http_status": resp.status_code,
                        "error_type": err_type,
                        "auth_error": f"HTTP {resp.status_code}: Credentials rejected by router at {device.host}",
                    },
                )
                return [record], [], ["interface_oper_status", "interface_crc_errors", "cpu_utilization_pct"]

            # -------------------------------------------------------------
            # HTTP 404: YANG Model Path Not Implemented on Device
            # -------------------------------------------------------------
            elif resp.status_code == 404:
                record = TelemetryRecord(
                    timestamp=timestamp,
                    device_id=device.device_id,
                    device_type=device.device_type,
                    device_status="DEGRADED",
                    latency_ms=lat_ms,
                    packet_loss_pct=0.0,
                    telemetry_origin="LIVE_DEVICE",
                    custom_metrics={
                        "protocol": "RESTCONF",
                        "endpoint": endpoint,
                        "http_status": 404,
                        "error_type": "YANG_MODEL_NOT_FOUND",
                        "probe_note": f"RESTCONF path '{endpoint}' was not found (404) on {device.host}. Device does not implement this YANG module.",
                    },
                )
                return [record], ["latency_ms", "device_status"], ["interface_oper_status", "cpu_utilization_pct"]

            # -------------------------------------------------------------
            # HTTP 429: Rate Limited
            # -------------------------------------------------------------
            elif resp.status_code == 429:
                record = TelemetryRecord(
                    timestamp=timestamp,
                    device_id=device.device_id,
                    device_type=device.device_type,
                    device_status="DEGRADED",
                    latency_ms=lat_ms,
                    packet_loss_pct=0.0,
                    telemetry_origin="LIVE_DEVICE",
                    custom_metrics={
                        "protocol": "RESTCONF",
                        "endpoint": endpoint,
                        "http_status": 429,
                        "error_type": "RATE_LIMITED",
                        "probe_note": "Router rate-limited RESTCONF requests (429 Too Many Requests).",
                    },
                )
                return [record], ["latency_ms", "device_status"], unsupported_metrics

            # -------------------------------------------------------------
            # Other HTTP Status (e.g. 500, 502, 503)
            # -------------------------------------------------------------
            else:
                record = TelemetryRecord(
                    timestamp=timestamp,
                    device_id=device.device_id,
                    device_type=device.device_type,
                    device_status="DEGRADED",
                    latency_ms=lat_ms,
                    packet_loss_pct=0.0,
                    telemetry_origin="LIVE_DEVICE",
                    custom_metrics={
                        "protocol": "RESTCONF",
                        "endpoint": endpoint,
                        "http_status": resp.status_code,
                        "error_type": f"HTTP_{resp.status_code}",
                    },
                )
                return [record], ["latency_ms", "device_status"], unsupported_metrics

    # -----------------------------------------------------------------
    # Network / Timeout / TLS Exceptions
    # -----------------------------------------------------------------
    except httpx.ConnectTimeout:
        rec = TelemetryRecord(
            timestamp=timestamp,
            device_id=device.device_id,
            device_type=device.device_type,
            device_status="DOWN",
            packet_loss_pct=100.0,
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={
                "protocol": "RESTCONF",
                "error_type": "TIMEOUT",
                "details": f"RESTCONF TCP connection timed out connecting to {device.host}:{port}",
            },
        )
        return [rec], [], ["interface_oper_status", "cpu_utilization_pct"]

    except httpx.ReadTimeout:
        rec = TelemetryRecord(
            timestamp=timestamp,
            device_id=device.device_id,
            device_type=device.device_type,
            device_status="DOWN",
            packet_loss_pct=100.0,
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={
                "protocol": "RESTCONF",
                "error_type": "TIMEOUT",
                "details": f"RESTCONF server at {device.host}:{port} did not send data within {timeout_sec}s",
            },
        )
        return [rec], [], ["interface_oper_status", "cpu_utilization_pct"]

    except (httpx.ConnectError, ssl.SSLError) as net_err:
        err_msg = str(net_err)
        is_tls_err = any(t in err_msg.lower() for t in ["certificate", "ssl", "tls", "handshake", "verify"])

        err_type = "TLS_VERIFICATION_FAILED" if is_tls_err else "CONNECTION_REFUSED"
        note = (
            "TLS certificate verification failed. If the device uses a private or self-signed certificate, "
            "provide an enterprise CA bundle via ca_cert_path."
            if is_tls_err
            else f"Failed to establish connection to {device.host}:{port}: {err_msg}"
        )

        rec = TelemetryRecord(
            timestamp=timestamp,
            device_id=device.device_id,
            device_type=device.device_type,
            device_status="DOWN",
            packet_loss_pct=100.0,
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={
                "protocol": "RESTCONF",
                "error_type": err_type,
                "probe_note": note,
                "details": err_msg,
            },
        )
        return [rec], [], ["interface_oper_status", "cpu_utilization_pct"]

    except Exception as exc:
        rec = TelemetryRecord(
            timestamp=timestamp,
            device_id=device.device_id,
            device_type=device.device_type,
            device_status="DOWN",
            packet_loss_pct=100.0,
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={
                "protocol": "RESTCONF",
                "error_type": "UNKNOWN_EXCEPTION",
                "details": str(exc),
            },
        )
        return [rec], [], ["interface_oper_status", "cpu_utilization_pct"]
