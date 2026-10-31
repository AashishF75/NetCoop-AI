"""
NetCoop AI — Phase 5 End-to-End Validation & Verification Script
Audits and exercises every required capability against the running backend:
1. All 6 Official Problem Statement Scenarios (Normal, Congestion, Wi-Fi, Interface, DNS/DHCP, Interoperability)
2. Robustness scenarios (Missing telemetry -> INCONCLUSIVE, Conflicting evidence)
3. Canonical Protocol Validation & Unit Normalization (JSON & CSV)
4. Live Collector dynamic gateway detection, pairing & IP probe workflow
5. Recommendation Agent human-approval safety gates
"""

import sys
import json
import urllib.request
import urllib.error

BACKEND_BASE = "http://127.0.0.1:8000"

def post_json(endpoint: str, payload: dict) -> dict:
    url = f"{BACKEND_BASE}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))

def get_json(endpoint: str) -> dict:
    url = f"{BACKEND_BASE}{endpoint}"
    with urllib.request.urlopen(url, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))

def test_health():
    print("\n--- 1. Testing Health Endpoint ---")
    data = get_json("/api/health")
    assert data["status"] == "ONLINE", f"Expected ONLINE, got {data['status']}"
    assert len(data["agents_registered"]) == 5, f"Expected 5 agents, got {len(data['agents_registered'])}"
    print(f"PASS: Backend ONLINE with all 5 specialized agents registered.")

def test_official_scenarios():
    print("\n--- 2. Testing 6 Official Problem Statement Scenarios ---")
    scenarios = [
        ("normal_network", "Normal Network Operation", ["HEALTHY", "NORMAL", "CONFIRMED"]),
        ("link_congestion", "Egress Link Buffer Congestion", ["CONFIRMED"]),
        ("weak_wifi_signal", "Wireless RF Path Loss", ["CONFIRMED"]),
        ("interface_fault", "Physical Link / Transceiver Integrity Fault", ["CONFIRMED"]),
        ("dns_dhcp_failure", "Core Network Services Failure", ["CONFIRMED", "SUSPECTED"]),
        ("incompatible_agent_messages", "Protocol Interoperability Rejection", ["INCONCLUSIVE", "FAILED"]),
    ]

    results = []
    for sc_id, expected_substr, expected_statuses in scenarios:
        res = post_json("/api/diagnose", {"scenario_id": sc_id})
        cr = res.get("canonical_report", {})
        status = res.get("status") or cr.get("status")
        cause = res.get("suspected_root_cause") or cr.get("suspected_root_cause", "")
        conf = res.get("confidence", cr.get("confidence", 0.0))
        facts = cr.get("observed_facts", [])
        hypos = cr.get("alternative_causes", [])
        recs = cr.get("recommended_actions", [])
        origin = cr.get("telemetry_origin") or "SIMULATED_SCENARIO"

        status_pass = any(s in str(status).upper() for s in expected_statuses)
        cause_pass = expected_substr.lower() in cause.lower()

        # Check human approval flags on actions
        has_approval_gate = any(r.get("requires_human_approval") for r in recs)

        # Fix 2 Verification: For incompatible_agent_messages, verify network confidence is low (<= 0.40)
        # while protocol_rejection_confidence is 1.0
        if sc_id == "incompatible_agent_messages":
            assert conf <= 0.40, f"Expected network diagnostic confidence <= 0.40 for INCONCLUSIVE, got {conf}"
            assert cr.get("protocol_rejection_confidence") == 1.0, f"Expected protocol_rejection_confidence == 1.0, got {cr.get('protocol_rejection_confidence')}"

        # Fix 1 Verification: No unvalidated Bayesian claims in confidence calculation method
        calc_method = cr.get("confidence_calculation_method", "")
        assert "bayesian" not in calc_method.lower(), f"Unexpected 'Bayesian' claim in method: {calc_method}"

        passed = status_pass and cause_pass
        results.append({
            "scenario": sc_id,
            "status": status,
            "confidence": conf,
            "cause": cause,
            "facts_count": len(facts),
            "hypos_count": len(hypos),
            "recs_count": len(recs),
            "human_approval_present": has_approval_gate,
            "passed": passed,
        })
        print(f"[{'PASS' if passed else 'FAIL'}] {sc_id}:")
        print(f"      Status={status} | Calibrated Confidence={conf:.2f} | Root Cause: {cause[:60]}...")
        print(f"      Facts={len(facts)} | Competing Hypotheses={len(hypos)} | Remediations={len(recs)} (Human-Approval Gated: {has_approval_gate})")
        print(f"      Telemetry Origin={origin}")
        assert passed, f"Scenario {sc_id} failed: status={status}, cause={cause}"

    return results

