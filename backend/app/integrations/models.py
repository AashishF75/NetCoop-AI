"""
Data models and schema definitions for Live Network Integrations.
Includes strict IP/hostname validation and write-only credential redaction.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import re
import ipaddress
from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    PING_PROBE = "PING_PROBE"
    SERVER_HOST = "SERVER_HOST"
    REST_API = "REST_API"
    SNMP = "SNMP"
    SYSLOG = "SYSLOG"
    CSV_IMPORT = "CSV_IMPORT"
    JSON_IMPORT = "JSON_IMPORT"


class AuthType(str, Enum):
    NONE = "NONE"
    COMMUNITY_STRING = "COMMUNITY_STRING"
    API_KEY = "API_KEY"
    BEARER_TOKEN = "BEARER_TOKEN"
    BASIC_AUTH = "BASIC_AUTH"


class ConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


def validate_target_host(v: str) -> str:
    """
    Validates target host. Prevents CIDR subnet notations, IP ranges,
    and scanning characters to ensure strict point-to-point interrogation.
    """
    clean_host = v.strip()
    if not clean_host:
        raise ValueError("Host cannot be empty")
    
    if "/" in clean_host:
        raise ValueError("Subnet CIDR notation is rejected. Enter a single IP or hostname.")
    
    if any(c in clean_host for c in ["*", "?", ";", "&", "|", "`", "$", " ", "\t"]):
        raise ValueError("Target host contains illegal characters or wildcards")

    # Verify if valid IP or RFC-compliant hostname
    try:
        ipaddress.ip_address(clean_host)
        return clean_host
    except ValueError:
        pass

    # Validate hostname syntax
    hostname_regex = re.compile(
        r"^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])"
        r"(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]))*$"
    )
    if not hostname_regex.match(clean_host):
        raise ValueError(f"Invalid IP address or hostname format: '{clean_host}'")

    return clean_host


class NetworkSourceConfig(BaseModel):
    """
    Internal configuration representation with secure write-only credentials.
    """
    id: str = Field(description="Unique source identifier")
    name: str = Field(description="Human-readable label for device or feed")
    source_type: SourceType = Field(description="Integration mechanism")
    host: str = Field(description="Target host IP or FQDN")
    port: int = Field(default=80, ge=1, le=65535, description="Target network port")
    endpoint_path: Optional[str] = Field(default="", description="REST path, e.g. /restconf/data")
    
    # Credentials (Write-only, never sent back in public API responses)
    auth_type: AuthType = Field(default=AuthType.NONE)
    community_string: Optional[str] = Field(default=None, description="SNMP Community String")
    username: Optional[str] = Field(default=None, description="Username for Basic Auth")
    password: Optional[str] = Field(default=None, description="Password for Basic Auth")
    api_key: Optional[str] = Field(default=None, description="API Key header")
    bearer_token: Optional[str] = Field(default=None, description="Bearer Token")

    polling_interval_sec: int = Field(default=30, ge=5, le=3600)
    timeout_sec: float = Field(default=3.0, ge=0.5, le=30.0)
    enabled: bool = Field(default=True)
    status: ConnectionStatus = Field(default=ConnectionStatus.UNKNOWN)
    
    last_polled_at: Optional[str] = None
    last_tested_at: Optional[str] = None
    last_error: Optional[str] = None
    metrics_supported: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @field_validator("host")
    @classmethod
    def check_host(cls, v: str) -> str:
        return validate_target_host(v)

    def to_public(self) -> "NetworkSourcePublic":
        """
        Produce a safe, redacted public view guaranteeing zero credential leakage.
        """
        has_credentials = bool(
            self.community_string
            or self.password
            or self.api_key
            or self.bearer_token
        )
        return NetworkSourcePublic(
            id=self.id,
            name=self.name,
            source_type=self.source_type,
            host=self.host,
            port=self.port,
            endpoint_path=self.endpoint_path,
            auth_type=self.auth_type,
            has_credentials=has_credentials,
            polling_interval_sec=self.polling_interval_sec,
            timeout_sec=self.timeout_sec,
            enabled=self.enabled,
            status=self.status,
            last_polled_at=self.last_polled_at,
            last_tested_at=self.last_tested_at,
            last_error=self.last_error,
            metrics_supported=self.metrics_supported,
            created_at=self.created_at,
        )


class NetworkSourcePublic(BaseModel):
    """
    Publicly visible projection of NetworkSourceConfig with credentials strictly redacted.
    """
    id: str
    name: str
    source_type: SourceType
    host: str
    port: int
    endpoint_path: Optional[str] = ""
    auth_type: AuthType
    has_credentials: bool = False
    polling_interval_sec: int
    timeout_sec: float
    enabled: bool
    status: ConnectionStatus
    last_polled_at: Optional[str] = None
    last_tested_at: Optional[str] = None
    last_error: Optional[str] = None
    metrics_supported: List[str] = Field(default_factory=list)
    created_at: str


class ConnectionTestResult(BaseModel):
    """
    Detailed diagnostic test result of an active connection probe.
    """
    source_id: str
    source_name: str
    source_type: SourceType
    success: bool
    status: ConnectionStatus
    latency_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    packet_loss_pct: Optional[float] = None
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    tested_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SourceCreateRequest(BaseModel):
    """
    Payload for registering a new live source.
    """
    name: str
    source_type: SourceType
    host: str
    port: Optional[int] = None
    endpoint_path: Optional[str] = ""
    auth_type: Optional[AuthType] = AuthType.NONE
    community_string: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    polling_interval_sec: Optional[int] = 30
    timeout_sec: Optional[float] = 3.0
    enabled: Optional[bool] = True

    @field_validator("host")
    @classmethod
    def check_host(cls, v: str) -> str:
        return validate_target_host(v)


class SourceUpdateRequest(BaseModel):
    """
    Payload for updating an existing live source.
    """
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    endpoint_path: Optional[str] = None
    auth_type: Optional[AuthType] = None
    community_string: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    polling_interval_sec: Optional[int] = None
    timeout_sec: Optional[float] = None
    enabled: Optional[bool] = None

    @field_validator("host")
    @classmethod
    def check_host(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_target_host(v)
        return v


class SyslogIngestRequest(BaseModel):
    """
    Ingest payload for one or more raw Syslog messages.
    """
    device_id: Optional[str] = None
    messages: List[str] = Field(description="RFC 5424 / RFC 3164 or plain Syslog lines")


class LiveDiagnosisRequest(BaseModel):
    """
    Request to trigger multi-agent diagnosis over live network sources.
    """
    source_ids: Optional[List[str]] = None
    timeout_sec: float = Field(default=5.0, ge=1.0, le=30.0)

