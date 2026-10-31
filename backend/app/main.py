"""
FastAPI Application for NetCoop AI.
Provides REST APIs for multi-agent network fault diagnosis,
telemetry ingestion (JSON/CSV), canonical protocol validation,
scenario benchmarks, and interactive visualization.
"""

from typing import List, Dict, Any, Optional
import time
import uuid
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.protocol.schema import (
    TelemetryRecord,
    AgentMessage,
    MessageType,
    DiagnosticStatus,
    CURRENT_SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
)
from app.protocol.normalizer import (
    TelemetryNormalizer,
    InteroperabilityValidator,
    ProtocolError,
    MalformedDataError,
    SchemaVersionMismatchError,
    MissingFieldError,
)
from app.orchestrator.engine import MultiAgentOrchestrator
from app.orchestrator.store import investigation_store
from app.scenarios.generator import ScenarioCatalog, get_default_topology
from app.simulator.twin import digital_twin_engine
from app.simulator.engine import remediation_simulator
from app.simulator.prioritizer import incident_prioritizer
from app.intelligence import (
    proactive_predictor,
    cross_incident_correlator,
    explainable_health_scorer,
)
from app.integrations.models import (
    SourceCreateRequest,
    SourceUpdateRequest,
    SyslogIngestRequest,
    LiveDiagnosisRequest,
    NetworkSourcePublic,
    ConnectionTestResult,
)
from app.integrations.manager import get_integration_manager
from app.integrations.collector_hub import (
    get_collector_hub,
    CollectorRegisterRequest,
    CollectorHeartbeatRequest,
    TelemetryPushRequest,
    DeviceRegisterRequest,
)
from app.generator.telemetry_generator import (
    generate_telemetry,
    adapt_to_canonical_record,
    validate_generated_payload,
    VALID_FAULT_TYPES,
)

app = FastAPI(
    title="NetCoop AI — Multi-Agent Network Fault Diagnosis Platform",
    description="Agentic cooperative network diagnosis platform with canonical JSON protocol interoperability.",
    version="1.0.0",
)

