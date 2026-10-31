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
    HYPOTHESIS_CHALLENGED = "HYPOTHESIS_CHALLENGED"
    HYPOTHESIS_REJECTED = "HYPOTHESIS_REJECTED"
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
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
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
    interface_id: Optional[str] = None
    interface_oper_status: Optional[str] = None
    interface_admin_status: Optional[str] = None
    interface_in_octets: Optional[int] = None
    interface_out_octets: Optional[int] = None
    interface_in_discards: Optional[int] = None
    interface_out_discards: Optional[int] = None
    sys_name: Optional[str] = None
    sys_descr: Optional[str] = None
    sys_uptime_sec: Optional[float] = None
    
    # Connectivity metrics
    link_id: Optional[str] = None
    target_device_id: Optional[str] = None
    wifi_rssi_dbm: Optional[float] = None
    wifi_snr_db: Optional[float] = None
    wifi_retry_pct: Optional[float] = None
    dns_response_ms: Optional[float] = None
    dhcp_response_ms: Optional[float] = None
    dhcp_pool_utilization_pct: Optional[float] = None

    # Origin & Source metadata (SIMULATED_SCENARIO, CUSTOM_IMPORT, LIVE_HOST, LIVE_DEVICE, GENERATED_TEST)
    telemetry_origin: str = Field(
        default="SIMULATED_SCENARIO",
        description="SIMULATED_SCENARIO, CUSTOM_IMPORT, LIVE_HOST, LIVE_DEVICE, GENERATED_TEST",
    )
    source_id: Optional[str] = Field(default=None, description="Identifier of live network source adapter")

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
    telemetry_origin: Optional[str] = "SIMULATED_SCENARIO"


class HypothesisStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SUPPORTED = "SUPPORTED"
    CHALLENGED = "CHALLENGED"
    REJECTED = "REJECTED"
    CONFIRMED = "CONFIRMED"


class CompetingHypothesis(BaseModel):
    hypothesis_id: str
    name: str
    description: str
    probability: float
    supporting_evidence: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)
    status: str = "PROPOSED"  # PROPOSED, SUPPORTED, CHALLENGED, REJECTED, CONFIRMED (also VALIDATED/REFUTED)
    reasoning: Optional[str] = None
    implicated_devices: List[str] = Field(default_factory=list)


class RemediationAction(BaseModel):
    step: int
    action: str
    target_device: str
    command: Optional[str] = None
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH
    rationale: str
    rollback_plan: Optional[str] = None
    expected_outcome: Optional[str] = None
    supporting_evidence: List[str] = Field(default_factory=list)
    requires_human_approval: bool = False


class InvestigationExplanation(BaseModel):
    """
    Structured reasoning artifact explaining why the multi-agent swarm arrived at its conclusion.
    """
    initial_symptoms: List[str] = Field(default_factory=list)
    initial_hypotheses: List[str] = Field(default_factory=list)
    inter_agent_queries: List[Dict[str, Any]] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    refuting_evidence: List[str] = Field(default_factory=list)
    final_resolution: str = ""
    tradeoffs_and_risks: List[str] = Field(default_factory=list)
    assumptions_and_limitations: List[str] = Field(default_factory=list)
    conflict_status: Optional[str] = Field(default="NO_CONFLICT", description="NO_CONFLICT, RESOLVED, or UNRESOLVED")
    resolved_conflict_details: Optional[Dict[str, Any]] = Field(default=None, description="Details of initial hypothesis, refuting evidence, and resolution logic")


class InvestigationTerminationReason(str, Enum):
    EVIDENTIAL_CONSENSUS = "EVIDENTIAL_CONSENSUS"
    SUFFICIENT_PROOF = "SUFFICIENT_PROOF"
    MAX_ROUNDS_REACHED = "MAX_ROUNDS_REACHED"
    INSUFFICIENT_TELEMETRY = "INSUFFICIENT_TELEMETRY"


