"""
Base Agent Abstract Class for NetCoop AI Multi-Agent Network Diagnosis.
Defines agent lifecycle, structured canonical messaging, and state management.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from app.protocol.schema import (
    AgentMessage,
    MessageType,
    TelemetryRecord,
    EvidenceItem,
    CURRENT_SCHEMA_VERSION,
)


class BaseAgent(ABC):
    """
    Abstract Base Agent enforcing canonical message exchange and state tracking.
    """

    def __init__(self, agent_id: str, name: str, role: str):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.status = "IDLE"  # IDLE, ANALYZING, AWAITING_PEER, COMPLETE, ERROR
        self.current_task = ""
        self.findings_history: List[AgentMessage] = []
        self.sent_messages: List[AgentMessage] = []
        self.received_messages: List[AgentMessage] = []

    def set_status(self, status: str, task: str = ""):
        self.status = status
        self.current_task = task

    def create_message(
        self,
        message_type: MessageType,
        device_id: Optional[str] = None,
        metric: Optional[str] = None,
        value: Optional[Any] = None,
        unit: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
        findings: Optional[List[str]] = None,
        target_agent_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> AgentMessage:
        """Helper to create a compliant canonical AgentMessage."""
        msg = AgentMessage(
            agent_id=self.agent_id,
            target_agent_id=target_agent_id,
            message_type=message_type,
            schema_version=CURRENT_SCHEMA_VERSION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            device_id=device_id,
            metric=metric,
            value=value,
            unit=unit,
            evidence=evidence or {},
            confidence=confidence,
            findings=findings or [],
            correlation_id=correlation_id or str(uuid.uuid4())[:8],
        )
        self.sent_messages.append(msg)
        return msg

    @abstractmethod
    def analyze(self, telemetry: List[TelemetryRecord]) -> List[AgentMessage]:
        """Process telemetry records and emit initial findings/anomalies."""
        pass

    @abstractmethod
    def handle_query(self, query: AgentMessage, telemetry: List[TelemetryRecord]) -> AgentMessage:
        """Handle an inter-agent query message requesting evidence or clarification."""
        pass

    def reset(self):
        """Reset agent runtime state for a new diagnosis session."""
        self.status = "IDLE"
        self.current_task = ""
        self.findings_history.clear()
        self.sent_messages.clear()
        self.received_messages.clear()