# Enable CORS for React Vite development & Vercel Production
ALLOWED_ORIGINS = [
    "https://net-coop-ai.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = MultiAgentOrchestrator()


@app.on_event("startup")
def seed_default_investigations():
    """Seeds default investigation benchmark runs if store is empty."""
    try:
        if len(investigation_store.list_investigations()) == 0:
            for sc_id, inc_id in [("conflicting_evidence", "INC-DEMO-SC8"), ("link_congestion", "INC-DEMO-SC2")]:
                telem = ScenarioCatalog.generate_telemetry(sc_id)
                orchestrator.run_diagnosis(telem, incident_id=inc_id, scenario_id=sc_id)
    except Exception as e:
        print(f"Warning during seed: {e}")


@app.get("/api/investigations")
def list_investigations():
    """Returns list of past completed investigations available for replay."""
    return investigation_store.list_investigations()


@app.get("/api/investigations/{incident_id}")
def get_investigation_details(incident_id: str):
    """Retrieves full investigation state and timeline event stream for replay."""
    record = investigation_store.get_investigation(incident_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Investigation #{incident_id} not found in store")
    return record


class DiagnoseRequest(BaseModel):
    scenario_id: Optional[str] = None
    telemetry: Optional[List[Dict[str, Any]]] = None
    raw_content: Optional[str] = None
    data_format: Optional[str] = "json"  # "json" or "csv"
    incident_id: Optional[str] = None


class ProtocolValidationRequest(BaseModel):
    message: Dict[str, Any]


@app.get("/api/health")
def health_check():
    return {
        "status": "ONLINE",
        "service": "NetCoop AI Multi-Agent Diagnosis Engine",
        "protocol_version": CURRENT_SCHEMA_VERSION,
        "supported_versions": list(SUPPORTED_SCHEMA_VERSIONS),
        "agents_registered": [
            "Performance Agent (perf-agent-01)",
            "Infrastructure Health Agent (infra-agent-01)",
            "Connectivity Analysis Agent (conn-agent-01)",
            "Fault Correlation Agent (corr-agent-01)",
            "Recommendation & Reporting Agent (recom-agent-01)",
        ]
    }


@app.get("/api/topology")
def get_topology():
    return get_default_topology()


@app.get("/api/scenarios")
def list_scenarios():
    return ScenarioCatalog.get_scenario_metadata()


@app.get("/api/scenarios/{scenario_id}/telemetry")
def get_scenario_telemetry(scenario_id: str):
    records = ScenarioCatalog.generate_telemetry(scenario_id)
    return {
        "scenario_id": scenario_id,
        "count": len(records),
        "telemetry": [r.model_dump() for r in records],
        "topology": get_default_topology(),
    }


@app.get("/api/scenarios/{scenario_id}/export")
def export_scenario_data(scenario_id: str, format: str = "json"):
    if format.lower() == "csv":
        csv_data = ScenarioCatalog.export_csv(scenario_id)
        return Response(content=csv_data, media_type="text/csv", headers={
            "Content-Disposition": f"attachment; filename={scenario_id}_telemetry.csv"
        })
    else:
        json_data = ScenarioCatalog.export_json(scenario_id)
        return Response(content=json_data, media_type="application/json", headers={
            "Content-Disposition": f"attachment; filename={scenario_id}_telemetry.json"
        })


@app.post("/api/protocol/validate-message")
def validate_agent_message(req: ProtocolValidationRequest):
    """
    Validates whether an inter-agent message complies with the canonical protocol.
    Catches schema version mismatches, missing fields, or malformed data explicitly.
    """
    try:
        validated = InteroperabilityValidator.validate_message(req.message)
        return {
            "valid": True,
            "message": "Compliant with NetCoop canonical JSON protocol",
            "schema_version": validated.schema_version,
            "agent_message": validated.model_dump(),
        }
    except SchemaVersionMismatchError as sve:
        return {
            "valid": False,
            "error_type": "SCHEMA_VERSION_MISMATCH",
            "error_detail": str(sve),
            "received_version": sve.version,
            "supported_versions": list(sve.supported),
        }
    except MissingFieldError as mfe:
        return {
            "valid": False,
            "error_type": "MISSING_REQUIRED_FIELD",
            "error_detail": str(mfe),
            "missing_fields": mfe.missing_fields,
        }
    except MalformedDataError as mde:
        return {
            "valid": False,
            "error_type": "MALFORMED_DATA",
            "error_detail": str(mde),
            "details": mde.details,
        }


@app.post("/api/diagnose")
def run_fault_diagnosis(req: DiagnoseRequest):
    """
    Executes multi-agent fault diagnosis for a specified scenario or uploaded dataset.
    Handles unit normalization, schema validation, and inter-agent coordination.
    """
    # Special Handling for Scenario 7: Incompatible Agent Messages
    if req.scenario_id == "incompatible_agent_messages":
        # Simulate incoming legacy agent message with incompatible schema version and malformed unit
        bad_message_dict = {
            "agent_id": "legacy-vendor-probe-09",
            "schema_version": "0.8.2",  # Unsupported schema version!
            "metric": "bandwidth_utilization",
            "value": "invalid_string_ratio",
            "unit": "kilo-bytes-per-sec",
            # Missing message_type and confidence!
        }
        
        # Test protocol validator directly to demonstrate explicit handling
        error_response = None
        try:
            InteroperabilityValidator.validate_message(bad_message_dict)
        except ProtocolError as pe:
            error_response = {
                "error_type": type(pe).__name__,
                "details": str(pe),
                "rejected_payload": bad_message_dict,
            }

        # Also generate the diagnosis showing how the multi-agent system registers this error
        telemetry = ScenarioCatalog.generate_telemetry("incompatible_agent_messages")
        result = orchestrator.run_diagnosis(telemetry, incident_id=req.incident_id or "INC-SCHEMA-FAIL")
        
        # Add the explicit protocol rejection alert into the message bus
        proto_alert = AgentMessage(
            agent_id="corr-agent-01",
            target_agent_id="legacy-vendor-probe-09",
            message_type=MessageType.SCHEMA_VERSION_MISMATCH,
            schema_version=CURRENT_SCHEMA_VERSION,
            confidence=1.0,
            findings=[
                "CRITICAL INTEROPERABILITY REJECTION: Received message with unsupported schema_version '0.8.2'.",
                "Strict protocol enforcement: Missing required field 'message_type'.",
                "Non-compliant unit 'kilo-bytes-per-sec' rejected. Canonical unit must be 'Mbps'.",
            ],
            evidence=error_response or {}
        )
        result["message_bus"].insert(0, proto_alert.model_dump())
        result["status"] = "INCONCLUSIVE"
        result["suspected_root_cause"] = "Protocol Interoperability Rejection (Schema Version Mismatch & Malformed Fields)"
        result["canonical_report"]["status"] = "INCONCLUSIVE"
        result["canonical_report"]["suspected_root_cause"] = "Protocol Interoperability Rejection (Schema Version Mismatch & Malformed Fields)"
        result["canonical_report"]["limitations"].append(
            "Agent message from 'legacy-vendor-probe-09' rejected due to schema version 0.8.2 incompatibility."
        )
        result["investigation_id"] = result["incident_id"]
        result["scenario_id"] = "incompatible_agent_messages"
        investigation_store.save_investigation(result)
        return result

    # Standard Ingestion
    telemetry_records: List[TelemetryRecord] = []

    # 1. Raw text ingestion (CSV or JSON)
    if req.raw_content:
        try:
            if req.data_format == "csv" or ("," in req.raw_content and "\n" in req.raw_content):
                telemetry_records = TelemetryNormalizer.parse_csv_telemetry(req.raw_content)
            else:
                telemetry_records = TelemetryNormalizer.parse_json_telemetry(req.raw_content)
        except ProtocolError as pe:
            raise HTTPException(status_code=400, detail=str(pe))

    # 2. Structured JSON telemetry records passed directly
    elif req.telemetry:
        try:
            for item in req.telemetry:
                telemetry_records.append(TelemetryNormalizer.validate_and_normalize_telemetry(item))
        except ProtocolError as pe:
            raise HTTPException(status_code=400, detail=str(pe))

    # 3. Scenario ID selector
    elif req.scenario_id:
        telemetry_records = ScenarioCatalog.generate_telemetry(req.scenario_id)

    else:
        # Default scenario
        telemetry_records = ScenarioCatalog.generate_telemetry("normal_network")

    # Run Multi-Agent Orchestrator Pipeline
    result = orchestrator.run_diagnosis(
        telemetry_records,
        incident_id=req.incident_id,
        scenario_id=req.scenario_id,
    )
    return result


# -------------------------------------------------------------
# DIGITAL TWIN & WHAT-IF SIMULATOR ENDPOINTS
# -------------------------------------------------------------

class SimulationRequest(BaseModel):
    incident_id: str
    strategy_id: str
    target_device: str = "Core-Router-01"
    root_cause: str = "Control Plane Processor Saturation"
    current_telemetry: Optional[Dict[str, Any]] = None


class StrategyCompareRequest(BaseModel):
    incident_id: str
    target_device: str = "Core-Router-01"
    root_cause: str = "Control Plane Processor Saturation"
    current_telemetry: Optional[Dict[str, Any]] = None


class FaultInjectionRequest(BaseModel):
    device_id: str = "Core-Router-01"
    cpu_utilization_pct: Optional[float] = None
    latency_ms: Optional[float] = None
    packet_loss_pct: Optional[float] = None
    utilization_pct: Optional[float] = None
    queue_drops_per_sec: Optional[float] = None
    interface_crc_errors: Optional[int] = None
    wifi_rssi_dbm: Optional[float] = None
    dns_response_ms: Optional[float] = None
    dropped_fields: Optional[List[str]] = Field(default_factory=list)


@app.get("/api/digital-twin")
def get_digital_twin_snapshot():
    """
    Returns the current Network Digital Twin snapshot, device dependencies,
    health scores, and baseline SLA compliance.
    """
    return digital_twin_engine.get_cached_or_default()


@app.get("/api/simulator/strategies")
def get_remediation_strategies(
    root_cause: Optional[str] = "Control Plane Processor Saturation",
    target_device: Optional[str] = "Core-Router-01",
):
    """
    Returns 3 candidate remediation strategies for a given root cause.
    """
    strategies = remediation_simulator.get_candidate_strategies(
        root_cause=root_cause,
        target_device=target_device,
    )
    return strategies


@app.post("/api/simulator/simulate")
def simulate_remediation(req: SimulationRequest):
    """
    Executes a deterministic What-If simulation comparing current state against projected state.
    """
    strategies = remediation_simulator.get_candidate_strategies(
        root_cause=req.root_cause,
        target_device=req.target_device,
        current_metrics=req.current_telemetry or {},
    )

    selected = next((s for s in strategies if s.strategy_id == req.strategy_id), strategies[0])

    result = remediation_simulator.run_simulation(
        incident_id=req.incident_id,
        strategy=selected,
        current_telemetry=req.current_telemetry or {},
        target_device=req.target_device,
    )
    return result


@app.post("/api/simulator/compare")
def compare_strategies(req: StrategyCompareRequest):
    """
    Returns a side-by-side trade-off matrix comparing all alternative strategies.
    """
    return remediation_simulator.generate_comparison_matrix(
        incident_id=req.incident_id,
        target_device=req.target_device,
        root_cause=req.root_cause,
        current_metrics=req.current_telemetry or {},
    )


@app.get("/api/incidents/prioritization")
def get_incident_prioritization():
    """
    Returns multi-incident priority queue ranked by severity, SLA breach, and blast radius.
    """
    return incident_prioritizer.prioritize_incidents()


@app.post("/api/simulator/inject-fault")
def inject_fault_and_diagnose(req: FaultInjectionRequest):
    """
    Injects custom telemetry modifications into baseline topology and executes the real multi-agent diagnosis.
    """
    # Start with baseline nominal network
    base_records = ScenarioCatalog.generate_telemetry("normal_network")
    
    # Apply injected values to target device
    for rec in base_records:
        if rec.device_id == req.device_id:
            if req.cpu_utilization_pct is not None:
                rec.cpu_utilization_pct = req.cpu_utilization_pct
            if req.latency_ms is not None:
                rec.latency_ms = req.latency_ms
            if req.packet_loss_pct is not None:
                rec.packet_loss_pct = req.packet_loss_pct
            if req.utilization_pct is not None:
                rec.utilization_pct = req.utilization_pct
            if req.queue_drops_per_sec is not None:
                rec.queue_drops_per_sec = req.queue_drops_per_sec
            if req.interface_crc_errors is not None:
                rec.interface_crc_errors = req.interface_crc_errors
            if req.wifi_rssi_dbm is not None:
                rec.wifi_rssi_dbm = req.wifi_rssi_dbm
            if req.dns_response_ms is not None:
                rec.dns_response_ms = req.dns_response_ms

            # Handle simulated missing telemetry fields
            if req.dropped_fields:
                for f in req.dropped_fields:
                    if hasattr(rec, f):
                        setattr(rec, f, None)

    # Execute genuine multi-agent diagnosis
    custom_inc_id = f"INC-INJECT-{uuid.uuid4().hex[:6].upper()}"
    diag_result = orchestrator.run_diagnosis(
        base_records,
        incident_id=custom_inc_id,
        scenario_id="custom_injected_fault",
    )
    diag_result["is_custom_injected"] = True
    diag_result["injected_params"] = req.model_dump()
    return diag_result


# -------------------------------------------------------------
# PHASE 4: AUTONOMOUS NETWORK INTELLIGENCE ENDPOINTS
# -------------------------------------------------------------

@app.get("/api/intelligence/health-breakdown")
def get_explainable_health_breakdown(scenario_id: Optional[str] = None):
    """
    Returns transparent, auditable network health score with itemized point deductions
    against golden SLA baselines for each monitored node and the composite fabric.
    """
    sc_id = scenario_id or "normal_network"
    telemetry = ScenarioCatalog.generate_telemetry(sc_id)
    report = explainable_health_scorer.compute_health_report(telemetry)
    return report.model_dump()


@app.get("/api/intelligence/proactive-risks")
def get_proactive_risks(scenario_id: Optional[str] = None):
    """
    Evaluates multi-point telemetry time-series trends to identify metric drift,
    time-to-breach projections, and preventive remediation recommendations.
    """
    sc_id = scenario_id or "shared_upstream_fault"
    current_telem = ScenarioCatalog.generate_telemetry(sc_id)
    
    # Generate 3-interval time series showing creeping metric degradation
    t_minus_20: List[TelemetryRecord] = []
    t_minus_10: List[TelemetryRecord] = []
    
    for r in current_telem:
        # T-20m snapshot: baseline / slight drift
        r20 = r.model_copy()
        if r.cpu_utilization_pct is not None:
            r20.cpu_utilization_pct = max(15.0, round(r.cpu_utilization_pct * 0.55, 1))
        if r.latency_ms is not None:
            r20.latency_ms = max(2.0, round(r.latency_ms * 0.4, 1))
        if r.utilization_pct is not None:
            r20.utilization_pct = max(5.0, round(r.utilization_pct * 0.5, 1))
        if r.interface_crc_errors is not None:
            r20.interface_crc_errors = max(0, int(r.interface_crc_errors * 0.1))
        t_minus_20.append(r20)

        # T-10m snapshot: mid-way drift
        r10 = r.model_copy()
        if r.cpu_utilization_pct is not None:
            r10.cpu_utilization_pct = max(20.0, round(r.cpu_utilization_pct * 0.78, 1))
        if r.latency_ms is not None:
            r10.latency_ms = max(3.0, round(r.latency_ms * 0.7, 1))
        if r.utilization_pct is not None:
            r10.utilization_pct = max(8.0, round(r.utilization_pct * 0.75, 1))
        if r.interface_crc_errors is not None:
            r10.interface_crc_errors = max(0, int(r.interface_crc_errors * 0.5))
        t_minus_10.append(r10)

    history = [t_minus_20, t_minus_10, current_telem]
    warnings = proactive_predictor.analyze_trends(history, current_telemetry=current_telem)

    return {
        "scenario_id": sc_id,
        "count": len(warnings),
        "warnings": [w.model_dump() for w in warnings],
        "analysis_mode": "DETERMINISTIC_MULTI_POINT_TREND_EXTRAPOLATION",
        "intervals_evaluated": 3,
        "history_window_minutes": 20,
    }


@app.get("/api/intelligence/correlations")
def get_incident_correlations(scenario_id: Optional[str] = "shared_upstream_fault"):
    """
    Correlates multiple incident alerts across topology to identify shared upstream bottlenecks,
    prevent redundant remediation tickets, and pinpoint cascading fault origins.
    """
    from app.protocol.schema import IncidentPriority, IncidentPriorityItem

    # Build active incident representations based on scenario
    if scenario_id == "shared_upstream_fault":
        test_incidents = [
            IncidentPriorityItem(
                incident_id="INC-CORR-01",
                device_id="Agg-Switch-01",
                title="SFP+ Optical Transceiver Flaps & Frame Corruptions",
                severity="CRITICAL",
                priority=IncidentPriority.P1,
                priority_score=92.5,
                sla_breached=True,
                affected_devices_count=4,
                affected_devices=["Agg-Switch-01", "Edge-Switch-01", "Edge-Switch-02", "AP-01"],
                service_impact="Severe link frame discards (820 CRC errors) impairing core-to-access distribution transit",
                confidence=0.96,
                propagation_risk="HIGH",
                suspected_root_cause="Physical Link / Transceiver Integrity Fault",
                recommended_action="Soft-reset optical transceiver port and replace faulty SFP+ module",
                status="OPEN",
            ),
            IncidentPriorityItem(
                incident_id="INC-CORR-02",
                device_id="Edge-Switch-01",
                title="Cascaded Access Ingress Latency (68ms) & Packet Loss (6.2%)",
                severity="WARNING",
                priority=IncidentPriority.P2,
                priority_score=68.0,
                sla_breached=True,
                affected_devices_count=2,
                affected_devices=["Edge-Switch-01", "AP-01"],
                service_impact="Elevated hop delay on edge VLAN access switch",
                confidence=0.88,
                propagation_risk="LOW",
                suspected_root_cause="Downstream Propagation from Upstream Aggregation Switch",
                recommended_action="Hold edge interface resets; await upstream Agg-Switch-01 stabilization",
                status="OPEN",
            ),
            IncidentPriorityItem(
                incident_id="INC-CORR-03",
                device_id="Edge-Switch-02",
                title="Downstream Access Latency (71ms) & Jitter Spikes",
                severity="WARNING",
                priority=IncidentPriority.P2,
                priority_score=65.5,
                sla_breached=True,
                affected_devices_count=2,
                affected_devices=["Edge-Switch-02", "DNS-Server-01"],
                service_impact="Cascaded delay affecting server farm switch connectivity",
                confidence=0.85,
                propagation_risk="LOW",
                suspected_root_cause="Downstream Propagation from Upstream Aggregation Switch",
                recommended_action="Hold local switch restart; root cause is upstream trunk failure",
                status="OPEN",
            ),
            IncidentPriorityItem(
                incident_id="INC-CORR-04",
                device_id="AP-01",
                title="WLAN Ingress RTT Degradation (78ms)",
                severity="WARNING",
                priority=IncidentPriority.P3,
                priority_score=52.0,
                sla_breached=True,
                affected_devices_count=1,
                affected_devices=["AP-01"],
                service_impact="Wi-Fi client latency elevated, though local RF SNR and RSSI remain nominal",
                confidence=0.80,
                propagation_risk="LOW",
                suspected_root_cause="Wired Uplink Transit Impairment",
                recommended_action="Suppress AP reboot; issue resides upstream in distribution layer",
                status="OPEN",
            ),
        ]
    else:
        test_incidents = incident_prioritizer.prioritize_incidents()

    clusters = cross_incident_correlator.correlate_incidents(test_incidents)

    return {
        "scenario_id": scenario_id,
        "cluster_count": len(clusters),
        "clusters": [c.model_dump() for c in clusters],
        "incidents_evaluated": [inc.model_dump() for inc in test_incidents],
        "redundant_tickets_prevented": max(0, len(test_incidents) - len(clusters)),
    }


# =====================================================================
# LIVE NETWORK INTEGRATIONS ENDPOINTS
# =====================================================================

@app.get("/api/integrations/sources", response_model=List[NetworkSourcePublic])
def list_network_sources():
    """
    Returns all registered network sources with sensitive credentials strictly redacted.
    """
    manager = get_integration_manager()
    return manager.list_sources()


@app.post("/api/integrations/sources", response_model=NetworkSourcePublic)
def create_network_source(req: SourceCreateRequest):
    """
    Registers a new network device or telemetry source.
    """
    manager = get_integration_manager()
    try:
        return manager.create_source(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/integrations/sources/{source_id}", response_model=NetworkSourcePublic)
def get_network_source(source_id: str):
    """
    Fetches details of a specific network source (redacted).
    """
    manager = get_integration_manager()
    src = manager.get_source_public(source_id)
    if not src:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found.")
    return src


@app.put("/api/integrations/sources/{source_id}", response_model=NetworkSourcePublic)
def update_network_source(source_id: str, req: SourceUpdateRequest):
    """
    Updates configuration for an existing network source.
    """
    manager = get_integration_manager()
    try:
        updated = manager.update_source(source_id, req)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found.")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/integrations/sources/{source_id}")
def delete_network_source(source_id: str):
    """
    Deletes a network source.
    """
    manager = get_integration_manager()
    if not manager.delete_source(source_id):
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found.")
    return {"success": True, "message": f"Source '{source_id}' removed successfully."}


@app.post("/api/integrations/sources/{source_id}/test", response_model=ConnectionTestResult)
async def test_network_source(source_id: str):
    """
    Executes a real physical probe or socket connection against the target network device.
    """
    manager = get_integration_manager()
    result = await manager.test_connection(source_id)
    return result


@app.post("/api/integrations/sources/{source_id}/poll")
async def poll_network_source(source_id: str):
    """
    Polls real live telemetry counters from the network device.
    """
    manager = get_integration_manager()
    records = await manager.poll_source(source_id)
    return {
        "source_id": source_id,
        "count": len(records),
        "records": [r.model_dump() for r in records],
    }


@app.post("/api/integrations/diagnose-live")
async def diagnose_live_network(req: LiveDiagnosisRequest):
    """
    Polls live telemetry from active connected network sources or on-premise collectors,
    normalizes metrics, and runs the 5-agent diagnosis pipeline producing a live Canonical Diagnostic Report.
    Never silently falls back to synthetic data.
    """
    hub = get_collector_hub()
    valid_recs, stale_devs = hub.get_live_telemetry_snapshot()

    # If specific direct sources are explicitly requested (e.g. host probe), evaluate them directly
    manager = get_integration_manager()
    if req.source_ids:
        registered_mgr_ids = {s.id for s in manager.list_sources()}
        if all(sid in registered_mgr_ids for sid in req.source_ids):
            result = await manager.run_live_diagnosis(
                source_ids=req.source_ids,
                timeout_sec=req.timeout_sec,
            )
            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("error", "Failed to retrieve live telemetry."))
            return result

    # Priority 1: Telemetry streamed by local network collectors from physical/local devices
    if valid_recs:
        res = hub.diagnose_live_devices()
        if res.get("success"):
            return res

    # Priority 2: Direct localhost probes or active local integrations
    result = await manager.run_live_diagnosis(
        source_ids=req.source_ids,
        timeout_sec=req.timeout_sec,
    )
    if not result.get("success"):
        stale_msg = f" (Stale devices: {', '.join(stale_devs)})" if stale_devs else ""
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to retrieve live telemetry from network sources.") + stale_msg,
        )
    return result


