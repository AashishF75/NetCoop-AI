"""
Network Collector Agent.
Runs background polling loops for locally allowable network devices,
receives LAN syslog streams, and transmits verified metrics to the cloud backend.
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timezone

from collector.config import CollectorSettings, LocalDeviceConfig, DeviceProtocol, save_collector_config
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
            cid_to_send = self.settings.collector_id or "col-auto"
            logger.info("Initiating secure pairing with backend %s for collector candidate '%s'", self.settings.backend_url, cid_to_send)
            reg_data = await self.client.register(
                collector_id=cid_to_send,
                enrollment_token=self.settings.enrollment_token,
            )
            self.settings.session_token = reg_data["session_token"]
            if reg_data.get("collector_id"):
                self.settings.collector_id = reg_data["collector_id"]
            try:
                save_collector_config(self.settings)
            except Exception as e:
                logger.warning("Could not persist collector configuration: %s", e)
            logger.info("Pairing successful! Acquired session token for collector '%s'.", self.settings.collector_id)

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

    async def _execute_probe_job(self, job: dict) -> None:
        """
        Executes an on-demand probe job dispatched from cloud backend,
        runs the appropriate local adapter inside LAN, and pushes the result back.
        """
        job_id = job.get("job_id")
        target_ip = job.get("ip")
        proto_str = str(job.get("protocol", "PING")).upper()
        port = int(job.get("port") or 80)
        dev_id = job.get("device_id") or f"PROBE-{target_ip}"

        if proto_str in ("PING", "ICMP", "PING_PROBE"):
            proto = DeviceProtocol.PING_PROBE
        elif proto_str == "HOST_METRICS":
            proto = DeviceProtocol.HOST_METRICS
        elif proto_str == "SNMP":
            proto = DeviceProtocol.SNMP
        elif proto_str in ("RESTCONF", "YANG"):
            proto = DeviceProtocol.RESTCONF
        else:
            proto = DeviceProtocol.TCP_PROBE

        # Check if collector already has a locally configured device for this IP with saved credentials
        configured_dev = next((d for d in self.settings.devices if d.host == target_ip and d.protocol == proto), None)

        if configured_dev:
            tmp_device = configured_dev
        else:
            tmp_device = LocalDeviceConfig(
                device_id=dev_id,
                name=f"On-Demand Probe ({target_ip})",
                device_type="server" if proto == DeviceProtocol.HOST_METRICS else "router",
                host=target_ip,
                port=161 if proto == DeviceProtocol.SNMP else (443 if proto == DeviceProtocol.RESTCONF else (0 if proto == DeviceProtocol.PING_PROBE else port)),
                protocol=proto,
                timeout_sec=3.0,
                snmp_version=job.get("snmp_version") or "v3",
                snmp_community=job.get("snmp_community"),
                snmp_user=job.get("snmp_user"),
                snmp_auth_protocol=job.get("snmp_auth_protocol") or "SHA",
                snmp_auth_password=job.get("snmp_auth_password"),
                snmp_priv_protocol=job.get("snmp_priv_protocol") or "AES",
                snmp_priv_password=job.get("snmp_priv_password"),
                snmp_security_level=job.get("snmp_security_level") or "authPriv",
                rest_endpoint=job.get("rest_endpoint") or "/restconf/data/ietf-interfaces:interfaces-state",
                restconf_auth_type=job.get("restconf_auth_type") or "BASIC",
                username=job.get("username"),
                password=job.get("password"),
                bearer_token=job.get("bearer_token"),
                tls_verify=job.get("tls_verify", True),
                ca_cert_path=job.get("ca_cert_path"),
            )

        try:
            if proto == DeviceProtocol.HOST_METRICS:
                records, avail, unsupp = await poll_host_metrics(tmp_device)
            elif proto == DeviceProtocol.SNMP:
                records, avail, unsupp = await poll_snmp_device(tmp_device)
            elif proto == DeviceProtocol.RESTCONF:
                records, avail, unsupp = await poll_restconf_device(tmp_device)
            else:
                records, avail, unsupp = await probe_tcp_reachability(tmp_device)

            if records and self.settings.collector_id and self.settings.session_token:
                rec_dict = records[0].model_dump()
                await self.client.push_probe_job_result(
                    collector_id=self.settings.collector_id,
                    session_token=self.settings.session_token,
                    job_id=job_id,
                    result_payload={
                        "job_id": job_id,
                        "device_id": dev_id,
                        "ip": target_ip,
                        "protocol": proto_str,
                        "port": port,
                        "status": rec_dict.get("device_status", "UP"),
                        "record": rec_dict,
                        "metrics_available": avail,
                        "metrics_unsupported": unsupp,
                        "collector_id": self.settings.collector_id,
                    },
                )
        except Exception as e:
            logger.error("Failed to execute on-demand probe job %s: %s", job_id, e)

    async def _probe_dispatch_loop(self) -> None:
        """
        Polls cloud backend for on-demand IP probe requests and executes them immediately.
        Enables 1-second responsiveness for user-initiated IP checks through this local collector.
        """
        while self._running:
            if self.settings.collector_id and self.settings.session_token:
                try:
                    jobs = await self.client.fetch_pending_probe_jobs(
                        self.settings.collector_id, self.settings.session_token
                    )
                    for job in jobs:
                        asyncio.create_task(self._execute_probe_job(job))
                except Exception as e:
                    logger.debug("Probe job poll: %s", e)
            await asyncio.sleep(1)

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
        self._tasks.append(asyncio.create_task(self._probe_dispatch_loop()))
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

