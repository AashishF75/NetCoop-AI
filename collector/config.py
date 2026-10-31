"""
Collector Configuration & Local Device Registry.
Stores device credentials locally on the collector machine.
Credentials are NEVER sent to the remote cloud backend.
"""

import os
import json
import re
import ipaddress
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

CONFIG_FILE = Path("collector_config.json")


def detect_default_gateway() -> Optional[str]:
    """
    Dynamically discovers the local network default gateway IP.
    Returns None if undetected or unreachable.
    """
    import sys
    import subprocess
    import socket

    if sys.platform == "win32":
        try:
            out = subprocess.check_output(["route", "print", "0.0.0.0"], text=True, timeout=2.0)
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                    gw = parts[2]
                    if gw and not gw.startswith("0.") and not gw.startswith("127."):
                        return gw
        except Exception:
            pass
    elif sys.platform.startswith("linux") or sys.platform == "darwin":
        try:
            out = subprocess.check_output(["ip", "route"], text=True, timeout=2.0)
            for line in out.splitlines():
                if line.startswith("default via"):
                    return line.split()[2]
        except Exception:
            pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        parts = local_ip.split(".")
        if len(parts) == 4 and parts[0] in ("10", "192", "172"):
            return f"{parts[0]}.{parts[1]}.{parts[2]}.1"
    except Exception:
        pass
    return None


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

    try:
        ipaddress.ip_address(clean_host)
        return clean_host
    except ValueError:
        pass

    hostname_regex = re.compile(
        r"^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])"
        r"(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]))*$"
    )
    if not hostname_regex.match(clean_host):
        raise ValueError(f"Invalid IP address or hostname format: '{clean_host}'")

    return clean_host


class DeviceProtocol(str, Enum):
    SNMP = "SNMP"
    RESTCONF = "RESTCONF"
    TCP_PROBE = "TCP_PROBE"
    PING_PROBE = "PING_PROBE"
    SYSLOG = "SYSLOG"
    WIFI_CONTROLLER = "WIFI_CONTROLLER"
    HOST_METRICS = "HOST_METRICS"


class LocalDeviceConfig(BaseModel):
    """
    Local device definition stored solely on the collector.
    Credentials (passwords, community strings) are stored locally and never sent to cloud.
    """
    device_id: str
    name: str
    device_type: str = "router"
    host: str
    protocol: DeviceProtocol = DeviceProtocol.TCP_PROBE
    port: int = 80
    polling_interval_sec: int = Field(default=15, ge=5, le=3600)
    timeout_sec: float = Field(default=2.5, ge=0.5, le=30.0)

    # Local credentials
    snmp_community: Optional[str] = "public"
    snmp_version: str = "v2c"
    rest_endpoint: Optional[str] = "/restconf/data/ietf-interfaces:interfaces-state"
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    enabled: bool = True

    @field_validator("host")
    @classmethod
    def check_host(cls, v: str) -> str:
        return validate_target_host(v)


class CollectorSettings(BaseModel):
    """
    Local collector agent configuration and pairing tokens.
    """
    collector_id: Optional[str] = None
    collector_name: str = "LAN-Collector-01"
    backend_url: str = "http://127.0.0.1:8000"
    enrollment_token: Optional[str] = None
    session_token: Optional[str] = None
    heartbeat_interval_sec: int = 15
    syslog_port: int = 5140
    default_gateway: Optional[str] = None
    devices: List[LocalDeviceConfig] = Field(default_factory=list)


def load_collector_config(file_path: Path = CONFIG_FILE) -> CollectorSettings:
    """Loads collector config from file, or returns defaults if absent."""
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return CollectorSettings(**data)
        except Exception:
            pass
    return CollectorSettings()


def save_collector_config(settings: CollectorSettings, file_path: Path = CONFIG_FILE) -> None:
    """Persists collector config to file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(settings.model_dump(), f, indent=2)
    except Exception:
        pass

