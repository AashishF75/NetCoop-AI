import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api"

def diagnose_scenario(scenario_id):
    req_data = json.dumps({"scenario_id": scenario_id}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/diagnose",
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def test_all():
    scenarios_meta = json.loads(urllib.request.urlopen(f"{BASE_URL}/scenarios").read().decode("utf-8"))
    print(f"=== TESTING ALL {len(scenarios_meta)} SCENARIOS THROUGH /api/diagnose ===")
    
    results = {}
    for sc in scenarios_meta:
        sc_id = sc["id"]
        res = diagnose_scenario(sc_id)
        results[sc_id] = res
        print(f"\n------------------------------------------------------------")
        print(f"Scenario: {sc['name']} ({sc_id})")
        print(f"Status: {res['status']}")
        print(f"Suspected Root Cause: {res['suspected_root_cause']}")
        print(f"Confidence: {res['confidence']}")
        print(f"Affected Devices: {res['affected_devices']}")
        print(f"Inter-Agent Messages: {len(res['message_bus'])}")
        print(f"Remediation Actions Count: {len(res['canonical_report']['recommended_actions'])}")
        
        # Verify specific scenario expectations
        if sc_id == "normal_network":
            assert res["status"] == "HEALTHY", f"Expected HEALTHY, got {res['status']}"
            assert res["confidence"] >= 0.95
        elif sc_id == "link_congestion":
            assert "Congestion" in res["suspected_root_cause"]
            assert res["status"] == "CONFIRMED"
            assert "Core-Router-01" in res["affected_devices"]
        elif sc_id == "weak_wifi_signal":
            assert "Wireless" in res["suspected_root_cause"] or "RF" in res["suspected_root_cause"] or "Wi-Fi" in res["suspected_root_cause"]
            assert res["status"] == "CONFIRMED"
            assert "AP-02" in res["affected_devices"]
        elif sc_id == "interface_fault":
            assert "Interface" in res["suspected_root_cause"] or "Physical" in res["suspected_root_cause"]
            assert res["status"] == "CONFIRMED"
            assert "Edge-Switch-01" in res["affected_devices"]
        elif sc_id == "dns_dhcp_failure":
            assert "DNS" in res["suspected_root_cause"] or "DHCP" in res["suspected_root_cause"] or "Services" in res["suspected_root_cause"]
            assert res["status"] == "CONFIRMED"
            assert "DNS-Server-01" in res["affected_devices"]
        elif sc_id == "missing_telemetry":
            assert res["status"] == "INCONCLUSIVE"
            assert len(res["canonical_report"]["limitations"]) > 0
            assert res["confidence"] < 0.60
        elif sc_id == "incompatible_agent_messages":
            assert res["status"] == "INCONCLUSIVE"
            assert "Protocol" in res["suspected_root_cause"] or "Schema" in res["suspected_root_cause"]
            assert any(m["message_type"] == "SCHEMA_VERSION_MISMATCH" for m in res["message_bus"])
        elif sc_id == "conflicting_evidence":
            # Scenario 8 checks:
            # Latency is elevated (115ms)
            # Link utilization is 14%
            # CPU utilization is 99.4%
            # Queue drops are zero
            # The correlation agent rejects congestion as the primary cause
            # The final diagnosis identifies Control Plane CPU Starvation / Processor Saturation
            assert "CPU" in res["suspected_root_cause"] or "Processor Saturation" in res["suspected_root_cause"]
            assert res["status"] == "CONFIRMED"
            
            # Check telemetry for Core-Router-01
            core_telemetry = next((t for t in res["telemetry"] if t["device_id"] == "Core-Router-01"), None)
            assert core_telemetry is not None
            assert core_telemetry["latency_ms"] == 115.0, f"Expected 115.0ms, got {core_telemetry['latency_ms']}"
            assert core_telemetry["utilization_pct"] == 14.0, f"Expected 14.0%, got {core_telemetry['utilization_pct']}"
            assert core_telemetry["cpu_utilization_pct"] == 99.4, f"Expected 99.4%, got {core_telemetry['cpu_utilization_pct']}"
            assert core_telemetry["queue_drops_per_sec"] == 0.0, f"Expected 0.0 drops, got {core_telemetry['queue_drops_per_sec']}"
            
            # Check for CONFLICT_DETECTED message in message bus
            conflict_msg = next((m for m in res["message_bus"] if m["message_type"] == "CONFLICT_DETECTED"), None)
            assert conflict_msg is not None, "Missing CONFLICT_DETECTED message in message bus"
            print(f"  -> Conflict Message: {conflict_msg['findings'][0]}")
            
            # Check competing hypotheses
            hypotheses = res["canonical_report"]["alternative_causes"]
            cpu_hyp = next((h for h in hypotheses if "CPU" in h["name"] or "Processor" in h["name"]), None)
            cong_hyp = next((h for h in hypotheses if "Congestion" in h["name"]), None)
            assert cpu_hyp is not None and cpu_hyp["status"] in ["VALIDATED", "CONFIRMED"]
            assert cong_hyp is not None and cong_hyp["status"] in ["REFUTED", "REJECTED"]
            print(f"  -> Validated Hypothesis: {cpu_hyp['name']} (p={cpu_hyp['probability']})")
            print(f"  -> Refuted Hypothesis: {cong_hyp['name']} (p={cong_hyp['probability']})")

    print("\nALL 8 SCENARIOS SUCCESSFULLY VERIFIED WITH ZERO ERRORS!")

if __name__ == "__main__":
    test_all()