@app.post("/api/integrations/syslog/ingest")
def ingest_syslog_messages(req: SyslogIngestRequest):
    """
    Ingests RFC 5424 / RFC 3164 Syslog messages into the live parsing pipeline.
    """
    manager = get_integration_manager()
    count = manager.ingest_syslog(req.messages, device_id=req.device_id)
    return {"success": True, "ingested_messages": count}


# =====================================================================
# COLLECTOR AGENT & ON-PREMISE INGESTION ENDPOINTS
# =====================================================================

class CollectorEnrollRequest(BaseModel):
    name: str = "LAN-Collector-01"
    backend_url: Optional[str] = None


@app.post("/api/collectors/enroll")
def enroll_collector(req: CollectorEnrollRequest, request: Request):
    """
    Generates a secure enrollment token and copyable pairing commands for a new collector.
    """
    hub = get_collector_hub()
    base_url = req.backend_url or str(request.base_url).rstrip("/")
    return hub.create_enrollment(name=req.name, backend_base_url=base_url)


@app.get("/api/collectors")
def list_collectors():
    """
    Returns all registered collectors with their live heartbeat status.
    """
    hub = get_collector_hub()
    return hub.list_collectors()


@app.post("/api/collectors/register")
def register_collector(req: CollectorRegisterRequest):
    """
    Called by on-premise collector during startup to complete cryptographic pairing.
    """
    hub = get_collector_hub()
    try:
        return hub.register_collector(req)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/collectors/heartbeat")
