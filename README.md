# NetCoop AI — Multi-Agent Network Fault Diagnosis and Interoperability
### IIT Bhubaneswar Agentic AI Grand Finale — Autonomous NOC Platform

[![Protocol](https://img.shields.io/badge/Protocol-Canonical_v1.0.0-cyan.svg)](file:///backend/app/protocol/schema.py)
[![Backend](https://img.shields.io/badge/FastAPI-Python_3.13-009688.svg)](file:///backend/app/main.py)
[![Frontend](https://img.shields.io/badge/React_18-Vite_Tailwind-61dafb.svg)](file:///frontend/src/App.jsx)
[![Tests](https://img.shields.io/badge/Pytest-30%2F30_Passing-brightgreen.svg)](file:///backend/tests)

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
cd c:\NetCoopAI\backend
pip install -r requirements.txt

# Run automated test suite
python -m pytest tests -v

# Launch FastAPI backend server
python -m uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8000
```

#### 2. Frontend Setup
```bash
# Navigate to frontend and install dependencies
cd c:\NetCoopAI\frontend
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
backend/tests/test_scenarios.py::test_scenario_conflicting_evidence PASSED [100%]

============================= 30 passed in 0.33s ==============================
```

---

## 7. Project Structure

```
NetCoopAI/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI REST API & Ingestion handlers
│   │   ├── protocol/
│   │   │   ├── schema.py               # Canonical Pydantic schemas (AgentMessage, Telemetry)
│   │   │   └── normalizer.py           # Unit normalizer, protocol validator, CSV/JSON parser
│   │   ├── agents/
│   │   │   ├── base_agent.py           # Abstract Base Agent lifecycle & bus
│   │   │   ├── performance_agent.py    # Latency, loss, jitter, buffer drops
│   │   │   ├── infrastructure_agent.py # CPU, memory, CRC errors, transceivers
│   │   │   ├── connectivity_agent.py   # Wi-Fi RF, DNS, DHCP, L2/L3 reachability
│   │   │   ├── correlation_agent.py    # Cross-examination, hypotheses, conflict resolution
│   │   │   └── recommendation_agent.py # Remediation runbooks, canonical JSON report
│   │   ├── orchestrator/
│   │   │   └── engine.py               # Orchestration engine & execution tracing
│   │   └── scenarios/
│   │       └── generator.py            # 8 benchmark scenarios, topology, CSV/JSON exporter
│   ├── tests/
│   │   ├── test_protocol.py            # Protocol & schema unit tests
│   │   ├── test_agents.py              # Domain agent tests
│   │   ├── test_fault_resolution.py    # Inter-agent communication & conflict resolution
│   │   ├── test_scenarios.py           # All 8 benchmark scenario tests
│   │   └── test_api.py                 # FastAPI integration tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx              # NOC header & action buttons
│   │   │   ├── NetworkTopology.jsx     # React Flow interactive graph with pulsing alert nodes
│   │   │   ├── TelemetryCharts.jsx     # Recharts multi-tab metrics (latency, drops, CPU, RF)
│   │   │   ├── AgentActivityPanel.jsx  # Animated 5-agent swarm activity cards
│   │   │   ├── InterAgentMessageLog.jsx# Canonical protocol message stream & JSON inspector
│   │   │   ├── RootCausePanel.jsx      # Diagnosis, confidence gauge & remediation runbooks
│   │   │   ├── EvidenceCards.jsx       # Structured evidence artifacts ledger
│   │   │   ├── ScenarioSelector.jsx    # 8 benchmark scenarios & CSV/JSON custom upload
│   │   │   ├── JsonReportModal.jsx     # Copyable/downloadable canonical JSON report viewer
│   │   │   ├── ProtocolValidationTester.jsx # Interactive Pydantic protocol validator
│   │   │   └── DiagnosticHistory.jsx   # Timeline of session diagnosis runs
│   │   ├── api/
│   │   │   └── client.js               # Frontend API client
│   │   ├── App.jsx                     # Master dashboard layout
│   │   ├── index.css                   # Tailwind NOC theme & keyframe glow animations
│   │   └── main.jsx                    # React entry point
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── README.md                           # Comprehensive documentation & evaluation guide
└── start.bat                           # Windows one-click startup launcher
```
