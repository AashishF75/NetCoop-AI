"""
Authenticated SNMPv3 and Legacy SNMPv2c Telemetry Poller.
Queries RFC 1213 / RFC 2863 standard MIBs and hardware processor/storage MIBs
using the maintained, asynchronous pysnmp library.
Device credentials remain strictly local to the collector; internal metrics
like CPU/RAM are left None if unsupported (never fabricated).
"""

import time
import logging
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timezone

from collector.schema import TelemetryRecord
from collector.config import LocalDeviceConfig

# pysnmp imports
from pysnmp.hlapi.asyncio import (
    SnmpEngine,
    CommunityData,
    UsmUserData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    get_cmd,
    usmHMACSHAAuthProtocol,
    usmHMAC128SHA224AuthProtocol,
    usmHMAC192SHA256AuthProtocol,
    usmHMAC256SHA384AuthProtocol,
    usmHMAC384SHA512AuthProtocol,
    usmHMACMD5AuthProtocol,
    usmNoAuthProtocol,
    usmAesCfb128Protocol,
    usmAesCfb192Protocol,
    usmAesCfb256Protocol,
    usmDESPrivProtocol,
    usm3DESEDEPrivProtocol,
    usmNoPrivProtocol,
)
from pysnmp.proto import rfc1905

logger = logging.getLogger("SNMPPoller")

# Standard MIB-II OIDs (RFC 1213, RFC 2863)
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"

# Standard Hardware Host Resources MIB (RFC 2790)
OID_HR_PROCESSOR_LOAD = "1.3.6.1.2.1.25.3.3.1.2.1"
OID_HR_STORAGE_SIZE = "1.3.6.1.2.1.25.2.3.1.5.1"
OID_HR_STORAGE_USED = "1.3.6.1.2.1.25.2.3.1.6.1"

# Vendor Hardware MIBs (Cisco CISCO-PROCESS-MIB & CISCO-MEMORY-POOL-MIB)
OID_CISCO_CPU_5MIN = "1.3.6.1.4.1.9.9.109.1.1.1.1.8.1"
OID_CISCO_MEM_USED = "1.3.6.1.4.1.9.9.48.1.1.1.5.1"
OID_CISCO_MEM_FREE = "1.3.6.1.4.1.9.9.48.1.1.1.6.1"

# Auth Protocol Mappings
AUTH_PROTOCOLS = {
    "SHA": usmHMACSHAAuthProtocol,
    "SHA1": usmHMACSHAAuthProtocol,
    "SHA224": usmHMAC128SHA224AuthProtocol,
    "SHA256": usmHMAC192SHA256AuthProtocol,
    "SHA384": usmHMAC256SHA384AuthProtocol,
    "SHA512": usmHMAC384SHA512AuthProtocol,
    "MD5": usmHMACMD5AuthProtocol,
    "NONE": usmNoAuthProtocol,
}

# Privacy Protocol Mappings
PRIV_PROTOCOLS = {
    "AES": usmAesCfb128Protocol,
    "AES128": usmAesCfb128Protocol,
    "AES192": usmAesCfb192Protocol,
    "AES256": usmAesCfb256Protocol,
    "DES": usmDESPrivProtocol,
    "3DES": usm3DESEDEPrivProtocol,
    "NONE": usmNoPrivProtocol,
}

IF_OPER_STATUS_MAP = {
    1: "UP",
    2: "DOWN",
    3: "TESTING",
    4: "UNKNOWN",
    5: "DORMANT",
    6: "NOT_PRESENT",
    7: "LOWER_LAYER_DOWN",
}

IF_ADMIN_STATUS_MAP = {
    1: "UP",
    2: "DOWN",
    3: "TESTING",
}


def _is_unsupported_val(val: Any) -> bool:
    """Checks whether pysnmp returned an RFC 1905 error/exception value."""
    if val is None:
        return True
    return isinstance(val, (rfc1905.NoSuchObject, rfc1905.NoSuchInstance, rfc1905.EndOfMibView))


def _clean_str(val: Any) -> Optional[str]:
    """Safely extracts clean string from ASN.1 OctetString or DisplayString."""
    if _is_unsupported_val(val):
        return None
    try:
        raw = bytes(val)
        return raw.decode("utf-8", errors="replace").strip()
    except Exception:
        return str(val).strip()


