"""
Script to enroll and stream genuine live telemetry from the local machine into the running backend.
Runs for a couple cycles to populate fresh telemetry.
"""
import sys
import os
import asyncio
import socket

# Ensure paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from collector.config import CollectorSettings, LocalDeviceConfig, DeviceProtocol
from collector.agent import NetworkCollectorAgent
import requests

BACKEND_URL = "http://127.0.0.1:8000"

def setup_and_stream():
    # 1. Enroll collector via backend API
    enroll_resp = requests.post(
        f"{BACKEND_URL}/api/collectors/enroll",
        json={"name": "Windows-NOC-Edge-Collector", "backend_url": BACKEND_URL}
    )
    enroll_resp.raise_for_status()
    enroll_data = enroll_resp.json()
    collector_id = enroll_data["collector_id"]
    token = enroll_data["enrollment_token"]
    print(f"Enrolled collector: {collector_id} with token: {token}")

    # 2. Register devices on backend
    hostname = socket.gethostname()
    host_dev_id = f"HOST-{hostname[:12].upper()}"
    gw_dev_id = "LAN-Gateway-01"

    requests.post(
        f"{BACKEND_URL}/api/collectors/{collector_id}/devices",
        json={
            "device_id": host_dev_id,
            "name": f"Collector Host Appliance ({hostname})",
            "device_type": "server",
            "ip": "127.0.0.1",
            "port": 8000,
            "protocol": "HOST_METRICS",
        }
    )
    requests.post(
        f"{BACKEND_URL}/api/collectors/{collector_id}/devices",
        json={
            "device_id": gw_dev_id,
            "name": "Local Gateway Probe",
            "device_type": "router",
            "ip": "127.0.0.1",
            "port": 8000,
            "protocol": "TCP_PROBE",
        }
    )

    # 3. Create settings and collector agent
    settings = CollectorSettings(
        backend_url=BACKEND_URL,
        collector_id=collector_id,
        collector_name="Windows-NOC-Edge-Collector",
        enrollment_token=token,
        devices=[
            LocalDeviceConfig(
                device_id=host_dev_id,
                name=f"Collector Host Appliance ({hostname})",
                device_type="server",
                host="127.0.0.1",
                port=8000,
                protocol=DeviceProtocol.HOST_METRICS,
                polling_interval_sec=5,
            ),
            LocalDeviceConfig(
                device_id=gw_dev_id,
                name="Local Gateway Probe",
                device_type="router",
                host="127.0.0.1",
                port=8000,
                protocol=DeviceProtocol.TCP_PROBE,
                polling_interval_sec=5,
            ),
        ]
    )

    agent = NetworkCollectorAgent(settings)

    async def run_cycles():
        await agent.pair_if_needed()
        print("Paired! Session token:", agent.settings.session_token)
        # Send heartbeat
        await agent.client.heartbeat(agent.settings.collector_id, agent.settings.session_token, active_devices=2)
        print("Heartbeat sent.")
        # Poll both devices twice
        for i in range(2):
            print(f"Polling cycle {i+1}...")
            for dev in agent.settings.devices:
                await agent._poll_device(dev)
            await asyncio.sleep(1)
        print("Polling complete.")

    asyncio.run(run_cycles())

    # 4. Check inventory
    inv = requests.get(f"{BACKEND_URL}/api/collectors/inventory").json()
    print("Online collectors:", inv.get("online_collectors_count"))
    for d in inv.get("devices", []):
        if d["device_id"] in (host_dev_id, gw_dev_id):
            print(f"Device {d['device_id']}: status={d['status']}, available_metrics={d['metrics_available']}")

    # 5. Run live diagnosis
    diag = requests.post(f"{BACKEND_URL}/api/integrations/diagnose-live", json={}).json()
    print("Diagnosis success:", diag.get("success"))
    print("Provenance:", diag.get("telemetry_origin"))
    print("Root cause:", diag.get("report", {}).get("suspected_root_cause"))
    print("Confidence:", diag.get("report", {}).get("confidence"))
    print("Incident ID:", diag.get("incident_id"))

if __name__ == "__main__":
    setup_and_stream()

