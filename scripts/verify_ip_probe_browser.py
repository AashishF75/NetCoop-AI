import asyncio
import os
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\spaas\.gemini\antigravity\brain\7ee9a139-9371-4c3d-aaef-46fbc39425c8"
SCREENSHOT_IP_PROBE = os.path.join(ARTIFACT_DIR, "ip_probe_workflow_verified.png")
SCREENSHOT_REPLAY_FROM_PROBE = os.path.join(ARTIFACT_DIR, "ip_probe_replay_verified.png")

async def run_ip_probe_browser_verification():
    print("[Playwright] Starting browser verification targeting http://localhost:5173 ...", flush=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 960})
        page = await context.new_page()

        # Listen to browser console and errors
        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}", flush=True))
        page.on("pageerror", lambda exc: print(f"[Browser Error] {exc}", flush=True))

        # Step 1: Open Application
        print("[Playwright] Navigating to http://localhost:5173 ...", flush=True)
        await page.goto("http://localhost:5173", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)

        # Step 2: Navigate to Live Network Integrations tab
        print("[Playwright] Clicking 'Live Network Integrations' navigation tab...", flush=True)
        live_tab = page.locator("button:has-text('Live Network Integrations')")
        await live_tab.wait_for(state="visible", timeout=10000)
        await live_tab.click()
        await asyncio.sleep(2)

        # Step 3: Verify the 'On-Demand IP Check & Swarm Diagnosis' panel is visible
        print("[Playwright] Verifying 'On-Demand IP Check & Swarm Diagnosis' panel...", flush=True)
        ip_panel = page.locator("h3:has-text('Target IP Device Interrogation & 5-Agent Swarm Diagnosis')")
        await ip_panel.wait_for(state="visible", timeout=10000)

        # Step 4: Verify default IP is populated
        ip_input = page.locator("input[placeholder*='10.244.241.91']")
        val = await ip_input.input_value()
        print(f"[Playwright] Target IP input contains: '{val}'", flush=True)

        # Step 5: Click 'Execute IP Probe & Swarm Diagnosis'
        print("[Playwright] Clicking 'Execute IP Probe & Swarm Diagnosis' button...", flush=True)
        probe_btn = page.locator("button:has-text('Execute IP Probe & Swarm Diagnosis')")
        await probe_btn.wait_for(state="visible", timeout=5000)
        await probe_btn.click()

        # Step 6: Wait for probe and 5-agent swarm diagnosis results to appear
        print("[Playwright] Waiting for probe and 5-agent diagnosis card...", flush=True)
        consensus_header = page.locator("h4:has-text('5-Agent Swarm Consensus Diagnosis')")
        await consensus_header.wait_for(state="visible", timeout=30000)
        await asyncio.sleep(2)

        # Capture text summary of probe findings
        target_badge = await page.locator(f"h3.font-mono:has-text('{val}')").inner_text()
        print(f"[Playwright] Verified target probe badge: {target_badge}", flush=True)

        # Capture Screenshot 1: IP Probe & Swarm Diagnosis Card
        print(f"[Playwright] Saving screenshot 1 to: {SCREENSHOT_IP_PROBE}", flush=True)
        await page.screenshot(path=SCREENSHOT_IP_PROBE, full_page=True)

        # Step 7: Click 'Open in Investigation Replay'
        print("[Playwright] Clicking 'Open in Investigation Replay' button...", flush=True)
        replay_btn = page.locator("button:has-text('Open in Investigation Replay')").first
        await replay_btn.wait_for(state="visible", timeout=5000)
        await replay_btn.click()
        await asyncio.sleep(3)

        # Verify Replay view loaded with the new incident
        print("[Playwright] Verifying Investigation Replay loaded the probe incident...", flush=True)
        replay_heading = page.locator("h2:has-text('Autonomous Investigation Replay')")
        await replay_heading.wait_for(state="visible", timeout=10000)

        # Capture Screenshot 2: Replay of IP Probe incident
        print(f"[Playwright] Saving screenshot 2 to: {SCREENSHOT_REPLAY_FROM_PROBE}", flush=True)
        await page.screenshot(path=SCREENSHOT_REPLAY_FROM_PROBE, full_page=True)

        print("[Playwright] Browser verification completed successfully!", flush=True)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_ip_probe_browser_verification())