class AgentInvestigationTrace(BaseModel):
    """
    Detailed audit trace of agent reasoning, interrogation priority, and stopping condition.
    """
    investigation_id: str
    total_rounds_executed: int
    max_rounds_allowed: int = 2
    agents_queried_sequence: List[str] = Field(default_factory=list)
    evidence_collected_count: int = 0
    hypotheses_revised_count: int = 0
    termination_reason: InvestigationTerminationReason
    termination_explanation: str
    query_priority_ranking: List[str] = Field(default_factory=list)
    uncertainty_factors: List[str] = Field(default_factory=list)


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ProactiveRiskWarning(BaseModel):
    """
    Proactive warning emitted by trend analysis before hard SLA breach thresholds are crossed.
    """
    warning_id: str
    device_id: str
    metric: str
    current_value: float
    projected_value_10m: float
    threshold_limit: float
    unit: str
    drift_rate_per_min: float
    severity: RiskSeverity
    time_to_breach_minutes: Optional[float] = None
    title: str
    expected_impact: str
    preventive_remediation: str
    confidence: float
    evidence: Dict[str, Any] = Field(default_factory=dict)
    status: str = "ACTIVE_WATCH"  # ACTIVE_WATCH, ACKNOWLEDGED, MITIGATED


class CanonicalDiagnosticReport(BaseModel):
    """
    Standardized final diagnostic output required by Problem Statement.
    """
    incident_id: str
    investigation_id: Optional[str] = None
    timestamp: str
    status: DiagnosticStatus
    suspected_root_cause: str
    confidence: float
    confidence_calculation_method: str = "Multi-Factor Evidential Likelihood & Anomaly Scoring"
    affected_devices: List[str]
    supporting_evidence: List[EvidenceItem]
    alternative_causes: List[CompetingHypothesis]
    primary_hypothesis: Optional[CompetingHypothesis] = None
    fault_propagation_paths: List[List[str]] = Field(default_factory=list)
    missing_telemetry: List[str] = Field(default_factory=list)
    recommended_actions: List[RemediationAction]
    investigation_explanation: Optional[InvestigationExplanation] = None
    investigation_trace: Optional[AgentInvestigationTrace] = None
    proactive_warnings: List[ProactiveRiskWarning] = Field(default_factory=list)
    evidence_sources: List[str]
    limitations: List[str]
    next_diagnostic_checks: List[str] = Field(default_factory=list)
    observed_facts: List[str] = Field(default_factory=list)
    execution_time_ms: float
    inter_agent_messages_count: int
    telemetry_origin: str = Field(
        default="SIMULATED_SCENARIO",
        description="SIMULATED_SCENARIO, CUSTOM_IMPORT, LIVE_HOST, LIVE_DEVICE, GENERATED_TEST",
    )
    protocol_rejection_confidence: Optional[float] = Field(
        default=None,
        description="Confidence that an incompatible protocol message was correctly rejected (1.0 = 100%)",
    )
    conflict_status: Optional[str] = Field(
        default="NO_CONFLICT",
        description="NO_CONFLICT, RESOLVED, or UNRESOLVED",
    )
    resolved_conflict_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Details of initial hypothesis, refuting evidence, and resolution logic",
    )


# -------------------------------------------------------------
# DIGITAL TWIN & SIMULATION MODELS
# -------------------------------------------------------------

class DeviceOperationalStatus(str, Enum):
    OPTIMAL = "OPTIMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    OFFLINE = "OFFLINE"


class SLAStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    AT_RISK = "AT_RISK"
    BREACHED = "BREACHED"


class DigitalTwinDevice(BaseModel):
    """
    State representation of a network device within the simulated Digital Twin environment.
    """
    device_id: str
    name: str
    device_type: str
    role: str
    ip: str
    status: DeviceOperationalStatus
    health_score: float = Field(..., ge=0.0, le=100.0, description="Health index from 0 to 100")
    sla_status: SLAStatus
    upstream_dependencies: List[str] = Field(default_factory=list)
    downstream_dependencies: List[str] = Field(default_factory=list)
    current_telemetry: Dict[str, Any] = Field(default_factory=dict)
    baseline_sla: Dict[str, Any] = Field(default_factory=dict)
    active_anomalies: List[str] = Field(default_factory=list)
    implicated_in_fault: bool = False
    fault_propagation_role: Optional[str] = None  # "ROOT_CAUSE", "TRANSIT_DEGRADED", "AFFECTED_LEAF", "NORMAL"


