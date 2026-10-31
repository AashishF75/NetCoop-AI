"""
FastAPI Application for NetCoop AI.
Provides REST APIs for multi-agent network fault diagnosis,
telemetry ingestion (JSON/CSV), canonical protocol validation,
scenario benchmarks, and interactive visualization.
"""

from typing import List, Dict, Any, Optional
import time
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
from app.scenarios.generator import ScenarioCatalog, get_default_topology

app = FastAPI(
    title="NetCoop AI — Multi-Agent Network Fault Diagnosis Platform",
    description="Agentic cooperative network diagnosis platform with canonical JSON protocol interoperability.",
    version="1.0.0",
)

# Enable CORS for React Vite development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = MultiAgentOrchestrator()


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
    result = orchestrator.run_diagnosis(telemetry_records, incident_id=req.incident_id)
    return result
