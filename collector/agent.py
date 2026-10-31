"""
Network Collector Agent.
Runs background polling loops for locally allowable network devices,
receives LAN syslog streams, and transmits verified metrics to the cloud backend.
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timezone

from collector.config import CollectorSettings, LocalDeviceConfig, DeviceProtocol
from collector.client import CollectorBackendClient
from collector.adapters.reachability_probe import probe_tcp_reachability
from collector.adapters.snmp_poller import poll_snmp_device
from collector.adapters.restconf_poller import poll_restconf_device
from collector.adapters.syslog_receiver import SyslogServer
from collector.adapters.wifi_poller import poll_wifi_controller
from collector.adapters.host_metrics import poll_host_metrics

logger = logging.getLogger("NetCoopCollector")


class NetworkCollectorAgent:
    """
    Local daemon monitoring LAN network devices and pushing outbound telemetry.
    """

    def __init__(self, settings: CollectorSettings):
        self.settings = settings
        self.client = CollectorBackendClient(settings.backend_url)
        self.syslog_server = SyslogServer(port=settings.syslog_port)
        self._running = False
        self._tasks: List[asyncio.Task] = []

    async def pair_if_needed(self) -> None:
        """
        Pairs with backend if enrollment token is set and no session token exists.
        """
        if self.settings.enrollment_token and not self.settings.session_token:
            if not self.settings.collector_id:
                # Extract collector id from token if prefixed or request backend
                self.settings.collector_id = "col-lan-01"

            logger.info("Initiating secure pairing with backend: %s", self.settings.backend_url)
            reg_data = await self.client.register(
                collector_id=self.settings.collector_id or "col-auto",
                enrollment_token=self.settings.enrollment_token,
            )
            self.settings.session_token = reg_data["session_token"]
            if reg_data.get("collector_id"):
                self.settings.collector_id = reg_data["collector_id"]
            logger.info("Pairing successful! Session token acquired.")

    async def _heartbeat_loop(self) -> None:
        """
        Sends periodic keepalive heartbeats to cloud backend.
        """
        interval = max(self.settings.heartbeat_interval_sec, 10)
        while self._running:
            try:
                if self.settings.collector_id and self.settings.session_token:
                    await self.client.heartbeat(
                        collector_id=self.settings.collector_id,
                        session_token=self.settings.session_token,
                        active_devices=len([d for d in self.settings.devices if d.enabled]),
                    )
            except Exception as e:
                logger.warning("Heartbeat failed (backend unreachable): %s", e)
            await asyncio.sleep(interval)

    async def _poll_device(self, device: LocalDeviceConfig) -> None:
        """
        Polls a single device using its designated adapter.
        """
        if not device.enabled:
            return

        try:
            if device.protocol in (DeviceProtocol.TCP_PROBE, DeviceProtocol.PING_PROBE):
                records, avail, unsupp = await probe_tcp_reachability(device)
            elif device.protocol == DeviceProtocol.HOST_METRICS:
                records, avail, unsupp = await poll_host_metrics(device)
            elif device.protocol == DeviceProtocol.SNMP:
                records, avail, unsupp = await poll_snmp_device(device)
            elif device.protocol == DeviceProtocol.RESTCONF:
                records, avail, unsupp = await poll_restconf_device(device)
            elif device.protocol == DeviceProtocol.WIFI_CONTROLLER:
                records, avail, unsupp = await poll_wifi_controller(device)
            else:
                records, avail, unsupp = await probe_tcp_reachability(device)

            if records and self.settings.collector_id and self.settings.session_token:
                await self.client.push_telemetry(
                    collector_id=self.settings.collector_id,
                    session_token=self.settings.session_token,
                    device_id=device.device_id,
                    records=records,
                    metrics_available=avail,
                    metrics_unsupported=unsupp,
                )
        except Exception as e:
            logger.error("Error polling device %s: %s", device.device_id, e)

    async def _device_polling_loop(self) -> None:
        """
        Iterates over all devices in the allowlist on their configured intervals.
        """
        while self._running:
            # Also flush any buffered syslog events
            syslog_recs = self.syslog_server.drain_records()
            if syslog_recs and self.settings.collector_id and self.settings.session_token:
                # Group by device_id
                by_dev = {}
                for r in syslog_recs:
                    by_dev.setdefault(r.device_id, []).append(r)
                for dev_id, recs in by_dev.items():
                    try:
                        await self.client.push_telemetry(
                            collector_id=self.settings.collector_id,
                            session_token=self.settings.session_token,
                            device_id=dev_id,
                            records=recs,
                            metrics_available=["interface_flaps", "interface_crc_errors"],
                        )
                    except Exception as e:
                        logger.warning("Failed to push syslog batch: %s", e)

            # Synchronize any devices registered via the remote Cloud NOC Dashboard
            if self.settings.collector_id and self.settings.session_token:
                try:
                    remote_devs = await self.client.fetch_devices(self.settings.collector_id)
                    existing_ids = {d.device_id for d in self.settings.devices}
                    for rd in remote_devs:
                        dev_id = rd.get("device_id")
                        if dev_id and dev_id not in existing_ids:
                            proto_str = str(rd.get("protocol", "TCP_PROBE")).upper()
                            proto = getattr(DeviceProtocol, proto_str, DeviceProtocol.TCP_PROBE)
                            new_dev = LocalDeviceConfig(
                                device_id=dev_id,
                                name=rd.get("name") or dev_id,
                                device_type=rd.get("device_type", "router"),
                                host=rd.get("ip", "127.0.0.1"),
                                port=rd.get("port", 80),
                                protocol=proto,
                            )
                            self.settings.devices.append(new_dev)
                            logger.info("Synchronized device from cloud backend: %s (%s:%d)", dev_id, new_dev.host, new_dev.port)
                except Exception as e:
                    logger.debug("Device sync skipped: %s", e)

            # Poll devices
            for dev in self.settings.devices:
                asyncio.create_task(self._poll_device(dev))

            await asyncio.sleep(15)

    async def start(self) -> None:
        """
        Starts the collector agent and background tasks.
        """
        self._running = True
        if not self.settings.devices:
            import socket
            self.settings.devices.append(
                LocalDeviceConfig(
                    device_id=f"HOST-{socket.gethostname()[:12].upper()}",
                    name=f"Collector Host Appliance ({socket.gethostname()})",
                    device_type="server",
                    host="127.0.0.1",
                    port=8000,
                    protocol=DeviceProtocol.HOST_METRICS,
                )
            )
        await self.pair_if_needed()
        await self.syslog_server.start()

        self._tasks.append(asyncio.create_task(self._heartbeat_loop()))
        self._tasks.append(asyncio.create_task(self._device_polling_loop()))
        logger.info("NetCoop Collector Agent running with %d target devices.", len(self.settings.devices))

    async def stop(self) -> None:
        """
        Graceful shutdown.
        """
        self._running = False
        self.syslog_server.stop()
        for t in self._tasks:
            t.cancel()
        logger.info("Collector Agent shutdown complete.")