def collector_heartbeat(req: CollectorHeartbeatRequest):
    """
    Periodic keepalive ping sent by on-premise collector.
    """
    hub = get_collector_hub()
    try:
        return hub.heartbeat(req)
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/collectors/{collector_id}/revoke")
def revoke_collector(collector_id: str):
    """
    Revokes an on-premise collector, disabling its session immediately.
    """
    hub = get_collector_hub()
    if not hub.revoke_collector(collector_id):
        raise HTTPException(status_code=404, detail="Collector not found")
    return {"success": True, "message": f"Collector '{collector_id}' revoked."}


@app.post("/api/collectors/telemetry")
def ingest_collector_telemetry(req: TelemetryPushRequest):
    """
    Ingests live telemetry records streamed outbound from a paired collector.
    """
    hub = get_collector_hub()
    try:
        count = hub.ingest_telemetry(req)
        return {"success": True, "ingested_records": count, "device_id": req.device_id}
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/collectors/inventory")
def get_collector_inventory():
    """
    Comprehensive inventory of collectors and registered devices with metric availability.
    """
    hub = get_collector_hub()
    collectors = hub.list_collectors()
    devices = hub.list_devices()
    return {
        "collectors_count": len(collectors),
        "online_collectors_count": len([c for c in collectors if c.status == "ONLINE"]),
        "devices_count": len(devices),
        "collectors": [c.model_dump() for c in collectors],
        "devices": [d.model_dump() for d in devices],
    }