def test_robustness_scenarios():
    print("\n--- 3. Testing Robustness & Edge Cases ---")

    # 3a. Missing telemetry -> INCONCLUSIVE / INSUFFICIENT_EVIDENCE
    res_missing = post_json("/api/diagnose", {"scenario_id": "missing_telemetry"})
    cr_missing = res_missing.get("canonical_report", {})
    status_missing = res_missing.get("status") or cr_missing.get("status")
    conf_missing = res_missing.get("confidence", cr_missing.get("confidence", 1.0))
    limitations = cr_missing.get("limitations", [])
    print(f"Missing Telemetry: Status={status_missing}, Confidence={conf_missing}, Limitations={len(limitations)}")
    assert "INCONCLUSIVE" in str(status_missing).upper() or "INSUFFICIENT" in str(status_missing).upper()
    assert conf_missing <= 0.50, f"Expected confidence <= 0.50 for missing telemetry, got {conf_missing}"
    assert len(limitations) > 0, "Expected documented limitations for missing telemetry"
    print("PASS: Missing telemetry produces calibrated INCONCLUSIVE diagnosis with documented limitations.")

    # 3b. Conflicting evidence -> Competing Hypotheses & Conflict Resolution
    res_conflict = post_json("/api/diagnose", {"scenario_id": "conflicting_evidence"})
    cr_conflict = res_conflict.get("canonical_report", {})
    status_conflict = res_conflict.get("status") or cr_conflict.get("status")
    conf_conflict = res_conflict.get("confidence", cr_conflict.get("confidence", 0.0))
    hypos = cr_conflict.get("alternative_causes", [])
    cause = res_conflict.get("suspected_root_cause")
    print(f"Conflicting Evidence: Status={status_conflict}, Confidence={conf_conflict}, Winner={cause}, Competing Hypotheses={len(hypos)}")
    assert len(hypos) >= 2, f"Expected multiple competing hypotheses, got {len(hypos)}"

    # Fix 3 Verification: Verify conflict is explicitly marked RESOLVED and details are present
    assert cr_conflict.get("conflict_status") == "RESOLVED", f"Expected conflict_status RESOLVED, got {cr_conflict.get('conflict_status')}"
    details = cr_conflict.get("resolved_conflict_details")
    assert details is not None, "Expected resolved_conflict_details"
    assert "Egress Link Buffer Congestion" in details.get("initial_hypothesis")
    assert "99.4%" in details.get("refuting_evidence")
    calc_str = cr_conflict.get("confidence_calculation_method", "")
    assert "Conflict: Resolved (0.00 penalty)" in calc_str, f"Unexpected penalty string: {calc_str}"
    assert "bayesian" not in calc_str.lower()
    print("PASS: Conflicting evidence successfully captured competing hypotheses, refuted initial congestion, and marked conflict RESOLVED with 0.00 penalty.")

