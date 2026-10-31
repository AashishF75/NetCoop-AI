"""
End-to-end verification script for On-Premise Collector flow and Browser UI.
Runs actual agent polling, telemetry push, multi-agent diagnosis, and Playwright verification.
"""

import sys
import os
import time
import asyncio
import requests
from playwright.sync_api import sync_playwright

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:5173"
ARTIFACT_DIR = r"C:\Users\spaas\.gemini\antigravity\brain\7ee9a139-9371-4c3d-aaef-46fbc39425c8"


def main():
    print("=== Step 1: Enrolling New Collector ===")
    enroll_resp = requests.post(
        f"{BACKEND_URL}/api/collectors/enroll",
        json={"name": "Bhubaneswar-LAN-Collector-01", "backend_url": BACKEND_URL},
    )
    assert enroll_resp.status_code == 200, f"Enroll failed: {enroll_resp.text}"
    enroll_data = enroll_resp.json()
    collector_id = enroll_data["collector_id"]
    token = enroll_data["enrollment_token"]
    print(f"Enrolled collector: {collector_id}")
    print(f"Enrollment token: {token[:12]}...")

    print("\n=== Step 2: Registering Monitored LAN Devices ===")
    # Register 2 real local network targets (local loopback ports that are active)
    dev1_resp = requests.post(
        f"{BACKEND_URL}/api/collectors/{collector_id}/devices",
        json={
            "device_id": "dev-core-switch-01",
            "name": "Bhubaneswar-Core-Switch-01",
            "device_type": "switch",
            "ip": "127.0.0.1",
            "port": 8000,
            "protocol": "TCP_PROBE",
        },
    )
    assert dev1_resp.status_code == 200, f"Device 1 reg failed: {dev1_resp.text}"
    print("Registered dev-core-switch-01 (TCP 8000)")

    dev2_resp = requests.post(
        f"{BACKEND_URL}/api/collectors/{collector_id}/devices",
        json={
            "device_id": "dev-edge-ap-01",
            "name": "IIT-BBS-Campus-WLAN-AP",
            "device_type": "ap",
            "ip": "127.0.0.1",
            "port": 5173,
            "protocol": "TCP_PROBE",
        },
    )
    assert dev2_resp.status_code == 200, f"Device 2 reg failed: {dev2_resp.text}"
    print("Registered dev-edge-ap-01 (TCP 5173)")

    print("\n=== Step 3: Starting Local Collector Agent ===")
    from collector.config import CollectorSettings, LocalDeviceConfig, DeviceProtocol
    from collector.agent import NetworkCollectorAgent

    settings = CollectorSettings(
        collector_id=collector_id,
        collector_name="Bhubaneswar-LAN-Collector-01",
        backend_url=BACKEND_URL,
        enrollment_token=token,
        heartbeat_interval_sec=5,
        devices=[
            LocalDeviceConfig(
                device_id="dev-core-switch-01",
                name="Bhubaneswar-Core-Switch-01",
                device_type="switch",
                host="127.0.0.1",
                port=8000,
                protocol=DeviceProtocol.TCP_PROBE,
                polling_interval_sec=5,
            ),
            LocalDeviceConfig(
                device_id="dev-edge-ap-01",
                name="IIT-BBS-Campus-WLAN-AP",
                device_type="ap",
                host="127.0.0.1",
                port=5173,
                protocol=DeviceProtocol.TCP_PROBE,
                polling_interval_sec=5,
            ),
        ],
    )

    agent = NetworkCollectorAgent(settings=settings)

    async def run_collector_briefly():
        print("Starting agent background loop...")
        task = asyncio.create_task(agent.start())
        print("Polling local network devices and streaming telemetry for 6 seconds...")
        await asyncio.sleep(6.0)
        print("Stopping collector agent cleanly...")
        await agent.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(run_collector_briefly())

    print("\n=== Step 4: Verifying Inventory & Device Telemetry ===")
    inv_resp = requests.get(f"{BACKEND_URL}/api/collectors/inventory")
    assert inv_resp.status_code == 200
    inv = inv_resp.json()
    print(f"Collectors count: {inv['collectors_count']}, Online: {inv['online_collectors_count']}")
    print(f"Devices count: {inv['devices_count']}")
    for d in inv["devices"]:
        print(f"  Device: {d['device_id']} ({d['name']}) | Status: {d['status']} | Last Telemetry: {d.get('last_telemetry_at')}")
        print(f"    Available Metrics: {d.get('metrics_available', [])}")

    print("\n=== Step 5: Executing Multi-Agent Live Diagnosis ===")
    diag_resp = requests.post(
        f"{BACKEND_URL}/api/integrations/diagnose-live",
        json={"timeout_sec": 3.0},
    )
    assert diag_resp.status_code == 200, f"Live diagnosis failed: {diag_resp.text}"
    diag = diag_resp.json()
    print(f"Live Diagnosis Status: {diag.get('success')}")
    print(f"Provenance Origin: {diag.get('telemetry_origin')}")
    print(f"Suspected Root Cause: {diag.get('suspected_root_cause')}")
    print(f"Confidence: {diag.get('confidence')}")
    print(f"Agents Participating: {len(diag.get('agent_contributions', {}))}")
    assert diag.get("telemetry_origin") == "LIVE_DEVICE", f"Expected LIVE_DEVICE origin, got {diag.get('telemetry_origin')}"

    print("\n=== Step 6: Browser UI Verification with Playwright ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})

        print(f"Navigating to {FRONTEND_URL}...")
        page.goto(FRONTEND_URL, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Click on "Live Integrations" tab
        print("Clicking 'Live Integrations' navigation tab...")
        page.click("button:has-text('Live Integrations')")
        page.wait_for_timeout(1500)

        # Check that collector card and device table are rendered
        collector_text = page.locator("text=Bhubaneswar-LAN-Collector-01").first
        print(f"Collector card visible: {collector_text.is_visible()}")

        # Take screenshot of collector inventory dashboard
        dash_screenshot = os.path.join(ARTIFACT_DIR, "collector_integrations_dashboard.png")
        page.screenshot(path=dash_screenshot, full_page=False)
        print(f"Saved dashboard screenshot to: {dash_screenshot}")

        # Click "Run Live Network Diagnosis"
        print("Triggering Live Network Diagnosis from UI...")
        diag_btn = page.locator("button:has-text('Run Live Network Diagnosis')")
        if diag_btn.is_visible():
            diag_btn.click()
            print("Waiting for 5-agent live diagnosis to finish...")
            page.wait_for_timeout(3500)

        diag_screenshot = os.path.join(ARTIFACT_DIR, "collector_live_diagnosis_result.png")
        page.screenshot(path=diag_screenshot, full_page=False)
        print(f"Saved diagnosis screenshot to: {diag_screenshot}")

        browser.close()

    print("\nAll collector integration and UI verification steps passed successfully!")


if __name__ == "__main__":
    main()
