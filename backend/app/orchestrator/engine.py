"""
Multi-Agent Orchestrator Engine for NetCoop AI.
Executes the cooperative multi-agent fault diagnosis workflow, records execution traces,
and manages genuine inter-agent message exchange.
"""

from typing import List, Dict, Any, Optional, Tuple
import time
import uuid
from datetime import datetime, timezone

from app.protocol.schema import (
    AgentMessage,
    TelemetryRecord,
    MessageType,
    DiagnosticStatus,
    CanonicalDiagnosticReport,
    CURRENT_SCHEMA_VERSION,
)
from app.protocol.normalizer import (
    TelemetryNormalizer,
    InteroperabilityValidator,
    ProtocolError,
    MalformedDataError,
    SchemaVersionMismatchError,
    MissingFieldError,
)
from app.agents.performance_agent import PerformanceAgent
from app.agents.infrastructure_agent import InfrastructureAgent
from app.agents.connectivity_agent import ConnectivityAgent
from app.agents.correlation_agent import FaultCorrelationAgent
from app.agents.recommendation_agent import RecommendationAgent


class MultiAgentOrchestrator:
    """
    Coordinates domain agents, message bus, conflict resolution, and final report assembly.
    """

    def __init__(self):
        self.perf_agent = PerformanceAgent()
        self.infra_agent = InfrastructureAgent()
        self.conn_agent = ConnectivityAgent()
        self.corr_agent = FaultCorrelationAgent()
        self.recom_agent = RecommendationAgent()

        self.agents_map = {
            self.perf_agent.agent_id: self.perf_agent,
            self.infra_agent.agent_id: self.infra_agent,
            self.conn_agent.agent_id: self.conn_agent,
            self.corr_agent.agent_id: self.corr_agent,
            self.recom_agent.agent_id: self.recom_agent,
        }

    def reset(self):
        """Reset state of all agents."""
        for agent in self.agents_map.values():
            agent.reset()

    def run_diagnosis(
        self,
        telemetry: List[TelemetryRecord],
        incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end multi-agent diagnosis pipeline.
        Returns full execution trace containing:
          - execution_trace (step-by-step logs with timeline)
          - message_bus (all inter-agent messages in order)
          - canonical_report (CanonicalDiagnosticReport)
          - agent_states (snapshot of all agent states)
          - affected_nodes (for topology pulsing)
        """
        start_time = time.perf_counter()
        self.reset()
        inc_id = incident_id or f"INC-{uuid.uuid4().hex[:6].upper()}"

        message_bus: List[AgentMessage] = []
        execution_trace: List[Dict[str, Any]] = []

        def log_step(phase: str, agent_id: str, description: str, data: Optional[Dict[str, Any]] = None):
            execution_trace.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "phase": phase,
                "agent_id": agent_id,
                "description": description,
                "data": data or {},
            })

        log_step("INGESTION", "orchestrator", f"Ingested {len(telemetry)} telemetry records for Incident {inc_id}")

        # -------------------------------------------------------------
        # STEP 1: Specialized Domain Agents Parallel Analysis
        # -------------------------------------------------------------
        log_step("DOMAIN_ANALYSIS", self.perf_agent.agent_id, "Performance Agent analyzing latency, jitter, loss & queue drops")
        perf_messages = self.perf_agent.analyze(telemetry)
        for msg in perf_messages:
            InteroperabilityValidator.validate_message(msg.model_dump())
            message_bus.append(msg)

        log_step("DOMAIN_ANALYSIS", self.infra_agent.agent_id, "Infrastructure Agent analyzing CPU, memory & interface integrity")
        infra_messages = self.infra_agent.analyze(telemetry)
        for msg in infra_messages:
            InteroperabilityValidator.validate_message(msg.model_dump())
            message_bus.append(msg)

        log_step("DOMAIN_ANALYSIS", self.conn_agent.agent_id, "Connectivity Agent analyzing RF signal, DNS & DHCP availability")
        conn_messages = self.conn_agent.analyze(telemetry)
        for msg in conn_messages:
            InteroperabilityValidator.validate_message(msg.model_dump())
            message_bus.append(msg)

        all_domain_messages = perf_messages + infra_messages + conn_messages
        log_step("SYNTHESIS", "orchestrator", f"Gathered {len(all_domain_messages)} initial anomalies from domain agents")

        # -------------------------------------------------------------
        # STEP 2: Fault Correlation Agent Inter-Agent Dialogue & Synthesis
        # -------------------------------------------------------------
        log_step("CORRELATION", self.corr_agent.agent_id, "Fault Correlation Agent commencing inter-agent cross-examination")

        (
            status,
            root_cause,
            confidence,
            affected_devices,
            hypotheses,
            evidence_store,
            limitations,
            dialogue_messages,
        ) = self.corr_agent.cross_examine_and_correlate(
            domain_messages=all_domain_messages,
            telemetry=telemetry,
            performance_agent=self.perf_agent,
            infrastructure_agent=self.infra_agent,
            connectivity_agent=self.conn_agent,
        )

        for msg in dialogue_messages:
            InteroperabilityValidator.validate_message(msg.model_dump())
            message_bus.append(msg)

        log_step(
            "CORRELATION",
            self.corr_agent.agent_id,
            f"Correlation complete: {root_cause} (Confidence: {round(confidence*100, 1)}%)",
            {"competing_hypotheses_count": len(hypotheses), "status": status.value}
        )

        # -------------------------------------------------------------
        # STEP 3: Recommendation Agent Compiles Report & Runbooks
        # -------------------------------------------------------------
        log_step("RECOMMENDATION", self.recom_agent.agent_id, "Recommendation Agent generating remediation runbooks")

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        evidence_sources = [
            f"{self.perf_agent.name} ({self.perf_agent.agent_id})",
            f"{self.infra_agent.name} ({self.infra_agent.agent_id})",
            f"{self.conn_agent.name} ({self.conn_agent.agent_id})",
            f"{self.corr_agent.name} ({self.corr_agent.agent_id})",
        ]

        canonical_report = self.recom_agent.compile_canonical_report(
            incident_id=inc_id,
            status=status,
            root_cause=root_cause,
            confidence=confidence,
            affected_devices=affected_devices,
            supporting_evidence=evidence_store,
            alternative_causes=hypotheses,
            evidence_sources=evidence_sources,
            limitations=limitations,
            execution_time_ms=elapsed_ms,
            inter_agent_messages_count=len(message_bus),
        )

        for msg in self.recom_agent.sent_messages:
            InteroperabilityValidator.validate_message(msg.model_dump())
            message_bus.append(msg)

        log_step("COMPLETE", "orchestrator", f"Diagnosis finished in {round(elapsed_ms, 2)} ms with {len(message_bus)} messages")

        # Snapshot agent states
        agent_states = [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "role": a.role,
                "status": a.status,
                "current_task": a.current_task,
                "messages_sent": len(a.sent_messages),
                "messages_received": len(a.received_messages),
            }
            for a in self.agents_map.values()
        ]

        return {
            "incident_id": inc_id,
            "status": status.value,
            "suspected_root_cause": root_cause,
            "confidence": round(confidence, 4),
            "affected_devices": affected_devices,
            "execution_time_ms": round(elapsed_ms, 2),
            "canonical_report": canonical_report.model_dump(),
            "message_bus": [m.model_dump() for m in message_bus],
            "execution_trace": execution_trace,
            "agent_states": agent_states,
        }