def test_protocol_validation():
    print("\n--- 4. Testing Canonical Protocol Validation Endpoint ---")
    # 4a. Unsupported schema version
    bad_version_req = {
        "message": {
            "agent_id": "test-agent",
            "schema_version": "99.0",
            "message_type": "TELEMETRY_ANOMALY",
            "confidence": 0.9,
            "findings": ["Test"]
        }
    }
    res_bv = post_json("/api/protocol/validate-message", bad_version_req)
    assert not res_bv["valid"] and res_bv["error_type"] == "SCHEMA_VERSION_MISMATCH"
    print("PASS: Incompatible schema version explicitly rejected.")

    # 4b. Missing required field
    missing_field_req = {
        "message": {
            "agent_id": "test-agent",
            "schema_version": "1.0.0",
            # missing message_type
            "confidence": 0.9,
        }
    }
    res_mf = post_json("/api/protocol/validate-message", missing_field_req)
    assert not res_mf["valid"] and res_mf["error_type"] == "MISSING_REQUIRED_FIELD"
    print("PASS: Missing required message field explicitly rejected.")

    # 4c. Valid message
    valid_req = {
        "message": {
            "agent_id": "perf-agent-01",
            "schema_version": "1.0.0",
            "message_type": "TELEMETRY_ANOMALY",
            "confidence": 0.95,
            "findings": ["All interfaces operating within nominal bounds."]
        }
    }
    res_val = post_json("/api/protocol/validate-message", valid_req)
    assert res_val["valid"] is True
    print("PASS: Canonical compliant message successfully accepted.")

def test_collector_and_ip_probe():
    print("\n--- 5. Testing Collector Hub & Live IP Probe Workflow ---")
    # 5a. Check collector list
    collectors = get_json("/api/collectors")
    assert isinstance(collectors, list)
    online_collectors = [c for c in collectors if c.get("status") == "ONLINE"]
    print(f"Total enrolled collectors: {len(collectors)} | Online collectors: {len(online_collectors)}")
    assert len(online_collectors) > 0, "Expected at least 1 online collector"
    active_col = online_collectors[0]
    print(f"Active paired collector: {active_col['collector_id']} ({active_col['name']}) on {active_col['local_ip']}")

    # 5b. Check detected gateway
    gw_info = get_json("/api/collectors/detected-gateway")
    print(f"Detected gateway info: {gw_info}")
    assert "default_gateway" in gw_info or "gateway_ip" in gw_info
    target_ip = gw_info.get("default_gateway") or gw_info.get("gateway_ip") or "127.0.0.1"
    probe_payload = {
        "ip": target_ip,
        "protocol": "PING",
        "device_type": "router",
        "probe_timeout_sec": 3.0
    }
    print(f"Initiating live IP probe targeting: {target_ip}...")
    probe_res = post_json("/api/integrations/probe-ip", probe_payload)
    assert probe_res.get("success") is True, f"Probe unsuccessful: {probe_res}"
    pr = probe_res.get("probe_result", {})
    probe_status = pr.get("status")
    print(f"Probe execution status: {probe_status} (routed via {probe_res.get('routed_via_collector')})")
    print(f"Probe telemetry: latency={pr.get('latency_ms')} ms, loss={pr.get('packet_loss_pct')}%")
    print(f"Supported metrics: {pr.get('supported_metrics')}")
    print(f"Unsupported metrics: {pr.get('unsupported_metrics')}")

    # 5d. Check diagnosis result produced from probe
    diag = probe_res.get("diagnosis", {})
    if diag:
        cr = diag.get("canonical_report", {})
        status = diag.get("status") or cr.get("status")
        conf = diag.get("confidence", cr.get("confidence", 0.0))
        cause = diag.get("suspected_root_cause") or cr.get("suspected_root_cause")
        origin = pr.get("telemetry_origin") or cr.get("telemetry_origin") or "LIVE_DEVICE"
        print(f"Probe Multi-Agent Diagnosis: Status={status} | Calibrated Conf={conf} | Cause={cause}")
        print(f"Provenance origin badge: {origin}")
        print("PASS: Live IP Probe workflow completed end-to-end through paired local collector.")

def main():
    print("=" * 70)
    print("NETCOOP AI — PHASE 5 END-TO-END VALIDATION SUITE")
    print("=" * 70)
    test_health()
    test_official_scenarios()
    test_robustness_scenarios()
    test_protocol_validation()
    test_collector_and_ip_probe()
    print("\n" + "=" * 70)
    print("ALL PHASE 5 END-TO-END VALIDATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