@app.get("/api/collectors/{collector_id}/devices")
def list_collector_devices(collector_id: str):
    """
    Lists devices registered to a specific collector.
    """
    hub = get_collector_hub()
    return hub.list_devices(collector_id=collector_id)


@app.post("/api/collectors/{collector_id}/devices")
def register_device_to_collector(collector_id: str, req: DeviceRegisterRequest):
    """
    Registers a new network device to a collector's allowlist.
    """
    hub = get_collector_hub()
    try:
        dev = hub.register_device(collector_id, req)
        return dev
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/collectors/{collector_id}/devices/{device_id}")
def delete_collector_device(collector_id: str, device_id: str):
    """
    Deletes a registered device.
    """
    hub = get_collector_hub()
    if not hub.delete_device(device_id):
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found.")
    return {"success": True, "message": f"Device '{device_id}' removed."}


# =====================================================================
# OFFICIAL PROBLEM-STATEMENT TELEMETRY GENERATOR ENDPOINTS
# =====================================================================

class OfficialGeneratorDiagnoseRequest(BaseModel):
    fault_type: str = "normal"
    raw_telemetry: Optional[Dict[str, Any]] = None


@app.get("/api/generator/generate")
def get_generated_telemetry(fault_type: str = "normal"):
    """
    Generates synthetic telemetry using the exact problem-statement generator.
    Supports: 'normal', 'latency_spike', 'hardware_failure'.
    Strictly marked with telemetry_origin='GENERATED_TEST'.
    """
    clean_type = (fault_type or "normal").strip().lower()
    if clean_type not in VALID_FAULT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fault_type '{fault_type}'. Supported: {sorted(list(VALID_FAULT_TYPES))}",
        )
    raw_data = generate_telemetry(clean_type)
    return {
        "success": True,
        "fault_type": clean_type,
        "telemetry_origin": "GENERATED_TEST",
        "raw_telemetry": raw_data,
    }


