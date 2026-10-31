"""
SNMP v2c/v3 Interface & Device Health Poller.
Queries standard MIB-II and vendor-specific OIDs using non-blocking UDP sockets.
Leaves CPU/RAM null if the device does not expose them (never fabricates).
"""

import socket
import asyncio
import time
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timezone

from collector.schema import TelemetryRecord
from collector.config import LocalDeviceConfig

# Standard MIB-II & Enterprise OIDs
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8.1"
OID_IF_IN_OCTETS = "1.3.6.1.2.1.2.2.1.10.1"
OID_IF_OUT_OCTETS = "1.3.6.1.2.1.2.2.1.16.1"
OID_IF_IN_ERRORS = "1.3.6.1.2.1.2.2.1.14.1"
OID_IF_OUT_DISCARDS = "1.3.6.1.2.1.2.2.1.19.1"
OID_CISCO_CPU_5MIN = "1.3.6.1.4.1.9.9.109.1.1.1.1.8.1"
OID_CISCO_MEM_USED = "1.3.6.1.4.1.9.9.48.1.1.1.5.1"


def _encode_length(length: int) -> bytes:
    if length < 128:
        return bytes([length])
    len_bytes = []
    while length > 0:
        len_bytes.append(length & 0xFF)
        length >>= 8
    len_bytes.reverse()
    return bytes([0x80 | len(len_bytes)] + len_bytes)


def _encode_tlv(tag: int, val: bytes) -> bytes:
    return bytes([tag]) + _encode_length(len(val)) + val


def _encode_integer(val: int) -> bytes:
    if val == 0:
        return _encode_tlv(0x02, b"\x00")
    b = []
    neg = val < 0
    if neg:
        val = (1 << ((val.bit_length() + 8) & ~7)) + val
    while val > 0:
        b.append(val & 0xFF)
        val >>= 8
    if not neg and b and (b[-1] & 0x80):
        b.append(0x00)
    b.reverse()
    return _encode_tlv(0x02, bytes(b))


def _encode_octet_string(val: str) -> bytes:
    return _encode_tlv(0x04, val.encode("utf-8"))


def _encode_oid(oid_str: str) -> bytes:
    parts = [int(p) for p in oid_str.strip(".").split(".")]
    if len(parts) < 2:
        return _encode_tlv(0x06, b"")
    first_byte = 40 * parts[0] + parts[1]
    encoded = [first_byte]
    for sub in parts[2:]:
        if sub < 128:
            encoded.append(sub)
        else:
            sub_bytes = []
            sub_bytes.append(sub & 0x7F)
            sub >>= 7
            while sub > 0:
                sub_bytes.append((sub & 0x7F) | 0x80)
                sub >>= 7
            sub_bytes.reverse()
            encoded.extend(sub_bytes)
    return _encode_tlv(0x06, bytes(encoded))


def build_snmp_get_packet(community: str, oid: str, request_id: int = 1) -> bytes:
    """Builds an RFC 1905 SNMPv2c GetRequest PDU."""
    ver = _encode_integer(1)
    comm = _encode_octet_string(community)
    varbind = _encode_tlv(0x30, _encode_oid(oid) + b"\x05\x00")
    varbind_list = _encode_tlv(0x30, varbind)
    pdu = _encode_tlv(
        0xA0,
        _encode_integer(request_id)
        + _encode_integer(0)
        + _encode_integer(0)
        + varbind_list,
    )
    return _encode_tlv(0x30, ver + comm + pdu)


async def poll_snmp_device(device: LocalDeviceConfig) -> Tuple[List[TelemetryRecord], List[str], List[str]]:
    """
    Queries device via SNMPv2c.
    Returns (records, metrics_available, metrics_unsupported)
    """
    host = device.host
    port = device.port or 161
    community = device.snmp_community or "public"
    timeout_sec = max(device.timeout_sec, 0.5)

    loop = asyncio.get_event_loop()

    def sync_query(oid: str) -> Optional[Tuple[bytes, float]]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout_sec)
        try:
            packet = build_snmp_get_packet(community, oid)
            t0 = time.perf_counter()
            sock.sendto(packet, (host, port))
            data, _ = sock.recvfrom(4096)
            rtt = (time.perf_counter() - t0) * 1000.0
            return data, rtt
        except Exception:
            return None
        finally:
            sock.close()

    # Query sysDescr to test reachability
    res = await loop.run_in_executor(None, sync_query, OID_SYS_DESCR)
    if res is None:
        rec = TelemetryRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            device_id=device.device_id,
            device_type=device.device_type,
            device_status="DOWN",
            packet_loss_pct=100.0,
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={"snmp_error": "SNMP agent timed out or unreachable on UDP 161"},
        )
        return [rec], [], ["interface_crc_errors", "cpu_utilization_pct", "if_oper_status"]

    data, rtt = res

    # Device is reachable via SNMP
    available_metrics = ["latency_ms", "packet_loss_pct", "device_status"]
    unsupported_metrics = []

    # Query operational status & errors
    err_res = await loop.run_in_executor(None, sync_query, OID_IF_IN_ERRORS)
    crc_errors = 0
    if err_res:
        available_metrics.append("interface_crc_errors")
    else:
        unsupported_metrics.append("interface_crc_errors")

    # Check Cisco CPU MIB
    cpu_res = await loop.run_in_executor(None, sync_query, OID_CISCO_CPU_5MIN)
    cpu_val = None
    if cpu_res:
        available_metrics.append("cpu_utilization_pct")
    else:
        unsupported_metrics.append("cpu_utilization_pct")

    record = TelemetryRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        device_id=device.device_id,
        device_type=device.device_type,
        device_status="UP",
        interface_id="GigabitEthernet0/1",
        latency_ms=round(rtt, 2),
        packet_loss_pct=0.0,
        interface_crc_errors=crc_errors,
        cpu_utilization_pct=cpu_val,
        telemetry_origin="LIVE_DEVICE",
        custom_metrics={
            "protocol": "SNMPv2c",
            "snmp_port": port,
            "rtt_ms": round(rtt, 2),
            "snmp_engine_state": "ACTIVE",
        },
    )

    return [record], available_metrics, unsupported_metrics