class DigitalTwinSnapshot(BaseModel):
    """
    Comprehensive snapshot of the network digital twin benchmark environment.
    """
    timestamp: str
    environment_mode: str = "BENCHMARK_DIGITAL_TWIN_SIMULATION"
    devices: List[DigitalTwinDevice]
    network_health_index: float = Field(..., ge=0.0, le=100.0)
    sla_compliance_pct: float = Field(..., ge=0.0, le=100.0)
    active_incidents_count: int
    fault_propagation_paths: List[List[str]] = Field(default_factory=list)


class RemediationStrategy(BaseModel):
    """
    Candidate remediation strategy evaluated by the What-If Simulator.
    """
    strategy_id: str
    name: str
    description: str
    category: str
    target_device: str
    command: str
    rollback_command: str
    intervention_type: str  # AUTOMATED, OPERATOR_APPROVAL, MAINTENANCE_WINDOW
    operational_risk: str  # LOW, MEDIUM, HIGH
    recovery_time_seconds: int
    rollback_available: bool = True
    effectiveness_pct: float = 95.0
    tradeoffs: str
    projected_telemetry: Dict[str, Any]
    expected_benefits: List[str] = Field(default_factory=list)
    potential_risks: List[str] = Field(default_factory=list)


class SimulationResult(BaseModel):
    """
    Deterministic projection generated by the What-If Remediation Simulator.
    """
    simulation_id: str
    incident_id: str
    strategy_id: str
    strategy_name: str
    target_device: str
    before_telemetry: Dict[str, Any]
    projected_telemetry: Dict[str, Any]
    telemetry_deltas: Dict[str, Dict[str, Any]]
    device_health_before: float
    device_health_after: float
    sla_status_before: str
    sla_status_after: str
    fault_path_cleared: bool
    recovery_status: str  # FULL_RECOVERY, PARTIAL_MITIGATION, STABILIZED
    expected_benefits: List[str] = Field(default_factory=list)
    potential_risks: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class StrategyComparisonMatrix(BaseModel):
    """
    Side-by-side comparative trade-off matrix of multiple remediation alternatives.
    """
    incident_id: str
    device_id: str
    root_cause: str
    strategies: List[RemediationStrategy]
    recommended_strategy_id: str
    recommendation_rationale: str
    comparison_summary: str


class IncidentPriority(str, Enum):
    P1 = "P1"  # Critical
    P2 = "P2"  # High
    P3 = "P3"  # Medium
    P4 = "P4"  # Low


class IncidentPriorityItem(BaseModel):
    """
    Prioritized incident queue item for operational NOC triage.
    """
    incident_id: str
    device_id: str
    title: str
    severity: str  # CRITICAL, WARNING, INFO
    priority: IncidentPriority
    priority_score: float = Field(..., ge=0.0, le=100.0)
    sla_breached: bool
    affected_devices_count: int
    affected_devices: List[str]
    service_impact: str
    confidence: float
    propagation_risk: str  # HIGH, MEDIUM, LOW
    suspected_root_cause: str
    recommended_action: str
    status: str = "OPEN"  # OPEN, SIMULATED, MITIGATED


class InvestigationEventType(str, Enum):
    INCIDENT_DETECTED = "INCIDENT_DETECTED"
    AGENT_ACTIVATED = "AGENT_ACTIVATED"
    AGENT_DEACTIVATED = "AGENT_DEACTIVATED"
    TELEMETRY_INGESTED = "TELEMETRY_INGESTED"
    INITIAL_HYPOTHESIS_PROPOSED = "INITIAL_HYPOTHESIS_PROPOSED"
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    CROSS_AGENT_QUERY = "CROSS_AGENT_QUERY"
    CROSS_AGENT_RESPONSE = "CROSS_AGENT_RESPONSE"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    HYPOTHESIS_CHALLENGED = "HYPOTHESIS_CHALLENGED"
    HYPOTHESIS_REJECTED = "HYPOTHESIS_REJECTED"
    HYPOTHESIS_CONFIRMED = "HYPOTHESIS_CONFIRMED"
    ROOT_CAUSE_RESOLVED = "ROOT_CAUSE_RESOLVED"
    REMEDIATION_GENERATED = "REMEDIATION_GENERATED"
    INVESTIGATION_COMPLETE = "INVESTIGATION_COMPLETE"


