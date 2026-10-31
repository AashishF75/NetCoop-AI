import asyncio
import os
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\spaas\.gemini\antigravity\brain\7ee9a139-9371-4c3d-aaef-46fbc39425c8"
SCREENSHOT_1 = os.path.join(ARTIFACT_DIR, "live_network_integration_verified.png")
SCREENSHOT_2 = os.path.join(ARTIFACT_DIR, "live_network_replay_verified.png")

async def run_browser_verification():
    print("Starting Playwright browser verification targeting http://localhost:5173 ...", flush=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 960})
        page = await context.new_page()

        # Step 1: Open Application
        print("Navigating to http://localhost:5173 ...", flush=True)
        await page.goto("http://localhost:5173", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)

        # Step 2: Navigate to Live Integrations tab
        print("Clicking 'Live Integrations' tab...", flush=True)
        live_tab = page.locator("button:has-text('Live Integrations')")
        await live_tab.wait_for(state="visible", timeout=10000)
        await live_tab.click()
        await asyncio.sleep(3)

        # Step 3: Verify Collector and Devices
        print("Verifying Collector Hub UI elements...", flush=True)
        online_count = await page.locator(":has-text('ONLINE')").count()
        streaming_count = await page.locator(":has-text('STREAMING_LIVE')").count()
        print(f"Elements matching ONLINE: {online_count}, elements matching STREAMING_LIVE: {streaming_count}", flush=True)

        # Step 4: Click 'Run Live Diagnosis'
        print("Locating 'Run Live Diagnosis' button...", flush=True)
        diag_btn = page.locator("button:has-text('Run Live Diagnosis')")
        await diag_btn.wait_for(state="visible", timeout=10000)
        print("Clicking 'Run Live Diagnosis' button...", flush=True)
        await diag_btn.click()

        # Step 5: Wait for Live Diagnosis Banner to appear
        print("Waiting for live multi-agent diagnosis banner to appear...", flush=True)
        banner = page.locator("h3:has-text('Live Multi-Agent Diagnosis Complete')")
        await banner.wait_for(state="visible", timeout=30000)
        await asyncio.sleep(2)

        banner_text = await page.locator(".bg-emerald-950\\/40").inner_text()
        print("=" * 60, flush=True)
        print("DIAGNOSIS BANNER INNER TEXT:\n" + banner_text, flush=True)
        print("=" * 60, flush=True)

        # Step 6: Take first screenshot
        print(f"Saving live integration screenshot to {SCREENSHOT_1} ...", flush=True)
        await page.screenshot(path=SCREENSHOT_1, full_page=True)
        print("Screenshot 1 saved successfully.", flush=True)

        # Step 7: Click 'Open in Investigation Replay'
        print("Clicking 'Open in Investigation Replay' button...", flush=True)
        replay_btn = page.locator("button:has-text('Open in Investigation Replay')")
        await replay_btn.wait_for(state="visible", timeout=10000)
        await replay_btn.click()
        await asyncio.sleep(3)

        # Step 8: Verify Investigation Replay View
        print("Verifying Investigation Replay view with 5 agents...", flush=True)
        for agent_name in ["Performance", "Infrastructure", "Connectivity", "Correlation", "Recommendation"]:
            matches = await page.locator(f":has-text('{agent_name}')").count()
            print(f"Replay view contains '{agent_name}': {matches > 0} ({matches} matches)", flush=True)

        # Step 9: Take second screenshot
        print(f"Saving live investigation replay screenshot to {SCREENSHOT_2} ...", flush=True)
        await page.screenshot(path=SCREENSHOT_2, full_page=True)
        print("Screenshot 2 saved successfully.", flush=True)

        await browser.close()
        print("Browser verification completed successfully!", flush=True)

if __name__ == "__main__":
    asyncio.run(run_browser_verification())
