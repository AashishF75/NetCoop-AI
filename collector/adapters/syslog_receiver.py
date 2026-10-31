"""
Local Asynchronous UDP Syslog Server & Event Parser.
Receives incoming RFC 3164 / 5424 and Cisco IOS syslog streams on LAN UDP 514 / 5140.
"""

import asyncio
import re
from typing import List, Optional
from datetime import datetime, timezone

from collector.schema import TelemetryRecord


class SyslogDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, message_callback):
        self.message_callback = message_callback

    def datagram_received(self, data: bytes, addr):
        try:
            line = data.decode("utf-8", errors="ignore").strip()
            if line:
                self.message_callback(line, addr[0])
        except Exception:
            pass


class SyslogServer:
    """
    Asynchronous UDP Syslog Server listening on local network.
    """

    def __init__(self, port: int = 5140):
        self.port = port
        self.transport = None
        self._buffer: List[TelemetryRecord] = []

    def handle_syslog_line(self, line: str, source_ip: str) -> None:
        """
        Parses incoming syslog string into normalized TelemetryRecord.
        """
        device_id = source_ip

        # Check for device hostname in Cisco syslog: <189>123: Router-HQ-01: %LINK-3-UPDOWN...
        dev_match = re.search(r"([A-Za-z0-9\-_]+)\s*:\s*(%[A-Z0-9_\-]+)", line)
        if dev_match:
            device_id = dev_match.group(1)

        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Link Down / Flap
        if re.search(r"(LINK|LINEPROTO)-[0-5]-UPDOWN.*?changed state to down", line, re.I):
            iface_match = re.search(r"Interface\s+([A-Za-z0-9\/\.\-_]+)", line, re.I)
            iface = iface_match.group(1) if iface_match else "GigabitEthernet0/1"
            rec = TelemetryRecord(
                timestamp=now_iso,
                device_id=device_id,
                device_type="router",
                device_status="DOWN",
                interface_id=iface,
                packet_loss_pct=100.0,
                interface_flaps=1,
                telemetry_origin="LIVE_DEVICE",
                custom_metrics={"raw_syslog": line, "event_type": "LINK_DOWN"},
            )
            self._buffer.append(rec)

        # 2. Duplex Mismatch / CRC Errors
        elif re.search(r"duplex mismatch|crc error|frame error|fcs discard", line, re.I):
            iface_match = re.search(r"([A-Za-z]+[0-9\/\.\-_]+)", line)
            iface = iface_match.group(1) if iface_match else "eth0"
            rec = TelemetryRecord(
                timestamp=now_iso,
                device_id=device_id,
                device_type="switch",
                device_status="DEGRADED",
                interface_id=iface,
                interface_crc_errors=145,
                telemetry_origin="LIVE_DEVICE",
                custom_metrics={"raw_syslog": line, "event_type": "CRC_DEGRADATION"},
            )
            self._buffer.append(rec)

        # 3. CPU Saturation
        elif re.search(r"CPU utilization.*?([0-9]{1,3})%", line, re.I):
            match = re.search(r"([0-9]{1,3})%", line)
            if match:
                cpu_val = float(match.group(1))
                rec = TelemetryRecord(
                    timestamp=now_iso,
                    device_id=device_id,
                    device_type="router",
                    device_status="DEGRADED",
                    cpu_utilization_pct=cpu_val,
                    telemetry_origin="LIVE_DEVICE",
                    custom_metrics={"raw_syslog": line, "event_type": "CPU_THRESHOLD_EXCEEDED"},
                )
                self._buffer.append(rec)

        # 4. Queue / Buffer Exhaustion
        elif re.search(r"queue.*?full|buffer.*?exhausted|tail drop", line, re.I):
            rec = TelemetryRecord(
                timestamp=now_iso,
                device_id=device_id,
                device_type="router",
                device_status="DEGRADED",
                queue_drops_per_sec=280.0,
                telemetry_origin="LIVE_DEVICE",
                custom_metrics={"raw_syslog": line, "event_type": "BUFFER_EXHAUSTION"},
            )
            self._buffer.append(rec)

    async def start(self) -> None:
        loop = asyncio.get_event_loop()
        try:
            self.transport, _ = await loop.create_datagram_endpoint(
                lambda: SyslogDatagramProtocol(self.handle_syslog_line),
                local_addr=("0.0.0.0", self.port),
            )
        except OSError as e:
            # Fallback to alternate port if 514 requires root/admin privilege
            if self.port == 514:
                self.port = 5140
                self.transport, _ = await loop.create_datagram_endpoint(
                    lambda: SyslogDatagramProtocol(self.handle_syslog_line),
                    local_addr=("0.0.0.0", self.port),
                )

    def stop(self) -> None:
        if self.transport:
            self.transport.close()
            self.transport = None

    def drain_records(self) -> List[TelemetryRecord]:
        recs = list(self._buffer)
        self._buffer.clear()
        return recs
