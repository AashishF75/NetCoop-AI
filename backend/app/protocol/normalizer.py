"""
Protocol Normalizer and Interoperability Validator.
Ensures semantic consistency, unit standardization, schema version compatibility,
and robust handling of malformed or missing telemetry.
"""

from typing import Dict, Any, List, Tuple, Optional
import csv
import io
import json
from datetime import datetime, timezone
from pydantic import ValidationError

from app.protocol.schema import (
    AgentMessage,
    TelemetryRecord,
    MessageType,
    CURRENT_SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
)


class ProtocolError(Exception):
    """Base exception for protocol interoperability issues."""
    pass


class SchemaVersionMismatchError(ProtocolError):
    """Raised when an incompatible schema version is encountered."""
    def __init__(self, version: str, supported: set):
        super().__init__(f"Incompatible schema_version '{version}'. Supported versions are: {sorted(list(supported))}")
        self.version = version
        self.supported = supported


class MalformedDataError(ProtocolError):
    """Raised when payload contains logically invalid or unparseable data."""
    def __init__(self, details: List[str]):
        super().__init__(f"Malformed data detected: {'; '.join(details)}")
        self.details = details


class MissingFieldError(ProtocolError):
    """Raised when required diagnostic or telemetry fields are absent."""
    def __init__(self, missing_fields: List[str], context: str = ""):
        super().__init__(f"Missing required field(s) in {context}: {', '.join(missing_fields)}")
        self.missing_fields = missing_fields


