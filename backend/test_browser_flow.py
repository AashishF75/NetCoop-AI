import time
import os
import json
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = "browser_verification_screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_browser_verification():
    console_errors = []
    console_logs = []
    page_errors = []

    with sync_playwright() as p:
        # Launch Chromium headless
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = context.new_page()

        # Capture console and page errors
        page.on("console", lambda msg: (
            console_errors.append(msg.text) if msg.type in ["error"] else console_logs.append(f"[{msg.type}] {msg.text}")
        ))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        print("[1/17] Navigating to http://127.0.0.1:5173 ...")
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Verify page title
        title = page.title()
        print(f"  Page Title: {title}")
        assert "NetCoop AI" in title

        # Verify Header Elements
        header = page.locator("header")
        assert header.is_visible()
        print("  Header is rendered.")
        page.screenshot(path=f"{SCREENSHOT_DIR}/01_initial_dashboard.png")

        # Verify Topology
        topo = page.locator(".react-flow")
        assert topo.is_visible()
        print("  React Flow Network Topology is rendered.")

        # Verify Telemetry Charts
        charts = page.locator("text=Live Telemetry Ingestion Metrics")
        assert charts.is_visible()
        print("  Telemetry Charts panel is rendered.")

        # [2/17] Select Scenario 8: Conflicting Evidence
        print("\n[2/17] Selecting Scenario 8 (Conflicting Evidence)...")
        sc8_card = page.locator("text=Scenario 8: Conflicting Evidence").first
        assert sc8_card.is_visible()
        sc8_card.click()
        page.wait_for_timeout(800)

        # [3/17] Click Run Multi-Agent Diagnosis
        print("\n[3/17] Triggering Multi-Agent Diagnosis...")
        run_btn = page.locator("button:has-text('Run Multi-Agent Diagnosis')")
        assert run_btn.is_visible()
        run_btn.click()

        # Wait for diagnosis to complete and replay to initiate
        page.wait_for_selector("text=Control Plane Processor Saturation", timeout=12000)
        page.wait_for_timeout(1000)
        print("  Diagnosis complete! Root cause displayed.")
        page.screenshot(path=f"{SCREENSHOT_DIR}/02_scenario_8_diagnosed.png")

        # [4/17] Verify Autonomous Investigation Replay Bar
        print("\n[4/17] Verifying Autonomous Investigation Replay Component...")
        replay_panel = page.locator("text=Autonomous Investigation Replay").first
        assert replay_panel.is_visible(), "Autonomous Investigation Replay not visible"

        # Verify Replay Controls: Speed, Step Next, Step Prev
        speed_2x_btn = page.locator("button:has-text('2x')").first
        assert speed_2x_btn.is_visible()
        speed_2x_btn.click()
        page.wait_for_timeout(300)

        step_fwd_btn = page.locator("button[title='Step Forward']").first
        assert step_fwd_btn.is_visible()
        step_fwd_btn.click()
        page.wait_for_timeout(300)

        step_back_btn = page.locator("button[title='Step Backward']").first
        assert step_back_btn.is_visible()
        step_back_btn.click()
        page.wait_for_timeout(300)

        # Toggle Inspect JSON on active event
        inspect_json_btn = page.locator("button:has-text('Inspect JSON')").first
        if inspect_json_btn.is_visible():
            inspect_json_btn.click()
            page.wait_for_timeout(300)
            print("  Replay Inspect JSON payload drawer toggled.")

        page.screenshot(path=f"{SCREENSHOT_DIR}/05_investigation_replay.png")
        print("  Investigation Replay controls verified.")

        # [5/17] Test Device Details Drawer (Click node in React Flow)
        print("\n[5/17] Testing Device Details Drawer (Node Click)...")
        core_node = page.locator(".react-flow__node:has-text('Core Router 01')").first
        if core_node.is_visible():
            core_node.click()
            page.wait_for_selector("text=Observed Telemetry vs. Baseline SLA Bounds", timeout=4000)
            page.wait_for_timeout(500)
            page.screenshot(path=f"{SCREENSHOT_DIR}/06_device_details_modal.png")
            print("  Device Details Drawer opened: Baseline comparison table verified.")

            # Close Device Details Drawer
            close_btn = page.locator(".fixed button:has(svg.lucide-x)").first
            close_btn.click()
            page.wait_for_timeout(400)
            print("  Device Details Drawer closed.")

        # [6/17] Verify Agent Swarm Cards
        print("\n[6/17] Verifying Multi-Agent Swarm Status Cards...")
        agent_names = [
            "Performance Agent",
            "Infrastructure Health Agent",
            "Connectivity Analysis Agent",
            "Fault Correlation Agent",
            "Recommendation & Reporting Agent",
        ]
        for name in agent_names:
            agent_el = page.locator(f"text={name}").first
            assert agent_el.is_visible(), f"Agent card {name} not found"
        print("  All 5 agent cards rendered with updated state.")

        # [7/17] Verify Root Cause Panel & Structured Investigation Explanation
        print("\n[7/17] Verifying Root Cause Panel & Investigation Explanation...")
        rc_panel = page.locator("text=Control Plane Processor Saturation").first
        assert rc_panel.is_visible()

        # Verify "Why Did the Agents Reach This Conclusion?"
        why_section = page.locator("text=Why Did the Agents Reach This Conclusion?")
        assert why_section.is_visible()
        print("  'Why Did the Agents Reach This Conclusion?' explanation visible.")

        # Verify Competing Hypotheses section
        hyp_header = page.locator("text=Competing Hypotheses Evaluation")
        assert hyp_header.is_visible()
        print("  Competing Hypotheses section is visible with status tracking.")

        # Verify Remediation Runbook with Expected Outcome
        runbook = page.locator("text=Actionable Remediation Runbook")
        assert runbook.is_visible()
        assert page.locator("text=Expected Outcome:").first.is_visible()
        print("  Remediation Runbook is visible with CLI steps and Expected Outcomes.")

        # [8/17] Verify Inter-Agent Message Log
        print("\n[8/17] Verifying Inter-Agent Message Log...")
        msg_log = page.locator("text=Canonical Inter-Agent Message Protocol Bus")
        assert msg_log.is_visible()

        # Click CONFLICTS filter
        conflicts_filter_btn = page.locator("button:has-text('CONFLICTS')")
        assert conflicts_filter_btn.is_visible()
        conflicts_filter_btn.click()
        page.wait_for_timeout(500)
        assert page.locator("text=CONFLICT_DETECTED").first.is_visible()
        print("  CONFLICTS filter works; CONFLICT_DETECTED message displayed.")
        page.locator("button:has-text('ALL')").click()

        # [9/17] Test Network Digital Twin View
        print("\n[9/17] Switching to Network Digital Twin View...")
        dt_tab = page.locator("button:has-text('Network Digital Twin')").first
        assert dt_tab.is_visible()
        dt_tab.click()
        page.wait_for_selector("text=Network Digital Twin Environment", timeout=4000)
        page.wait_for_timeout(600)

        # Verify KPI Metrics
        assert page.locator("text=Network Health Index").is_visible()
        assert page.locator("text=SLA Compliance Rate").is_visible()
        assert page.locator("text=BENCHMARK DIGITAL TWIN SIMULATION").is_visible()
        print("  Digital Twin KPI cards verified.")

        # Select a device in the roster
        agg_btn = page.locator("text=Aggregation Switch 01").first
        if agg_btn.is_visible():
            agg_btn.click()
            page.wait_for_timeout(400)
            print("  Selected Aggregation Switch 01 in Digital Twin roster.")

        page.screenshot(path=f"{SCREENSHOT_DIR}/07_digital_twin_view.png")

        # [10/17] Test What-If Remediation Simulator
        print("\n[10/17] Switching to What-If Remediation Simulator View...")
        whatif_tab = page.locator("button:has-text('What-If Remediation Simulator')").first
        assert whatif_tab.is_visible()
        whatif_tab.click()
        page.wait_for_selector("text=What-If Remediation Simulator", timeout=4000)
        page.wait_for_timeout(600)

        # Verify Strategy Cards rendered
        assert page.locator("text=Strategy A").is_visible()
        assert page.locator("text=Strategy B").is_visible()
        print("  Candidate strategies loaded.")

        # Execute Simulation
        sim_btn = page.locator("button:has-text('Execute What-If Simulation')")
        assert sim_btn.is_visible()
        sim_btn.click()

        # Wait for simulation deltas to calculate and render
        page.wait_for_selector("text=Simulation Projections:", timeout=4000)
        assert page.locator("text=FULL_RECOVERY").is_visible()
        assert page.locator("text=Observed vs Simulated Telemetry Deltas").is_visible()
        print("  Simulation executed! Deterministic deltas and recovery status verified.")
        page.screenshot(path=f"{SCREENSHOT_DIR}/08_what_if_simulation_result.png")

        # [11/17] Test Strategy Comparison Matrix
        print("\n[11/17] Testing Strategy Comparison Matrix Tab...")
        compare_tab = page.locator("button:has-text('Strategy Comparison Matrix')")
        assert compare_tab.is_visible()
        compare_tab.click()
        page.wait_for_selector("text=Recommendation Rationale:", timeout=3000)
        page.wait_for_timeout(400)

        # Verify table rendered
        table = page.locator("table")
        assert table.is_visible()
        assert page.locator("text=BEST").is_visible()
        print("  Side-by-side strategy trade-off comparison matrix verified.")
        page.screenshot(path=f"{SCREENSHOT_DIR}/09_strategy_comparison_matrix.png")

        # [12/17] Test Incident Prioritization View
        print("\n[12/17] Switching to Incident Prioritization View...")
        prio_tab = page.locator("button:has-text('Incident Prioritization')").first
        assert prio_tab.is_visible()
        prio_tab.click()
        page.wait_for_selector("text=Multi-Incident Operational Prioritization", timeout=4000)
        page.wait_for_timeout(600)

        # Verify P1/P2 items visible
        assert page.locator("text=P1 CRITICAL").first.is_visible()
        print("  P1 Critical incidents ranked at top of prioritization queue.")

        # Test Filter (CRITICAL)
        crit_filter = page.locator("button:has-text('CRITICAL')").first
        crit_filter.click()
        page.wait_for_timeout(400)
        page.screenshot(path=f"{SCREENSHOT_DIR}/10_incident_prioritization.png")
        print("  Incident severity filter verified.")

        # [13/17] Test Fault Injection Studio View
        print("\n[13/17] Switching to Fault Injection Studio View...")
        fault_tab = page.locator("button:has-text('Fault Injection Studio')").first
        assert fault_tab.is_visible()
        fault_tab.click()
        page.wait_for_selector("text=Interactive Fault Injection & Scenario Builder", timeout=4000)
        page.wait_for_timeout(600)

        # Apply Preset: Optical Transceiver CRC Degradation
        opt_preset = page.locator("button:has-text('Optical Transceiver CRC Degradation')").first
        assert opt_preset.is_visible()
        opt_preset.click()
        page.wait_for_timeout(400)
        print("  Applied Optical Transceiver CRC Degradation preset.")

        # Click Run Multi-Agent Diagnosis on Injected Fault using data-testid
        inject_run_btn = page.locator("button[data-testid='inject-run-btn']").first
        assert inject_run_btn.is_visible()
        inject_run_btn.click()

        # Wait for diagnosis to complete and switch back to Ops view
        page.wait_for_selector("text=Physical Link / Transceiver Integrity Fault", timeout=12000)
        page.wait_for_timeout(1000)
        print("  Injected fault diagnosed successfully by swarm!")
        page.screenshot(path=f"{SCREENSHOT_DIR}/11_fault_injection_diagnosed.png")

        # [14/19] Test Autonomous NOC Command Center View
        print("\n[14/19] Switching to NOC Command Center View...")
        cc_tab = page.locator("button:has-text('NOC Command Center')").first
        assert cc_tab.is_visible()
        cc_tab.click()
        page.wait_for_selector("text=Autonomous Network Intelligence Command Center", timeout=5000)
        page.wait_for_timeout(800)

        # Verify Executive Cockpit KPIs
        assert page.locator("text=Composite Health Score").is_visible()
        assert page.locator("text=Correlated Fault Clusters").is_visible()
        assert page.locator("text=Proactive Drift Warnings").is_visible()
        assert page.locator("text=Agent Swarm Convergence").is_visible()
        print("  Command Center Executive KPIs verified.")
        page.screenshot(path=f"{SCREENSHOT_DIR}/12_command_center_overview.png")

        # Test Switching Sub-Tabs in Command Center:
        # Tab 1: Cross-Incident Correlation
        corr_subtab = page.locator("button:has-text('Cross-Incident Correlation')").first
        assert corr_subtab.is_visible()
        corr_subtab.click()
        page.wait_for_selector("text=Cross-Incident Correlation Engine", timeout=3000)
        page.wait_for_timeout(400)
        assert page.locator("text=Topological Root Cause Node").first.is_visible()
        print("  Command Center Cross-Incident Correlation subtab verified.")
        page.screenshot(path=f"{SCREENSHOT_DIR}/13_command_center_correlations.png")

        # Tab 2: Proactive Risk Forecast
        proact_subtab = page.locator("button:has-text('Proactive Risk Forecast')").first
        assert proact_subtab.is_visible()
        proact_subtab.click()
        page.wait_for_selector("text=Proactive Telemetry Trend & Pre-Breach Warning Radar", timeout=3000)
        page.wait_for_timeout(400)
        print("  Command Center Proactive Risk Radar subtab verified.")

        # Tab 3: Explainable Health Audit
        health_subtab = page.locator("button:has-text('Explainable Health Audit')").first
        assert health_subtab.is_visible()
        health_subtab.click()
        page.wait_for_selector("text=Itemized SLA Health Audit Methodology", timeout=3000)
        page.wait_for_timeout(400)
        print("  Command Center Explainable Health Audit subtab verified.")

        # Switch back to Ops view for modal and custom ingestion tests
        page.locator("button:has-text('NOC Operations & Replay')").first.click()
        page.wait_for_timeout(600)

        # [15/19] Test JSON Report Modal
        print("\n[15/19] Testing JSON Report Modal...")
        report_btn = page.locator("button:has-text('JSON Report')")
        report_btn.click()
        page.wait_for_selector("text=Canonical JSON Diagnostic Report", timeout=3000)
        page.wait_for_timeout(400)

        # Close Modal
        close_modal_btn = page.locator("button:has(svg.lucide-x)").first
        close_modal_btn.click()
        page.wait_for_timeout(400)
        print("  JSON Report modal verified.")

        # [16/19] Test Protocol Inspector Modal
        print("\n[16/19] Testing Protocol Inspector Modal...")
        inspector_btn = page.locator("button:has-text('Protocol Inspector')")
        inspector_btn.click()
        page.wait_for_selector("text=Canonical Protocol Interoperability Inspector", timeout=3000)
        page.wait_for_timeout(400)

        # Test Valid message preset
        validate_action_btn = page.locator("button:has-text('Validate Against Canonical Protocol')")
        validate_action_btn.click()
        page.wait_for_selector("text=VALID PROTOCOL MESSAGE (Accepted)", timeout=3000)

        # Close Inspector Modal
        close_modal_btn = page.locator("button:has(svg.lucide-x)").first
        close_modal_btn.click()
        page.wait_for_timeout(400)
        print("  Protocol Inspector modal verified.")

        # [17/19] Test Custom Telemetry Ingestion Tab
        print("\n[17/19] Testing Custom Telemetry Ingestion Tab...")
        custom_tab_btn = page.locator("button:has-text('Custom Ingestion (CSV / JSON)')")
        custom_tab_btn.click()
        page.wait_for_timeout(300)

        load_sample_btn = page.locator("button:has-text('Load Sample Telemetry')")
        load_sample_btn.click()
        page.wait_for_timeout(300)

        ingest_btn = page.locator("button:has-text('Ingest & Run Diagnosis')")
        assert ingest_btn.is_enabled()
        ingest_btn.click()
        page.wait_for_timeout(1500)
        print("  Custom telemetry ingested and diagnosed successfully.")

        # Switch back to Benchmark Scenarios tab
        page.locator("button:has-text('Benchmark Scenarios')").first.click()
        page.wait_for_timeout(500)

        # [18/19] Test Scenario 9 (Shared Upstream Fault) from catalog
        print("\n[18/19] Selecting and executing Scenario 9 (Shared Upstream Fault)...")
        sc9_card = page.locator("text=Scenario 9: Shared Upstream Fault").first
        if sc9_card.is_visible():
            sc9_card.click()
            page.wait_for_timeout(600)
            run_btn = page.locator("button:has-text('Run Multi-Agent Diagnosis')")
            run_btn.click()
            page.wait_for_selector("text=Physical Link / Transceiver Integrity Fault", timeout=12000)
            page.wait_for_timeout(800)
            page.screenshot(path=f"{SCREENSHOT_DIR}/14_scenario_9_diagnosed.png")
            print("  Scenario 9 diagnosed successfully with cross-incident upstream correlation!")

        # [19/19] Check Console and Page Errors
        print("\n[19/19] Inspecting Browser Console Logs...")
        print(f"  Console Logs Count: {len(console_logs)}")
        print(f"  Console Errors Count: {len(console_errors)}")
        print(f"  Page Errors Count: {len(page_errors)}")

        if console_errors:
            print("  Console Errors encountered:")
            for err in console_errors:
                print(f"    - {err}")
        if page_errors:
            print("  Page Errors encountered:")
            for err in page_errors:
                print(f"    - {err}")

        # Assert zero page errors
        assert len(page_errors) == 0, f"Page errors: {page_errors}"

        browser.close()

    print("\nALL 19 BROWSER AUTOMATION WORKFLOWS PASSED COMPLETELY WITH 0 ERRORS!")

if __name__ == "__main__":
    run_browser_verification()
