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


class TargetType(str, Enum):
    PRIVATE_IPV4 = "PRIVATE_IPV4"
    PUBLIC_IPV4 = "PUBLIC_IPV4"
    HOSTNAME = "HOSTNAME"
    IPV6 = "IPV6"
    INVALID = "INVALID"


class TargetClassification(BaseModel):
    raw_target: str
    clean_target: str
    target_type: TargetType
    is_private: bool
    is_loopback: bool
    is_safe: bool
    resolved_ip: Optional[str] = None
    validation_error: Optional[str] = None
    recommended_routing: str  # "LOCAL_COLLECTOR" | "CLOUD_OR_COLLECTOR" | "BLOCKED"
    routing_explanation: str


def classify_target(target_str: str) -> TargetClassification:
    """
    Classifies a target host as PRIVATE_IPV4, PUBLIC_IPV4, HOSTNAME, or IPV6,
    and enforces strict security validation (anti-scanning, anti-SSRF, and command injection prevention).
    """
    raw = (target_str or "").strip()
    if not raw:
        return TargetClassification(
            raw_target=raw,
            clean_target="",
            target_type=TargetType.INVALID,
            is_private=False,
            is_loopback=False,
            is_safe=False,
            validation_error="Host cannot be empty.",
            recommended_routing="BLOCKED",
            routing_explanation="Empty target string provided.",
        )

    # 1. Reject range formats, list separators, wildcards, shell injection characters
    illegal_chars = ["*", "?", ";", "&", "|", "`", "$", ",", " ", "\t", "<", ">", '"', "'"]
    if any(c in raw for c in illegal_chars):
        return TargetClassification(
            raw_target=raw,
            clean_target=raw,
            target_type=TargetType.INVALID,
            is_private=False,
            is_loopback=False,
            is_safe=False,
            validation_error="Target contains illegal characters or wildcards.",
            recommended_routing="BLOCKED",
            routing_explanation="Security rule: Shell injection, wildcards, and target lists are strictly prohibited.",
        )

    # 2. Anti-Scanning: Reject CIDR subnet masks
    if "/" in raw:
        return TargetClassification(
            raw_target=raw,
            clean_target=raw,
            target_type=TargetType.INVALID,
            is_private=False,
            is_loopback=False,
            is_safe=False,
            validation_error="Subnet CIDR notation is rejected. Enter an explicit single IP or hostname.",
            recommended_routing="BLOCKED",
            routing_explanation="Anti-scanning security rule: Arbitrary subnet scanning (/CIDR) is prohibited.",
        )

    # 3. Reject IP range formats like 192.168.1.1-192.168.1.10
    if "-" in raw and not any(c.isalpha() for c in raw):
        return TargetClassification(
            raw_target=raw,
            clean_target=raw,
            target_type=TargetType.INVALID,
            is_private=False,
            is_loopback=False,
            is_safe=False,
            validation_error="IP range notation is rejected. Enter a single target.",
            recommended_routing="BLOCKED",
            routing_explanation="Anti-scanning rule: IP ranges are prohibited.",
        )

    clean = raw

    # 4. Check for Cloud Metadata Service SSRF targets
    cloud_metadata_ips = {
        "169.254.169.254",  # AWS/GCP/Azure/Render/OpenStack IPv4 metadata
        "169.254.170.2",    # AWS ECS container metadata
        "fd00:ec2::254",    # AWS IPv6 metadata
    }
    cloud_metadata_hosts = {
        "metadata.google.internal",
        "metadata.turing.render.com",
        "instance-data",
    }
    if clean.lower() in cloud_metadata_ips or clean.lower() in cloud_metadata_hosts:
        return TargetClassification(
            raw_target=raw,
            clean_target=clean,
            target_type=TargetType.INVALID,
            is_private=True,
            is_loopback=False,
            is_safe=False,
            validation_error="Target is an internal cloud metadata service. Probing cloud metadata is blocked for SSRF security.",
            recommended_routing="BLOCKED",
            routing_explanation="SSRF security violation: Cloud instance metadata endpoints cannot be targeted.",
        )

    # 5. Try IP address parsing
    try:
        ip = ipaddress.ip_address(clean)
        if isinstance(ip, ipaddress.IPv4Address):
            # Check for broadcast or unspecified
            if ip == ipaddress.IPv4Address("255.255.255.255") or ip == ipaddress.IPv4Address("0.0.0.0"):
                return TargetClassification(
                    raw_target=raw,
                    clean_target=clean,
                    target_type=TargetType.INVALID,
                    is_private=False,
                    is_loopback=False,
                    is_safe=False,
                    validation_error="Target address is an invalid probe destination (broadcast or unspecified 0.0.0.0).",
                    recommended_routing="BLOCKED",
                    routing_explanation="Broadcast and 0.0.0.0 addresses cannot be probed point-to-point.",
                )
            if ip.is_multicast:
                return TargetClassification(
                    raw_target=raw,
                    clean_target=clean,
                    target_type=TargetType.INVALID,
                    is_private=False,
                    is_loopback=False,
                    is_safe=False,
                    validation_error="Multicast IP addresses (224.0.0.0/4) cannot be targeted for point-to-point probes.",
                    recommended_routing="BLOCKED",
                    routing_explanation="Multicast destinations do not support unicast ICMP/TCP diagnostic probes.",
                )

            # Check if private, loopback, or link-local
            is_priv = ip.is_private or ip.is_loopback or ip.is_link_local
            is_loop = ip.is_loopback
            if is_priv:
                return TargetClassification(
                    raw_target=raw,
                    clean_target=clean,
                    target_type=TargetType.PRIVATE_IPV4,
                    is_private=True,
                    is_loopback=is_loop,
                    is_safe=True,
                    recommended_routing="LOCAL_COLLECTOR",
                    routing_explanation="Private LAN IPv4 address (RFC 1918 / loopback / link-local). Cloud backend cannot route to private LANs directly. Must be probed via an authorized on-premise local collector.",
                )
            else:
                return TargetClassification(
                    raw_target=raw,
                    clean_target=clean,
                    target_type=TargetType.PUBLIC_IPV4,
                    is_private=False,
                    is_loopback=False,
                    is_safe=True,
                    recommended_routing="CLOUD_OR_COLLECTOR",
                    routing_explanation="Public Internet IPv4 address. Can be probed directly by cloud backend network stack or routed through a paired local collector.",
                )

        elif isinstance(ip, ipaddress.IPv6Address):
            if ip == ipaddress.IPv6Address("::"):
                return TargetClassification(
                    raw_target=raw,
                    clean_target=clean,
                    target_type=TargetType.INVALID,
                    is_private=False,
                    is_loopback=False,
                    is_safe=False,
                    validation_error="IPv6 unspecified address (::) cannot be targeted.",
                    recommended_routing="BLOCKED",
                    routing_explanation="Unspecified IPv6 address cannot be probed.",
                )
            if ip.is_multicast:
                return TargetClassification(
                    raw_target=raw,
                    clean_target=clean,
                    target_type=TargetType.INVALID,
                    is_private=False,
                    is_loopback=False,
                    is_safe=False,
                    validation_error="IPv6 multicast addresses (ff00::/8) cannot be targeted.",
                    recommended_routing="BLOCKED",
                    routing_explanation="Multicast IPv6 destinations do not support point-to-point interrogation.",
                )

            is_priv = ip.is_private or ip.is_loopback or ip.is_link_local
            is_loop = ip.is_loopback
            return TargetClassification(
                raw_target=raw,
                clean_target=clean,
                target_type=TargetType.IPV6,
                is_private=is_priv,
                is_loopback=is_loop,
                is_safe=True,
                recommended_routing="LOCAL_COLLECTOR" if is_priv else "CLOUD_OR_COLLECTOR",
                routing_explanation="Private/Local IPv6 address. Requires on-premise collector." if is_priv else "Global IPv6 address. Can be probed directly or via collector.",
            )
    except ValueError:
        pass

    # 6. Validate RFC 1123 Hostname
    hostname_regex = re.compile(
        r"^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])"
        r"(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]))*$"
    )
    if not hostname_regex.match(clean) or len(clean) > 253:
        return TargetClassification(
            raw_target=raw,
            clean_target=clean,
            target_type=TargetType.INVALID,
            is_private=False,
            is_loopback=False,
            is_safe=False,
            validation_error=f"Invalid IP address or hostname format: '{clean}'.",
            recommended_routing="BLOCKED",
            routing_explanation="Hostname violates RFC 1123 format specifications.",
        )

    # Check for known private or local domains
    clean_lower = clean.lower()
    local_suffixes = (".local", ".lan", ".internal", ".corp", ".home.arpa", ".intranet")
    is_local_domain = clean_lower == "localhost" or clean_lower.endswith(local_suffixes)

    return TargetClassification(
        raw_target=raw,
        clean_target=clean,
        target_type=TargetType.HOSTNAME,
        is_private=is_local_domain,
        is_loopback=clean_lower == "localhost",
        is_safe=True,
        recommended_routing="LOCAL_COLLECTOR" if is_local_domain else "CLOUD_OR_COLLECTOR",
        routing_explanation="Local private domain hostname. Must be resolved and probed via local collector inside LAN." if is_local_domain else "Public or resolvable DNS hostname. Can be probed directly or via collector.",
    )


def validate_target_host(v: str) -> str:
    """
    Validates target host. Prevents CIDR subnet notations, IP ranges,
    and scanning characters to ensure strict point-to-point interrogation.
    """
    res = classify_target(v)
    if not res.is_safe or res.validation_error:
        raise ValueError(res.validation_error or f"Invalid target host: '{v}'")
    return res.clean_target


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

