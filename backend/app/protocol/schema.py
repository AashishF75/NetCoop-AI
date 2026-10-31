"""
Canonical JSON Message Protocol & Schemas for NetCoop AI.
Enforces strict typing, semantic validation, and interoperability across agents.
"""

from typing import List, Dict, Any, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone


class MessageType(str, Enum):
    TELEMETRY_ANOMALY = "TELEMETRY_ANOMALY"
    QUERY_EVIDENCE = "QUERY_EVIDENCE"
    QUERY_RESPONSE = "QUERY_RESPONSE"
    HYPOTHESIS_PROPOSAL = "HYPOTHESIS_PROPOSAL"
    HYPOTHESIS_CONFIRMATION = "HYPOTHESIS_CONFIRMATION"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    DIAGNOSTIC_SUMMARY = "DIAGNOSTIC_SUMMARY"
    REMEDIATION_PLAN = "REMEDIATION_PLAN"
    MALFORMED_INPUT_ALERT = "MALFORMED_INPUT_ALERT"
    SCHEMA_VERSION_MISMATCH = "SCHEMA_VERSION_MISMATCH"
    HEARTBEAT = "HEARTBEAT"


class DiagnosticStatus(str, Enum):
    HEALTHY = "HEALTHY"
    CONFIRMED = "CONFIRMED"
    SUSPECTED = "SUSPECTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    DEGRADED = "DEGRADED"


CURRENT_SCHEMA_VERSION = "1.0.0"
SUPPORTED_SCHEMA_VERSIONS = {"1.0.0", "1.0", "1.1"}


class AgentMessage(BaseModel):
    """
    Canonical Inter-Agent Message Protocol.
    All agents must communicate via this structured format.
    """
    agent_id: str = Field(..., description="Unique identifier of originating agent")
    message_type: MessageType = Field(..., description="Type of canonical message")
    schema_version: str = Field(default=CURRENT_SCHEMA_VERSION, description="Semver protocol version")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    device_id: Optional[str] = Field(default=None, description="Network device implicated")
    metric: Optional[str] = Field(default=None, description="Primary metric analyzed")
    value: Optional[Union[float, int, str, Dict[str, Any], None]] = Field(default=None, description="Observed value")
    unit: Optional[str] = Field(default=None, description="Unit of measurement (ms, %, Mbps, etc.)")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Supporting evidence data")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    findings: List[str] = Field(default_factory=list, description="Human-readable conclusions")
    
    # Interoperability routing fields
    target_agent_id: Optional[str] = Field(default=None, description="Target recipient agent if directed query")
    correlation_id: Optional[str] = Field(default=None, description="Trace ID linking query/response thread")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return round(v, 4)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("schema_version must be a non-empty string")
        return v


class TelemetryRecord(BaseModel):
    """
    Network telemetry record model representing a snapshot of device/link metrics.
    """
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    device_id: str = Field(..., description="Device ID e.g. Core-Router-01")
    device_type: str = Field(default="switch", description="router, switch, ap, server, client, dns_server")
    device_status: str = Field(default="UP", description="UP, DOWN, DEGRADED, FLAPPING")
    
    # Performance metrics
    latency_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    packet_loss_pct: Optional[float] = None
    throughput_mbps: Optional[float] = None
    bandwidth_mbps: Optional[float] = None
    utilization_pct: Optional[float] = None
    queue_drops_per_sec: Optional[float] = None
    
    # Infrastructure health metrics
    cpu_utilization_pct: Optional[float] = None
    memory_utilization_pct: Optional[float] = None
    temperature_c: Optional[float] = None
    fan_status: Optional[str] = "OK"
    power_supply_status: Optional[str] = "OK"
    interface_crc_errors: Optional[int] = 0
    interface_flaps: Optional[int] = 0
    
    # Connectivity metrics
    link_id: Optional[str] = None
    target_device_id: Optional[str] = None
    wifi_rssi_dbm: Optional[float] = None
    wifi_snr_db: Optional[float] = None
    wifi_retry_pct: Optional[float] = None
    dns_response_ms: Optional[float] = None
    dhcp_response_ms: Optional[float] = None
    dhcp_pool_utilization_pct: Optional[float] = None

    # Extensible raw metadata
    custom_metrics: Dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    agent_id: str
    device_id: str
    metric: str
    observed_value: Any
    baseline_value: Optional[Any] = None
    threshold: Optional[Any] = None
    unit: str
    severity: str = "INFO" # INFO, WARNING, CRITICAL
    timestamp: str
    summary: str


class CompetingHypothesis(BaseModel):
    hypothesis_id: str
    name: str
    description: str
    probability: float
    supporting_evidence: List[str]
    contradicting_evidence: List[str]
    status: str = "PROPOSED" # PROPOSED, VALIDATED, REFUTED


class RemediationAction(BaseModel):
    step: int
    action: str
    target_device: str
    command: Optional[str] = None
    risk_level: str = "LOW" # LOW, MEDIUM, HIGH
    rationale: str
    rollback_plan: Optional[str] = None


class CanonicalDiagnosticReport(BaseModel):
    """
    Standardized final diagnostic output required by Problem Statement.
    """
    incident_id: str
    timestamp: str
    status: DiagnosticStatus
    suspected_root_cause: str
    confidence: float
    affected_devices: List[str]
    supporting_evidence: List[EvidenceItem]
    alternative_causes: List[CompetingHypothesis]
    recommended_actions: List[RemediationAction]
    evidence_sources: List[str]
    limitations: List[str]
    execution_time_ms: float
    inter_agent_messages_count: int
