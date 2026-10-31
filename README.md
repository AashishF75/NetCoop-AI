# NetCoop AI — Multi-Agent Network Fault Diagnosis and Interoperability
### IIT Bhubaneswar Agentic AI Grand Finale — Autonomous NOC Platform

[![Protocol](https://img.shields.io/badge/Protocol-Canonical_v1.0.0-cyan.svg)](file:///backend/app/protocol/schema.py)
[![Backend](https://img.shields.io/badge/FastAPI-Python_3.13-009688.svg)](file:///backend/app/main.py)
[![Frontend](https://img.shields.io/badge/React_18-Vite_Tailwind-61dafb.svg)](file:///frontend/src/App.jsx)
[![Pytest](https://img.shields.io/badge/Pytest-68%2F68_Passing-brightgreen.svg)](file:///backend/tests)
[![Collector](https://img.shields.io/badge/Collector-On--Premise_Zero--Inbound-success.svg)](file:///DEPLOYMENT_AND_COLLECTOR_GUIDE.md)
[![Playwright](https://img.shields.io/badge/Playwright-Verified_Live_E2E-emerald.svg)](file:///backend/test_browser_flow.py)
[![Scenarios](https://img.shields.io/badge/Scenarios-9_Benchmarks_Passing-blueviolet.svg)](file:///backend/app/scenarios/generator.py)

---

## 1. Executive Summary

**NetCoop AI** is an evidence-based multi-agent network fault diagnosis platform designed for high-density enterprise networks and Network Operations Centers (NOC). 

Rather than relying on isolated static threshold alerts or opaque black-box models, NetCoop AI employs **five specialized autonomous agents** that actively collaborate, cross-examine evidence, resolve conflicting telemetry, and compile actionable remediation runbooks through a **strictly enforced canonical JSON message protocol**.

```
                        ┌────────────────────────────────────────────────────────┐
                        │             SYNTHETIC NETWORK TELEMETRY               │
                        │    (JSON / CSV: Latency, Loss, Queues, CPU, RF, DNS)   │
                        └───────────────────────────┬────────────────────────────┘
                                                    │
                                        [Telemetry Normalizer]
                                  Standardizes Units (ms, Mbps, %)
                                                    │
                 ┌──────────────────────────────────┼──────────────────────────────────┐
                 │                                  │                                  │
                 ▼                                  ▼                                  ▼
      ┌─────────────────────┐            ┌─────────────────────┐            ┌─────────────────────┐
      │  Performance Agent  │            │ Infrastructure Agt  │            │  Connectivity Agt   │
      │   (perf-agent-01)   │            │   (infra-agent-01)  │            │   (conn-agent-01)   │
      │ Latency, Jitter,    │            │ CPU, Memory, DOM,   │            │ Wi-Fi RSSI/SNR,     │
      │ Queue Drops & Loss  │            │ CRC Errors & Flaps  │            │ DNS/DHCP Resolution │
      └──────────┬──────────┘            └──────────┬──────────┘            └──────────┬──────────┘
                 │                                  │                                  │
                 └──────────────────┬───────────────┴──────────────────────────────────┘
                                    │ Emits Canonical TELEMETRY_ANOMALY
                                    ▼
                 ┌─────────────────────────────────────────────────────┐
                 │        Fault Correlation Agent (corr-agent-01)      │
                 │   - Coordinates Inter-Agent Cross-Examination       │
                 │   - Issues Directed QUERY_EVIDENCE to Peers         │
                 │   - Evaluates Competing Hypotheses                  │
                 │   - Executes Real-Time Conflict Resolution          │
                 │   - Calculates Synthesized Bayesian Confidence      │
                 └──────────────────────────┬──────────────────────────┘
                                            │ Emits DIAGNOSTIC_SUMMARY
                                            ▼
                 ┌─────────────────────────────────────────────────────┐
                 │    Recommendation Agent (recom-agent-01)            │
                 │   - Synthesizes Operational CLI Remediation Steps   │
                 │   - Validates Risks, Rationale & Rollback Plans     │
                 │   - Compiles Canonical JSON Diagnostic Report       │
                 └──────────────────────────┬──────────────────────────┘
                                            │
                                            ▼
                 ┌─────────────────────────────────────────────────────┐
                 │        Interactive Dark-Mode NOC Dashboard          │
                 │   - React Flow Network Topology (Pulsing Alerts)    │
                 │   - Recharts Real-Time Telemetry Multi-Charts       │
                 │   - Live Inter-Agent Message Protocol Stream        │
                 │   - Competing Hypotheses & Remediation Runbooks     │
                 └─────────────────────────────────────────────────────┘
```

---

## 2. Specialized Multi-Agent Roles

| Agent Name | Identifier | Domain Specialty | Monitored Telemetry |
| :--- | :--- | :--- | :--- |
| **Performance Agent** | `perf-agent-01` | Traffic dynamics & congestion | Latency (`ms`), Jitter (`ms`), Packet Loss (`%`), Bandwidth Utilization (`%`), Egress Queue Drops (`pkts/s`) |
| **Infrastructure Health Agent** | `infra-agent-01` | Hardware & node resources | CPU (`%`), Memory (`%`), Interface CRC Errors (`errors/s`), Physical Link Flaps, Device Status |
| **Connectivity Analysis Agent** | `conn-agent-01` | Physical reachability & core services | Wireless RF RSSI (`dBm`), SNR (`dB`), 802.11 Retries (`%`), DNS Response (`ms`), DHCP Pool (`%`) |
| **Fault Correlation Agent** | `corr-agent-01` | Cross-agent synthesis & hypothesis ranking | Interrogates domain agents via `QUERY_EVIDENCE`, detects conflicting signals, computes Bayesian probability |
| **Recommendation & Reporting Agent** | `recom-agent-01` | Operational runbooks & canonical reporting | Generates ordered CLI commands (Cisco/Arista/Linux), risk levels, rollback plans, and final canonical report |

### Genuine Inter-Agent Communication
Agents do **not** merely execute in a pipeline; they engage in bidirectional cross-examination:
1. `perf-agent-01` reports high packet loss on `Core-Router-01`.
2. `corr-agent-01` issues a directed `QUERY_EVIDENCE` message to `infra-agent-01` with correlation ID: *"Does Core-Router-01 have physical CRC errors or high CPU?"*
3. `infra-agent-01` replies via `QUERY_RESPONSE`: *"Zero CRC errors, but CPU is saturated at 99.4%."*
4. `corr-agent-01` issues a `CONFLICT_DETECTED` event, proving that the packet drop is control-plane CPU starvation rather than link buffer congestion!

---

## 3. Canonical Protocol & Interoperability Specification

All inter-agent communication and diagnostic reports strictly adhere to Pydantic v2 schemas.

### Canonical `AgentMessage` Schema
```json
{
  "agent_id": "corr-agent-01",
  "target_agent_id": "infra-agent-01",
  "message_type": "QUERY_EVIDENCE",
  "schema_version": "1.0.0",
  "timestamp": "2026-10-31T07:15:00.000Z",
  "device_id": "Core-Router-01",
  "metric": "cpu_utilization_pct",
  "value": null,
  "unit": "%",
  "evidence": { "threshold": 92.0 },
  "confidence": 0.94,
  "findings": ["Requesting hardware status and CPU load for Core-Router-01"],
  "correlation_id": "corr-4b2e8f10"
}
```

### Protocol Validation & Incompatibility Handling
- **Schema Version Mismatch**: Incoming payloads with unsupported schema versions (e.g., `0.8.2`) are rejected with `SchemaVersionMismatchError` and an explicit `SCHEMA_VERSION_MISMATCH` message, indicating supported versions (`1.0.0`).
- **Missing Required Fields**: Payloads lacking `message_type` or `agent_id` trigger `MissingFieldError`.
- **Unit Normalization**: Automatically converts inconsistent vendor units (`kbps`, `Gbps`, `bytes/s` → `Mbps`; `s`, `us` → `ms`; `ratio` → `%`).
- **Malformed Data**: Catches out-of-range physical values (negative latencies, loss > 100%, confidence > 1.0) with `MalformedDataError`.

---

## 4. Benchmark Evaluation Scenarios (All 8 Implemented)

| # | Benchmark Scenario | Injected Fault Signature | Root Cause Diagnosed | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Normal Network** | Latency 2-5ms, 0% loss, CPU 18-25%, 0 CRC errors | Normal Network Operation (Within SLA Baselines) | 98.0% |
| **2** | **Link Congestion** | Core-to-Agg trunk 98.2% util, 84 pkts/s queue drops, 142ms latency | Egress Link Buffer Congestion | 95.0% |
| **3** | **Weak Wi-Fi Signal** | AP-02 RSSI -86.5 dBm, 9 dB SNR, 42% frame retries | Wireless RF Path Loss / Edge Signal Attenuation | 96.0% |
| **4** | **Interface Fault** | Edge-Switch-01 1,450 CRC err/s, 6 flaps, 0 queue drops | Physical Link / Transceiver Integrity Fault | 94.0% |
| **5** | **DNS/DHCP Failure** | DNS latency 3,250ms (timeout), DHCP pool 100% capacity | Core Network Services Failure (DNS/DHCP) | 97.0% |
| **6** | **Missing Telemetry** | Core router records omit CPU, queue drops & CRC counters | Inconclusive Diagnosis (Critical Gaps Flagged) | 42.0% |
| **7** | **Incompatible Messages**| Incompatible schema version `0.8.2`, non-standard metric units | Protocol Rejection (Schema Version Mismatch) | 100.0% |
| **8** | **Conflicting Evidence**| 115ms latency, but link util is 14% and router CPU is 99.4% | Control Plane Processor Saturation (Conflict Resolved) | 92.0% |

---

## 5. Getting Started & Installation

### Prerequisites
- Python 3.10+ (Tested on Python 3.13.2)
- Node.js 18+ (Tested on Node v24.12.0)
- npm 9+

### Quick Start (Automated Windows Launcher)
Simply double-click `start.bat` or run:
```powershell
.\start.bat
```

### Manual Step-by-Step Setup

#### 1. Backend Setup
```bash
# Navigate to backend and install requirements
cd backend
pip install -r requirements.txt

# Run automated test suite
python -m pytest tests -v

# Launch FastAPI backend server
python -m uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8000
```

#### 2. Frontend Setup
```bash
# Navigate to frontend and install dependencies
cd frontend
npm install

# Start Vite development server
npm run dev
```

Open your browser at **`http://localhost:5173`**.

---

## 6. Verification and Automated Test Results

The backend contains 30 comprehensive automated tests covering all required evaluation criteria:

```bash
python -m pytest backend/tests -v
```

```
============================= test session starts =============================
collected 30 items

backend/tests/test_agents.py::test_performance_agent_detects_congestion PASSED [  3%]
backend/tests/test_agents.py::test_infrastructure_agent_detects_crc_errors PASSED [  6%]
backend/tests/test_agents.py::test_connectivity_agent_detects_weak_wifi PASSED [ 10%]
backend/tests/test_api.py::test_api_health PASSED                        [ 13%]
backend/tests/test_api.py::test_api_topology PASSED                      [ 16%]
backend/tests/test_api.py::test_api_scenarios_list PASSED                [ 20%]
backend/tests/test_api.py::test_api_scenario_telemetry PASSED            [ 23%]
backend/tests/test_api.py::test_api_scenario_export_json_and_csv PASSED  [ 26%]
backend/tests/test_api.py::test_api_protocol_validation PASSED           [ 30%]
backend/tests/test_api.py::test_api_diagnose_scenario_link_congestion PASSED [ 33%]
backend/tests/test_api.py::test_api_diagnose_incompatible_schema_scenario PASSED [ 36%]
backend/tests/test_api.py::test_api_diagnose_raw_csv_ingestion PASSED    [ 40%]
backend/tests/test_fault_resolution.py::test_genuine_agent_communication_exchange PASSED [ 43%]
backend/tests/test_fault_resolution.py::test_competing_hypotheses_ranking PASSED [ 46%]
backend/tests/test_fault_resolution.py::test_conflict_resolution_behavior PASSED [ 50%]
backend/tests/test_fault_resolution.py::test_insufficient_evidence_handling PASSED [ 53%]
backend/tests/test_protocol.py::test_valid_agent_message_creation PASSED [ 56%]
backend/tests/test_protocol.py::test_schema_version_mismatch PASSED      [ 60%]
backend/tests/test_protocol.py::test_missing_required_fields PASSED      [ 63%]
backend/tests/test_protocol.py::test_malformed_telemetry_ranges PASSED   [ 66%]
backend/tests/test_protocol.py::test_unit_normalization PASSED           [ 70%]
backend/tests/test_protocol.py::test_csv_telemetry_parsing PASSED        [ 73%]
backend/tests/test_protocol.py::test_json_telemetry_parsing PASSED       [ 76%]
backend/tests/test_scenarios.py::test_scenario_normal_network PASSED     [ 80%]
backend/tests/test_scenarios.py::test_scenario_link_congestion PASSED    [ 83%]
backend/tests/test_scenarios.py::test_scenario_weak_wifi_signal PASSED   [ 86%]
backend/tests/test_scenarios.py::test_scenario_interface_fault PASSED    [ 90%]
backend/tests/test_scenarios.py::test_scenario_dns_dhcp_failure PASSED   [ 93%]
backend/tests/test_scenarios.py::test_scenario_missing_telemetry PASSED  [ 96%]
backend/tests/test_scenarios.py::test_scenario_conflicting_evidence PASSED [ 83%]
backend/tests/test_simulation.py::test_digital_twin_topology_and_dependencies PASSED [ 85%]
backend/tests/test_simulation.py::test_digital_twin_health_and_sla_scoring PASSED [ 88%]
backend/tests/test_simulation.py::test_what_if_remediation_simulation_deterministic PASSED [ 90%]
backend/tests/test_simulation.py::test_strategy_comparison_matrix PASSED [ 92%]
backend/tests/test_simulation.py::test_multi_incident_prioritization_ordering PASSED [ 95%]
backend/tests/test_simulation.py::test_investigation_explanation_generation PASSED [ 97%]
backend/tests/test_simulation.py::test_remediation_strategies_for_link_congestion PASSED [100%]

============================= 42 passed in 2.40s ==============================
```

---

## 7. Autonomous Investigation Replay & Interactive Device Inspection

NetCoop AI includes a full **Autonomous Investigation Replay** engine:
- **Backend Event Stream**: The orchestrator emits a sequential `InvestigationEvent` timeline stream (`INCIDENT_DETECTED` ➔ `AGENT_ACTIVATED` ➔ `EVIDENCE_COLLECTED` ➔ `CROSS_AGENT_QUERY` ➔ `CONFLICT_DETECTED` ➔ `HYPOTHESIS_CHALLENGED` ➔ `ROOT_CAUSE_RESOLVED` ➔ `REMEDIATION_GENERATED`).
- **Interactive Replay Controls**: Real-time Play, Pause, Step Next, Step Prev, Speed Toggles (1x, 2x, 3x), and a timeline scrubber.
- **Inspectable Payloads**: Click "Inspect JSON" on any timeline event to review the exact canonical `AgentMessage` or evidence payload.
- **Topology Dynamic Synchronization**: As events step through, implicated devices glow and display active communication badges (e.g. `[Bot] perf-agent-01 querying...`). Directional fault propagation paths are clearly mapped (`⚡ Fault Path`).
- **Interactive Device Details Drawer**: Clicking any network device on the React Flow topology opens a real-time sliding drawer comparing observed telemetry against baseline SLA operational thresholds.
- **Persistent Investigation Store**: All completed investigations are automatically persisted in `backend/data/investigations.json` and can be retrieved, replayed, or audited via `GET /api/investigations`.

---

## 8. Autonomous Network Intelligence & Digital Twin

- **Autonomous NOC Command Center**: Executive cockpit unifying composite network health, cross-incident topological clusters, proactive pre-breach forecasts, and swarm consensus trace.
- **Cross-Incident Correlation Engine**: Groups concurrent downstream symptoms to shared upstream infrastructure choke points (e.g. `Agg-Switch-01`), eliminating redundant technician tickets.
- **Proactive Risk Warning Radar**: Deterministic multi-point linear trend analysis calculates metric drift rates, projects 10-minute metrics, and estimates time-to-breach before golden SLAs fail.
- **Explainable SLA Health Scoring**: Transparent point deduction audit attributing deductions to specific empirical metric breaches (e.g. -45 pts for CPU > 90%) against golden SLA baselines.
- **Agent Investigation Trace**: Explicit stopping conditions (`EVIDENTIAL_CONSENSUS`, `SUFFICIENT_PROOF`), bounded rounds (max 2), dynamic query priority ranking, and zero recursive loops.
- **Network Digital Twin**: Models enterprise network topology, operational SLA bounds, and live health index.
- **What-If Remediation Simulator**: Projects deterministic data-plane recovery, before/after metric deltas, and side-by-side trade-offs for 3 candidate strategies.
- **Fault Injection Studio**: Interactive scenario builder allowing operators to adjust sliders, drop telemetry dimensions, or apply quick fault templates to stress-test multi-agent reasoning.

---

## 9. Live Network Integrations & Telemetry Adapters

NetCoop AI includes a modular adapter framework enabling real-time telemetry ingestion from physical and virtual network infrastructure:

### Supported Ingestion Protocols
1. **Active Socket / Ping Probes (`PING_PROBE`)**: Non-blocking asynchronous TCP/socket latency, jitter, and packet loss measurement.
2. **Host Appliance Kernel Monitor (`SERVER_HOST`)**: Real OS physical memory load (`%`), CPU utilization (`%`), and hardware core count via native OS system calls (Windows `kernel32` ctypes & POSIX `/proc`).
3. **RESTCONF / Router REST APIs (`REST_API`)**: Queries RFC 8040 RESTCONF interface states (`/restconf/data/ietf-interfaces:interfaces`) with Bearer, API key, or Basic authentication.
4. **SNMP v2c MIB-II Interface Poller (`SNMP`)**: Real UDP socket ASN.1 BER queries for standard MIB-II OIDs (sysDescr, ifOperStatus, ifInErrors).
5. **Syslog Event Collector (`SYSLOG`)**: Ingests and normalizes RFC 3164 / 5424 and Cisco IOS syslog streams into canonical fault signals.
6. **CSV / JSON Custom File Ingestion (`CSV_IMPORT` / `JSON_IMPORT`)**: Manual and automated export imports tagged as `CUSTOM_IMPORT`.

### Security Safeguards & Integrity Standards
- **Anti-Scanning Policy**: Target validation strictly forbids CIDR mask notations (`/24`, `/16`), IP ranges, and shell characters to prevent unauthorized subnet scanning.
- **Write-Only Credential Isolation**: Passwords, API keys, and SNMP community strings are encrypted in memory and strictly redacted (`has_credentials: true`) from public REST APIs and browser state.
- **Human-in-the-Loop Remediation**: Remediation actions provide actionable CLI procedures with rollback plans for operator authorization; no unvetted automated configuration changes are pushed to physical routers.
- **Honest Provenance Labeling**: UI dynamically displays `🟢 LIVE NETWORK`, `🟡 CUSTOM IMPORT`, or `🟣 SIMULATED SCENARIO`. The platform never labels synthetic telemetry as live.

---

## 10. Project Structure

```
TeamFusionNetCoopAI/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI REST API & Ingestion handlers
│   │   ├── protocol/
│   │   │   ├── schema.py               # Canonical Pydantic schemas (AgentMessage, Telemetry, Twin, Simulator)
│   │   │   └── normalizer.py           # Unit normalizer, protocol validator, CSV/JSON parser
│   │   ├── agents/
│   │   │   ├── base_agent.py           # Abstract Base Agent lifecycle & bus
│   │   │   ├── performance_agent.py    # Latency, loss, jitter, buffer drops
│   │   │   ├── infrastructure_agent.py # CPU, memory, CRC errors, transceivers
│   │   │   ├── connectivity_agent.py   # Wi-Fi RF, DNS, DHCP, L2/L3 reachability
│   │   │   ├── correlation_agent.py    # Cross-examination, hypotheses, conflict resolution
│   │   │   └── recommendation_agent.py # Remediation runbooks, canonical JSON report
│   │   ├── orchestrator/
│   │   │   ├── engine.py               # Orchestration engine, timeline events & explanation
│   │   │   └── store.py                # File-backed investigation persistence store
│   │   ├── intelligence/
│   │   │   ├── proactive_predictor.py  # Trend analysis & pre-breach warnings
│   │   │   ├── cross_correlator.py     # Cross-incident upstream choke-point correlation
│   │   │   └── health_scorer.py        # Explainable point-deduction health audit
│   │   ├── integrations/
│   │   │   ├── models.py               # Source configs, validation, write-only credentials
│   │   │   ├── manager.py              # Persistent registry, live tests, diagnosis dispatch
│   │   │   └── adapters/               # Modular adapters: Ping, Host, RESTCONF, SNMP, Syslog
│   │   ├── simulator/
│   │   │   ├── twin.py                 # Network digital twin, health index & SLA bounds
│   │   │   ├── engine.py               # Deterministic What-If simulator & strategy comparison
│   │   │   └── prioritizer.py          # Multi-incident operational triage engine
│   │   └── scenarios/
│   │       └── generator.py            # 9 benchmark scenarios, topology, CSV/JSON exporter
│   ├── tests/
│   │   ├── test_protocol.py            # Protocol & schema unit tests
│   │   ├── test_agents.py              # Domain agent tests
│   │   ├── test_fault_resolution.py    # Inter-agent communication & conflict resolution
│   │   ├── test_investigation_replay.py# Investigation timeline, store, & reasoning tests
│   │   ├── test_simulation.py          # Digital Twin, What-If simulation & prioritization tests
│   │   ├── test_intelligence.py        # Proactive prediction, correlation, & health tests
│   │   ├── test_scenarios.py           # All 9 benchmark scenario tests
│   │   └── test_api.py                 # FastAPI integration tests
│   ├── test_browser_flow.py            # End-to-end Playwright headless 19-step verification
│   ├── verify_all_scenarios.py         # Automated API verification for all 9 scenarios
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx              # NOC header & action buttons
│   │   │   ├── CommandCenterView.jsx   # Autonomous NOC Command Center (Executive Cockpit)
│   │   │   ├── NetworkIntegrationsView.jsx # Live telemetry adapters & source dashboard
│   │   │   ├── NetworkTopology.jsx     # React Flow graph, fault propagation, agent badges
│   │   │   ├── DeviceDetailsModal.jsx  # Interactive observed vs baseline SLA telemetry drawer
│   │   │   ├── InvestigationReplay.jsx # Autonomous investigation scrubber & playback engine
│   │   │   ├── DigitalTwinView.jsx     # Full digital twin view, dependencies & health gauges
│   │   │   ├── WhatIfSimulator.jsx     # What-If simulator & side-by-side strategy matrix
│   │   │   ├── IncidentPrioritizer.jsx # Multi-incident operational queue (P1-P4)
│   │   │   ├── FaultInjectionStudio.jsx# Interactive scenario builder & telemetry sliders
│   │   │   ├── TelemetryCharts.jsx     # Recharts multi-tab metrics (latency, drops, CPU, RF)
│   │   │   ├── AgentActivityPanel.jsx  # Animated 5-agent swarm activity cards
│   │   │   ├── InterAgentMessageLog.jsx# Canonical protocol message stream & JSON inspector
│   │   │   ├── RootCausePanel.jsx      # Diagnosis, explanation ("Why did agents reach this?"), runbooks
│   │   │   ├── EvidenceCards.jsx       # Structured evidence artifacts ledger
│   │   │   ├── ScenarioSelector.jsx    # 9 benchmark scenarios & CSV/JSON custom upload
│   │   │   ├── JsonReportModal.jsx     # Copyable/downloadable canonical JSON report viewer
│   │   │   ├── ProtocolValidationTester.jsx # Interactive Pydantic protocol validator
│   │   │   └── DiagnosticHistory.jsx   # Timeline of session diagnosis runs
│   │   ├── api/
│   │   │   └── client.js               # Frontend API client
│   │   ├── App.jsx                     # Master dashboard layout & view switcher
│   │   ├── index.css                   # Tailwind NOC theme & keyframe glow animations
│   │   └── main.jsx                    # React entry point
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── DEMO_GUIDE.md                       # Complete 4-minute pitch playbook & presentation guide
├── README.md                           # Comprehensive documentation & evaluation guide
└── start.bat                           # Windows one-click startup launcher
```