def _clean_int(val: Any) -> Optional[int]:
    """Safely extracts integer value."""
    if _is_unsupported_val(val):
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _clean_float(val: Any) -> Optional[float]:
    """Safely extracts float value."""
    if _is_unsupported_val(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def build_security_credentials(device: LocalDeviceConfig):
    """
    Constructs either SNMPv3 UsmUserData or SNMPv2c CommunityData.
    Credentials are read from local configuration and never sent to cloud.
    """
    version = (device.snmp_version or "v3").strip().lower()

    if version in ("v2c", "2c", "v2"):
        community = device.snmp_community or "public"
        return CommunityData(community, mpModel=1), "SNMPv2c"

    # Default: SNMPv3 USM
    user_name = device.snmp_user or "snmpv3user"
    sec_level = (device.snmp_security_level or "authPriv").strip().lower()

    auth_proto = AUTH_PROTOCOLS.get(
        (device.snmp_auth_protocol or "SHA").upper(),
        usmHMACSHAAuthProtocol,
    )
    priv_proto = PRIV_PROTOCOLS.get(
        (device.snmp_priv_protocol or "AES").upper(),
        usmAesCfb128Protocol,
    )

    if sec_level == "authpriv" and device.snmp_auth_password and device.snmp_priv_password:
        user_data = UsmUserData(
            user_name,
            authKey=device.snmp_auth_password,
            authProtocol=auth_proto,
            privKey=device.snmp_priv_password,
            privProtocol=priv_proto,
        )
        return user_data, "SNMPv3 (authPriv)"
    elif sec_level in ("authnopriv", "authpriv") and device.snmp_auth_password:
        user_data = UsmUserData(
            user_name,
            authKey=device.snmp_auth_password,
            authProtocol=auth_proto,
        )
        return user_data, "SNMPv3 (authNoPriv)"
    else:
        user_data = UsmUserData(user_name)
        return user_data, "SNMPv3 (noAuthNoPriv)"


async def poll_snmp_device(device: LocalDeviceConfig) -> Tuple[List[TelemetryRecord], List[str], List[str]]:
    """
    Polls an authorized physical network device via SNMPv3 (or explicitly configured SNMPv2c).
    Extracts system info, interface health, errors, discards, and hardware counters if exposed.
    Returns: (records, metrics_available, metrics_unsupported)
    """
    host = device.host
    port = device.port or 161
    timeout_sec = max(device.timeout_sec, 0.5)
    if_idx = device.snmp_interface_index or 1

    credentials, protocol_label = build_security_credentials(device)
    context_data = ContextData(contextName=device.snmp_context_name or "")
    snmp_engine = SnmpEngine()

    # Define interface-specific OIDs
    oid_if_oper = f"1.3.6.1.2.1.2.2.1.8.{if_idx}"
    oid_if_admin = f"1.3.6.1.2.1.2.2.1.7.{if_idx}"
    oid_if_in_octets = f"1.3.6.1.2.1.2.2.1.10.{if_idx}"
    oid_if_out_octets = f"1.3.6.1.2.1.2.2.1.16.{if_idx}"
    oid_if_in_errors = f"1.3.6.1.2.1.2.2.1.14.{if_idx}"
    oid_if_out_errors = f"1.3.6.1.2.1.2.2.1.20.{if_idx}"
    oid_if_in_discards = f"1.3.6.1.2.1.2.2.1.13.{if_idx}"
    oid_if_out_discards = f"1.3.6.1.2.1.2.2.1.19.{if_idx}"
    oid_if_name = f"1.3.6.1.2.1.31.1.1.1.1.{if_idx}"
    oid_if_hc_in = f"1.3.6.1.2.1.31.1.1.1.6.{if_idx}"
    oid_if_hc_out = f"1.3.6.1.2.1.31.1.1.1.10.{if_idx}"

    oids_to_query = [
        # System
        (OID_SYS_DESCR, "sys_descr"),
        (OID_SYS_UPTIME, "sys_uptime"),
        (OID_SYS_NAME, "sys_name"),
        # Interface
        (oid_if_oper, "if_oper_status"),
        (oid_if_admin, "if_admin_status"),
        (oid_if_in_octets, "if_in_octets"),
        (oid_if_out_octets, "if_out_octets"),
        (oid_if_in_errors, "if_in_errors"),
        (oid_if_out_errors, "if_out_errors"),
        (oid_if_in_discards, "if_in_discards"),
        (oid_if_out_discards, "if_out_discards"),
        (oid_if_name, "if_name"),
        # CPU / Memory candidates
        (OID_HR_PROCESSOR_LOAD, "hr_cpu"),
        (OID_HR_STORAGE_USED, "hr_storage_used"),
        (OID_HR_STORAGE_SIZE, "hr_storage_size"),
        (OID_CISCO_CPU_5MIN, "cisco_cpu"),
        (OID_CISCO_MEM_USED, "cisco_mem_used"),
        (OID_CISCO_MEM_FREE, "cisco_mem_free"),
    ]

    available_metrics: List[str] = []
    unsupported_metrics: List[str] = ["wifi_rssi_dbm", "wifi_snr_db", "wifi_retry_pct"]
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        transport = await UdpTransportTarget.create((host, port), timeout=timeout_sec, retries=1)
    except Exception as e:
        rec = TelemetryRecord(
            timestamp=timestamp,
            device_id=device.device_id,
            device_type=device.device_type,
            device_status="DOWN",
            packet_loss_pct=100.0,
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={"error_type": "DNS_OR_SOCKET_ERROR", "snmp_error": str(e)},
        )
        return [rec], [], ["sys_descr", "if_oper_status", "interface_crc_errors", "cpu_utilization_pct"]

    query_objects = [ObjectType(ObjectIdentity(oid)) for oid, _ in oids_to_query]

    t0 = time.perf_counter()
    try:
        err_indication, err_status, err_index, var_binds = await get_cmd(
            snmp_engine,
            credentials,
            transport,
            context_data,
            *query_objects,
        )
        rtt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    except Exception as exc:
        rec = TelemetryRecord(
            timestamp=timestamp,
            device_id=device.device_id,
            device_type=device.device_type,
            device_status="DOWN",
            packet_loss_pct=100.0,
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={"error_type": "SNMP_ENGINE_EXCEPTION", "snmp_error": str(exc)},
        )
        return [rec], [], ["sys_descr", "if_oper_status", "cpu_utilization_pct"]

    # 1. Check for Transport / Timeout Errors
    if err_indication:
        err_str = str(err_indication)
        is_timeout = "timeout" in err_str.lower() or isinstance(err_indication, rfc1905.RequestTimedOut if hasattr(rfc1905, 'RequestTimedOut') else object)
        is_auth = any(term in err_str.lower() for term in ["auth", "digest", "security", "unknown user", "decryption"])

        status_code = "AUTH_REJECTED" if is_auth else ("DOWN" if is_timeout else "DEGRADED")
        rec = TelemetryRecord(
            timestamp=timestamp,
            device_id=device.device_id,
            device_type=device.device_type,
            device_status=status_code,
            packet_loss_pct=100.0 if status_code != "DEGRADED" else 0.0,
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={
                "protocol": protocol_label,
                "error_type": "AUTHENTICATION_FAILURE" if is_auth else ("TIMEOUT" if is_timeout else "SNMP_ERROR"),
                "snmp_error": err_str,
            },
        )
        return [rec], [], ["sys_descr", "if_oper_status", "interface_crc_errors", "cpu_utilization_pct"]

    # 2. Check for PDU Error Status
    if err_status:
        rec = TelemetryRecord(
            timestamp=timestamp,
            device_id=device.device_id,
            device_type=device.device_type,
            device_status="DEGRADED",
            packet_loss_pct=0.0,
            latency_ms=rtt_ms,
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={
                "protocol": protocol_label,
                "error_type": "SNMP_PDU_ERROR",
                "error_status": err_status.prettyPrint(),
                "error_index": int(err_index),
            },
        )
        return [rec], ["latency_ms", "device_status"], ["cpu_utilization_pct"]

    # 3. Parse VarBinds
    values_map: Dict[str, Any] = {}
    for i, var_bind in enumerate(var_binds):
        if i < len(oids_to_query):
            metric_tag = oids_to_query[i][1]
            values_map[metric_tag] = var_bind[1]

    # System attributes
    sys_descr = _clean_str(values_map.get("sys_descr"))
    sys_uptime_ticks = _clean_int(values_map.get("sys_uptime"))
    sys_uptime_sec = round(sys_uptime_ticks / 100.0, 1) if sys_uptime_ticks is not None else None
    sys_name = _clean_str(values_map.get("sys_name"))

    if sys_descr is not None:
        available_metrics.extend(["sys_descr", "sys_uptime", "sys_name"])
    else:
        unsupported_metrics.extend(["sys_descr", "sys_uptime", "sys_name"])

    # Interface metrics
    raw_oper = _clean_int(values_map.get("if_oper_status"))
    raw_admin = _clean_int(values_map.get("if_admin_status"))
    if_oper = IF_OPER_STATUS_MAP.get(raw_oper, "UNKNOWN") if raw_oper is not None else None
    if_admin = IF_ADMIN_STATUS_MAP.get(raw_admin, "UNKNOWN") if raw_admin is not None else None
    if_name = _clean_str(values_map.get("if_name")) or f"interface-{if_idx}"

    in_octets = _clean_int(values_map.get("if_in_octets"))
    out_octets = _clean_int(values_map.get("if_out_octets"))
    in_errors = _clean_int(values_map.get("if_in_errors")) or 0
    out_errors = _clean_int(values_map.get("if_out_errors")) or 0
    in_discards = _clean_int(values_map.get("if_in_discards")) or 0
    out_discards = _clean_int(values_map.get("if_out_discards")) or 0

    if if_oper is not None:
        available_metrics.extend(["interface_oper_status", "interface_admin_status", "latency_ms", "packet_loss_pct", "device_status"])
    else:
        unsupported_metrics.append("interface_oper_status")

    if in_errors is not None:
        available_metrics.extend(["interface_crc_errors", "interface_discards"])
    else:
        unsupported_metrics.extend(["interface_crc_errors", "interface_discards"])

    if in_octets is not None:
        available_metrics.extend(["interface_in_octets", "interface_out_octets"])
    else:
        unsupported_metrics.extend(["interface_in_octets", "interface_out_octets"])

    # CPU Utilization (Standard HR-MIB vs Cisco Enterprise MIB)
    cpu_val: Optional[float] = None
    hr_cpu = _clean_float(values_map.get("hr_cpu"))
    cisco_cpu = _clean_float(values_map.get("cisco_cpu"))

    if cisco_cpu is not None and 0.0 <= cisco_cpu <= 100.0:
        cpu_val = round(cisco_cpu, 1)
        available_metrics.append("cpu_utilization_pct")
    elif hr_cpu is not None and 0.0 <= hr_cpu <= 100.0:
        cpu_val = round(hr_cpu, 1)
        available_metrics.append("cpu_utilization_pct")
    else:
        unsupported_metrics.append("cpu_utilization_pct")

    # Memory Utilization (Standard HR-MIB vs Cisco Enterprise MIB)
    mem_val: Optional[float] = None
    cisco_used = _clean_float(values_map.get("cisco_mem_used"))
    cisco_free = _clean_float(values_map.get("cisco_mem_free"))
    hr_used = _clean_float(values_map.get("hr_storage_used"))
    hr_size = _clean_float(values_map.get("hr_storage_size"))

    if cisco_used is not None and cisco_free is not None and (cisco_used + cisco_free) > 0:
        mem_val = round((cisco_used / (cisco_used + cisco_free)) * 100.0, 1)
        available_metrics.append("memory_utilization_pct")
    elif hr_used is not None and hr_size is not None and hr_size > 0:
        mem_val = round((hr_used / hr_size) * 100.0, 1)
        available_metrics.append("memory_utilization_pct")
    else:
        unsupported_metrics.append("memory_utilization_pct")

    # Device reachability & status evaluation
    device_status = "UP" if (if_oper in ("UP", "TESTING") or sys_descr is not None) else "DOWN"
    loss_pct = 0.0 if device_status == "UP" else 100.0

    note = (
        f"Verified {protocol_label} telemetry from {host}:{port}. "
        f"sysName='{sys_name or 'N/A'}', sysUpTime={sys_uptime_sec or 'N/A'}s, ifOperStatus={if_oper or 'N/A'}. "
        f"CPU: {f'{cpu_val}%' if cpu_val is not None else 'Unsupported (not fabricated)'}, "
        f"RAM: {f'{mem_val}%' if mem_val is not None else 'Unsupported (not fabricated)'}."
    )

    record = TelemetryRecord(
        timestamp=timestamp,
        device_id=device.device_id,
        device_type=device.device_type,
        device_status=device_status,
        interface_id=if_name,
        interface_oper_status=if_oper,
        interface_admin_status=if_admin,
        interface_in_octets=in_octets,
        interface_out_octets=out_octets,
        interface_in_discards=in_discards,
        interface_out_discards=out_discards,
        sys_name=sys_name,
        sys_descr=sys_descr,
        sys_uptime_sec=sys_uptime_sec,
        latency_ms=rtt_ms,
        packet_loss_pct=loss_pct,
        interface_crc_errors=in_errors,
        cpu_utilization_pct=cpu_val,
        memory_utilization_pct=mem_val,
        telemetry_origin="LIVE_DEVICE",
        custom_metrics={
            "protocol": protocol_label,
            "snmp_port": port,
            "snmp_interface_index": if_idx,
            "rtt_ms": rtt_ms,
            "supported_metrics": available_metrics,
            "unsupported_metrics": unsupported_metrics,
            "probe_note": note,
        },
    )

    return [record], available_metrics, unsupported_metrics