class TelemetryNormalizer:
    """
    Standardizes units, resolves incompatible field aliases, and validates telemetry records.
    Canonical standard units:
      - Latency & Jitter: milliseconds (ms)
      - Throughput & Bandwidth: megabits per second (Mbps)
      - Loss & Utilization & CPU & Memory: percentage (%)
      - Wi-Fi RSSI: decibel-milliwatts (dBm)
      - Wi-Fi SNR: decibels (dB)
    """

    # Field aliases mapping non-canonical or vendor-specific telemetry keys to canonical schema
    FIELD_ALIASES = {
        "cpu": "cpu_utilization_pct",
        "cpu_pct": "cpu_utilization_pct",
        "cpu_util": "cpu_utilization_pct",
        "cpu_usage": "cpu_utilization_pct",
        "cpu_utilization": "cpu_utilization_pct",
        "processor_utilization": "cpu_utilization_pct",
        "memory": "memory_utilization_pct",
        "mem": "memory_utilization_pct",
        "ram": "memory_utilization_pct",
        "memory_pct": "memory_utilization_pct",
        "mem_pct": "memory_utilization_pct",
        "ram_pct": "memory_utilization_pct",
        "memory_util": "memory_utilization_pct",
        "loss": "packet_loss_pct",
        "packet_loss": "packet_loss_pct",
        "loss_pct": "packet_loss_pct",
        "latency": "latency_ms",
        "rtt": "latency_ms",
        "delay": "latency_ms",
        "ping_ms": "latency_ms",
        "round_trip_time_ms": "latency_ms",
        "jitter": "jitter_ms",
        "throughput": "throughput_mbps",
        "bitrate": "throughput_mbps",
        "bandwidth": "bandwidth_mbps",
        "link_speed": "bandwidth_mbps",
        "utilization": "utilization_pct",
        "link_utilization": "utilization_pct",
        "link_utilization_pct": "utilization_pct",
        "queue_drops": "queue_drops_per_sec",
        "buffer_drops": "queue_drops_per_sec",
        "crc_errors": "interface_crc_errors",
        "interface_errors": "interface_crc_errors",
        "fcs_errors": "interface_crc_errors",
        "flaps": "interface_flaps",
        "rssi": "wifi_rssi_dbm",
        "signal_rssi": "wifi_rssi_dbm",
        "snr": "wifi_snr_db",
        "signal_snr": "wifi_snr_db",
        "retry_pct": "wifi_retry_pct",
        "retries": "wifi_retry_pct",
        "dns_latency": "dns_response_ms",
        "dns_ms": "dns_response_ms",
        "dhcp_latency": "dhcp_response_ms",
        "dhcp_ms": "dhcp_response_ms",
    }

    @staticmethod
    def extract_numeric_and_unit(val: Any) -> Tuple[Optional[float], Optional[str]]:
        """
        Safely extracts float value and optional embedded unit string.
        Handles values like '45.2 ms', '120 Mbps', '35%', '8.5 dBm', or numeric types.
        """
        if val is None or val == "":
            return None, None
        if isinstance(val, (int, float)):
            return float(val), None
        if isinstance(val, str):
            s = val.strip()
            # Try direct float conversion
            try:
                return float(s), None
            except ValueError:
                pass
            # Pattern match number + unit suffix
            import re
            m = re.match(r"^([-+]?[0-9]*\.?[0-9]+)\s*([a-zA-Z/%]*)$", s)
            if m:
                try:
                    num = float(m.group(1))
                    unit = m.group(2).strip() or None
                    return num, unit
                except ValueError:
                    pass
        return None, None

    @staticmethod
    def normalize_unit_value(value: Any, unit: Optional[str], metric_name: str) -> Tuple[Optional[float], str]:
        """
        Converts given value and unit into the canonical metric unit.
        Returns (normalized_value, canonical_unit).
        """
        if value is None:
            return None, ""

        try:
            val = float(value)
        except (ValueError, TypeError):
            raise MalformedDataError([f"Metric '{metric_name}' value '{value}' cannot be parsed as a float"])

        unit_str = (unit or "").strip().lower()

        # Latency / Jitter normalization -> canonical 'ms'
        if any(keyword in metric_name.lower() for keyword in ["latency", "jitter", "delay"]):
            if unit_str in ["s", "sec", "seconds"]:
                return round(val * 1000.0, 3), "ms"
            elif unit_str in ["us", "µs", "microseconds"]:
                return round(val / 1000.0, 3), "ms"
            elif unit_str in ["ns", "nanoseconds"]:
                return round(val / 1_000_000.0, 3), "ms"
            return round(val, 3), "ms"

        # Bandwidth / Throughput normalization -> canonical 'Mbps'
        if any(keyword in metric_name.lower() for keyword in ["throughput", "bandwidth", "bitrate"]):
            if unit_str in ["gbps", "gigabits/sec"]:
                return round(val * 1000.0, 2), "Mbps"
            elif unit_str in ["kbps", "kilobits/sec"]:
                return round(val / 1000.0, 3), "Mbps"
            elif unit_str in ["bps", "bits/sec"]:
                return round(val / 1_000_000.0, 4), "Mbps"
            elif unit_str in ["mb/s", "megabytes/sec"]:
                return round(val * 8.0, 2), "Mbps"
            elif unit_str in ["kb/s", "kilobytes/sec"]:
                return round(val * 8.0 / 1000.0, 3), "Mbps"
            elif unit_str in ["b/s", "bytes/sec"]:
                return round(val * 8.0 / 1_000_000.0, 4), "Mbps"
            return round(val, 2), "Mbps"

        # Percentage normalization (0.0 - 1.0 ratio -> 0 - 100 %)
        if any(keyword in metric_name.lower() for keyword in ["utilization", "loss", "pct", "cpu", "memory", "retry"]):
            if unit_str in ["ratio", "fraction"] or (unit_str == "" and 0.0 <= val <= 1.0 and "pct" in metric_name):
                return round(val * 100.0, 2), "%"
            return round(val, 2), "%"

        return round(val, 3), unit or ""

    @classmethod
    def validate_and_normalize_telemetry(cls, raw: Dict[str, Any]) -> TelemetryRecord:
        """
        Parses raw dictionary into a strictly validated TelemetryRecord,
        resolves field aliases, checks range invariants, and standardizes units.
        Seamlessly adapts official problem-statement generator payload if present.
        """
        flat = dict(raw)

        # 1. Adapt problem-statement structure (nested "metrics")
        if "metrics" in flat and isinstance(flat["metrics"], dict):
            m = flat.pop("metrics")
            for k, v in m.items():
                if k not in flat:
                    flat[k] = v
            if "status" in flat and "device_status" not in flat:
                status_map = {"Healthy": "UP", "Warning": "DEGRADED", "Critical": "DOWN"}
                flat["device_status"] = status_map.get(flat["status"], "UP")
            if "telemetry_origin" not in flat:
                flat["telemetry_origin"] = "GENERATED_TEST"

        # 2. Resolve field aliases
        normalized_data: Dict[str, Any] = {}
        for k, v in flat.items():
            canonical_key = cls.FIELD_ALIASES.get(k.strip().lower(), k.strip())
            # If not yet set or current value is None, assign
            if canonical_key not in normalized_data or normalized_data[canonical_key] is None:
                normalized_data[canonical_key] = v

        # 3. String numeric parsing and unit normalization for standard metrics
        numeric_metric_keys = [
            "latency_ms", "jitter_ms", "packet_loss_pct", "throughput_mbps", "bandwidth_mbps",
            "utilization_pct", "queue_drops_per_sec", "cpu_utilization_pct", "memory_utilization_pct",
            "wifi_rssi_dbm", "wifi_snr_db", "wifi_retry_pct", "dns_response_ms", "dhcp_response_ms",
        ]
        for key in numeric_metric_keys:
            if key in normalized_data and normalized_data[key] is not None:
                val = normalized_data[key]
                num_val, embedded_unit = cls.extract_numeric_and_unit(val)
                if num_val is not None:
                    # Normalize unit if specified
                    if embedded_unit:
                        norm_val, _ = cls.normalize_unit_value(num_val, embedded_unit, key)
                        normalized_data[key] = norm_val
                    else:
                        normalized_data[key] = num_val

        errors: List[str] = []

        if not normalized_data.get("device_id"):
            errors.append("device_id is required and cannot be empty")

        # Range checks for physical realism
        lat = normalized_data.get("latency_ms")
        if lat is not None:
            try:
                lat_f = float(lat)
                if lat_f < 0:
                    errors.append(f"latency_ms cannot be negative ({lat_f})")
            except (ValueError, TypeError):
                errors.append(f"Invalid latency_ms value '{lat}'")

        loss = normalized_data.get("packet_loss_pct")
        if loss is not None:
            try:
                loss_f = float(loss)
                if loss_f < 0 or loss_f > 100:
                    errors.append(f"packet_loss_pct must be between 0 and 100 ({loss_f})")
            except (ValueError, TypeError):
                errors.append(f"Invalid packet_loss_pct value '{loss}'")

        cpu = normalized_data.get("cpu_utilization_pct")
        if cpu is not None:
            try:
                cpu_f = float(cpu)
                if cpu_f < 0 or cpu_f > 100:
                    errors.append(f"cpu_utilization_pct must be between 0 and 100 ({cpu_f})")
            except (ValueError, TypeError):
                errors.append(f"Invalid cpu_utilization_pct value '{cpu}'")

        if errors:
            raise MalformedDataError(errors)

        try:
            return TelemetryRecord(**normalized_data)
        except ValidationError as e:
            err_msgs = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            raise MalformedDataError(err_msgs)

    @classmethod
    def parse_csv_telemetry(cls, csv_content: str) -> List[TelemetryRecord]:
        """
        Ingests CSV network telemetry strings and transforms to TelemetryRecord list.
        """
        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        records = []
        line_num = 1
        for row in reader:
            line_num += 1
            cleaned_row: Dict[str, Any] = {}
            for k, v in row.items():
                if v is None or v.strip() == "":
                    continue
                k_clean = k.strip()
                v_clean = v.strip()
                # Attempt float conversion
                try:
                    if "." in v_clean:
                        cleaned_row[k_clean] = float(v_clean)
                    else:
                        cleaned_row[k_clean] = int(v_clean)
                except ValueError:
                    cleaned_row[k_clean] = v_clean
            
            try:
                rec = cls.validate_and_normalize_telemetry(cleaned_row)
                records.append(rec)
            except ProtocolError as pe:
                raise MalformedDataError([f"Line {line_num}: {str(pe)}"])

        return records

    @classmethod
    def parse_json_telemetry(cls, json_content: str) -> List[TelemetryRecord]:
        """
        Ingests JSON array or object telemetry string.
        """
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as jde:
            raise MalformedDataError([f"Invalid JSON syntax: {str(jde)}"])

        if isinstance(data, dict):
            # Check if wrapped in telemetry key or single record
            if "telemetry" in data and isinstance(data["telemetry"], list):
                items = data["telemetry"]
            else:
                items = [data]
        elif isinstance(data, list):
            items = data
        else:
            raise MalformedDataError(["Root JSON must be an object or array"])

        records = []
        for idx, item in enumerate(items):
            try:
                records.append(cls.validate_and_normalize_telemetry(item))
            except ProtocolError as pe:
                raise MalformedDataError([f"Record {idx}: {str(pe)}"])

        return records