class InvestigationEvent(BaseModel):
    """
    Structured timeline event emitted during autonomous multi-agent investigation.
    Drives the Autonomous Investigation Replay in the UI.
    """
    event_id: str
    step_number: int
    timestamp: str
    phase: str  # INGESTION, DOMAIN_ANALYSIS, CROSS_EXAMINATION, CONFLICT_RESOLUTION, SYNTHESIS, REPORTING
    event_type: InvestigationEventType
    agent_id: str
    target_agent_id: Optional[str] = None
    device_id: Optional[str] = None
    title: str
    description: str
    evidence_snapshot: Optional[Dict[str, Any]] = None
    hypotheses_snapshot: Optional[List[Dict[str, Any]]] = None
    affected_devices: List[str] = Field(default_factory=list)
    agent_message: Optional[Dict[str, Any]] = None
    elapsed_ms: float = 0.0


# -------------------------------------------------------------
# AUTONOMOUS NETWORK INTELLIGENCE & CORRELATION MODELS
# -------------------------------------------------------------

class CorrelationRelationshipType(str, Enum):
    SHARED_UPSTREAM_DEVICE = "SHARED_UPSTREAM_DEVICE"
    SHARED_TOPOLOGY_PATH = "SHARED_TOPOLOGY_PATH"
    COMMON_METRIC_PATTERN = "COMMON_METRIC_PATTERN"
    TEMPORAL_COINCIDENCE = "TEMPORAL_COINCIDENCE"
    CASCADING_PROPAGATION = "CASCADING_PROPAGATION"


class CorrelatedIncidentCluster(BaseModel):
    """
    Cluster of multiple symptoms/incidents grouped by common topological or temporal root cause.
    """
    cluster_id: str
    title: str
    root_cause_candidate: str
    primary_device: str
    implicated_devices: List[str]
    incident_ids: List[str]
    relationship_type: CorrelationRelationshipType
    relationship_confidence: float = Field(..., ge=0.0, le=1.0)
    status: str = "CONFIRMED"  # CONFIRMED vs SUSPECTED
    correlation_reasoning: str
    common_upstream_node: Optional[str] = None
    recommended_unified_remediation: str
    prevented_redundant_actions: int = 1


class MetricPenalty(BaseModel):
    """
    Itemized deduction contributing to the explainable device health score.
    """
    metric_name: str
    observed_value: Any
    sla_limit: Any
    unit: str
    points_deducted: float
    reason: str


class DeviceHealthBreakdown(BaseModel):
    """
    Fully explainable health audit for an individual network node.
    """
    device_id: str
    device_name: str
    role: str
    health_score: float = Field(..., ge=0.0, le=100.0)
    operational_status: str
    sla_status: str
    penalties: List[MetricPenalty] = Field(default_factory=list)
    positive_contributions: List[str] = Field(default_factory=list)


class NetworkHealthScoreReport(BaseModel):
    """
    Holistic and transparent explainable health assessment across the entire network fabric.
    """
    overall_health_score: float = Field(..., ge=0.0, le=100.0)
    status: str  # OPTIMAL, DEGRADED, CRITICAL
    calculation_methodology: str = "Multi-Factor Weighted Penalty Deduction against Golden SLA Baselines"
    total_devices_evaluated: int
    sla_compliance_rate_pct: float
    device_breakdowns: List[DeviceHealthBreakdown]
    top_risk_factors: List[str]
    caveats: List[str] = Field(default_factory=list)
