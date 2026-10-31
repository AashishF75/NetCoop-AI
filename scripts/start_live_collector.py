"""
Start a background live collector for NetCoop AI.
Enrolls with the local backend, registers host metrics, local probes,
and the live phone hotspot gateway reachability probe, streaming live telemetry continuously.
"""
import sys
import os
import asyncio
import socket
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import requests
from collector.config import (
    CollectorSettings,
    LocalDeviceConfig,
    DeviceProtocol,
    save_collector_config,
    detect_default_gateway,
)
from collector.agent import NetworkCollectorAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("LiveCollectorRunner")

BACKEND_URL = "http://127.0.0.1:8000"
DETECTED_GW = detect_default_gateway() or "10.244.241.91"
GATEWAY_IP = os.environ.get("GATEWAY_IP", DETECTED_GW)

async def main():
    logger.info("Dynamically resolved default gateway: %s", GATEWAY_IP)
    hostname = socket.gethostname()
    host_dev_id = f"HOST-{hostname[:12].upper()}"
    gw_ping_id = f"GATEWAY-PING-{GATEWAY_IP.replace('.', '-')}"
    gw_tcp_id = f"GATEWAY-TCP80-{GATEWAY_IP.replace('.', '-')}"

    # Enroll
    enroll_resp = requests.post(
        f"{BACKEND_URL}/api/collectors/enroll",
        json={"name": "Live-Edge-Collector", "backend_url": BACKEND_URL}
    )
    enroll_resp.raise_for_status()
    enroll_data = enroll_resp.json()
    collector_id = enroll_data["collector_id"]
    token = enroll_data["enrollment_token"]
    logger.info("Enrolled collector: %s", collector_id)

    # Register devices on backend
    devices_to_register = [
        {
            "device_id": host_dev_id,
            "name": f"Collector Host Appliance ({hostname})",
            "device_type": "server",
            "ip": "127.0.0.1",
            "port": 8000,
            "protocol": "HOST_METRICS",
        },
        {
            "device_id": gw_ping_id,
            "name": f"Default Gateway Ping ({GATEWAY_IP})",
            "device_type": "router",
            "ip": GATEWAY_IP,
            "port": 0,
            "protocol": "PING_PROBE",
        },
        {
            "device_id": gw_tcp_id,
            "name": f"Default Gateway TCP80 ({GATEWAY_IP}:80)",
            "device_type": "router",
            "ip": GATEWAY_IP,
            "port": 80,
            "protocol": "TCP_PROBE",
        },
    ]

    for dev in devices_to_register:
        requests.post(
            f"{BACKEND_URL}/api/collectors/{collector_id}/devices",
            json=dev,
        )

    settings = CollectorSettings(
        backend_url=BACKEND_URL,
        collector_id=collector_id,
        collector_name="Live-Edge-Collector",
        enrollment_token=token,
        heartbeat_interval_sec=10,
        default_gateway=GATEWAY_IP,
        devices=[
            LocalDeviceConfig(
                device_id=host_dev_id,
                name=f"Collector Host Appliance ({hostname})",
                device_type="server",
                host="127.0.0.1",
                port=8000,
                protocol=DeviceProtocol.HOST_METRICS,
                polling_interval_sec=10,
            ),
            LocalDeviceConfig(
                device_id=gw_ping_id,
                name=f"Default Gateway Ping ({GATEWAY_IP})",
                device_type="router",
                host=GATEWAY_IP,
                port=0,
                protocol=DeviceProtocol.PING_PROBE,
                polling_interval_sec=10,
            ),
            LocalDeviceConfig(
                device_id=gw_tcp_id,
                name=f"Default Gateway TCP80 ({GATEWAY_IP}:80)",
                device_type="router",
                host=GATEWAY_IP,
                port=80,
                protocol=DeviceProtocol.TCP_PROBE,
                polling_interval_sec=10,
            ),
        ]
    )

    save_collector_config(settings)
    agent = NetworkCollectorAgent(settings)
    logger.info("Starting collector agent loops...")
    await agent.start()
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