class InteroperabilityValidator:
    """
    Validates inter-agent message compliance with canonical protocol.
    Enforces schema version matching, required fields, and semantic consistency.
    """

    @classmethod
    def validate_message(cls, msg_dict: Dict[str, Any]) -> AgentMessage:
        """
        Validates an incoming agent message dict.
        Raises SchemaVersionMismatchError or MalformedDataError if non-compliant.
        """
        version = msg_dict.get("schema_version")
        if not version:
            raise MissingFieldError(["schema_version"], context="AgentMessage")

        if version not in SUPPORTED_SCHEMA_VERSIONS:
            raise SchemaVersionMismatchError(str(version), SUPPORTED_SCHEMA_VERSIONS)

        # Check required fields
        required_fields = ["agent_id", "message_type"]
        missing = [f for f in required_fields if not msg_dict.get(f)]
        if missing:
            raise MissingFieldError(missing, context="AgentMessage")

        try:
            return AgentMessage(**msg_dict)
        except ValidationError as ve:
            details = [f"{err['loc']}: {err['msg']}" for err in ve.errors()]
            raise MalformedDataError(details)

    @classmethod
    def create_error_message(
        cls,
        origin_agent: str,
        target_agent: Optional[str],
        error_type: MessageType,
        error_details: str,
        correlation_id: Optional[str] = None
    ) -> AgentMessage:
        """
        Constructs an explicit protocol error message instead of failing silently.
        """
        return AgentMessage(
            agent_id=origin_agent,
            target_agent_id=target_agent,
            message_type=error_type,
            schema_version=CURRENT_SCHEMA_VERSION,
            confidence=1.0,
            evidence={"error": error_details, "timestamp": datetime.now(timezone.utc).isoformat()},
            findings=[f"Protocol interoperability failure: {error_details}"],
            correlation_id=correlation_id
        )