@app.post("/api/generator/validate")
def validate_telemetry_payload(payload: Dict[str, Any]):
    """
    Validates a problem-statement telemetry payload against official specifications.
    """
    valid, err = validate_generated_payload(payload)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Validation failed: {err}")
    return {"success": True, "valid": True, "message": "Telemetry adheres to official generator schema."}


@app.post("/api/generator/diagnose")
def diagnose_generated_telemetry(req: OfficialGeneratorDiagnoseRequest):
    """
    Runs the multi-agent diagnosis pipeline over problem-statement generated telemetry.
    Strictly tags output with telemetry_origin='GENERATED_TEST' to preserve provenance.
    Never overwrites real live router telemetry or falls back to synthetic files.
    """
    clean_type = (req.fault_type or "normal").strip().lower()
    if clean_type not in VALID_FAULT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fault_type '{req.fault_type}'. Supported: {sorted(list(VALID_FAULT_TYPES))}",
        )

    # 1. Use provided raw telemetry or generate fresh
    raw_data = req.raw_telemetry
    if not raw_data:
        raw_data = generate_telemetry(clean_type)

    # 2. Validate payload
    valid, err = validate_generated_payload(raw_data)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Malformed telemetry payload: {err}")

    # 3. Adapt to canonical record with telemetry_origin='GENERATED_TEST'
    try:
        record = adapt_to_canonical_record(raw_data, fault_type=clean_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to adapt telemetry: {str(e)}")

    # 4. Execute Multi-Agent Diagnosis Pipeline
    inc_id = f"INC-GEN-{uuid.uuid4().hex[:6]}"
    result = orchestrator.run_diagnosis(
        telemetry=[record],
        incident_id=inc_id,
        scenario_id=f"official_gen_{clean_type}",
    )

    # Guarantee provenance is strictly GENERATED_TEST
    result["telemetry_origin"] = "GENERATED_TEST"
    if "canonical_report" in result:
        result["canonical_report"]["telemetry_origin"] = "GENERATED_TEST"

    return {
        "success": True,
        "incident_id": inc_id,
        "fault_type": clean_type,
        "telemetry_origin": "GENERATED_TEST",
        "raw_telemetry": raw_data,
        "status": result["status"],
        "suspected_root_cause": result["suspected_root_cause"],
        "confidence": result["confidence"],
        "affected_devices": result["affected_devices"],
        "timeline_events": result.get("timeline_events", []),
        "competing_hypotheses": result.get("competing_hypotheses", []),
        "report": result.get("canonical_report"),
        "message_bus": result.get("message_bus", []),
        "telemetry": result.get("telemetry", []),
        "full_result": result,
    }


