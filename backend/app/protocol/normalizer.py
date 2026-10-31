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
    Standardizes units and validates telemetry records.
    Canonical standard units:
      - Latency & Jitter: milliseconds (ms)
      - Throughput & Bandwidth: megabits per second (Mbps)
      - Loss & Utilization & CPU & Memory: percentage (%)
      - Wi-Fi RSSI: decibel-milliwatts (dBm)
      - Wi-Fi SNR: decibels (dB)
    """

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
        checking for required fields, range invariants, and standardizing units.
        Seamlessly adapts official problem-statement generator payload if present.
        """
        # Adapt problem-statement structure (nested "metrics")
        if "metrics" in raw and isinstance(raw["metrics"], dict):
            flat = dict(raw)
            m = flat.pop("metrics")
            for k, v in m.items():
                if k not in flat:
                    flat[k] = v
            if "cpu_utilization" in flat and "cpu_utilization_pct" not in flat:
                flat["cpu_utilization_pct"] = flat["cpu_utilization"]
            if "status" in flat and "device_status" not in flat:
                status_map = {"Healthy": "UP", "Warning": "DEGRADED", "Critical": "DOWN"}
                flat["device_status"] = status_map.get(flat["status"], "UP")
            if "link_utilization_pct" in flat and "utilization_pct" not in flat:
                flat["utilization_pct"] = flat["link_utilization_pct"]
            if "queue_drops" in flat and "queue_drops_per_sec" not in flat:
                flat["queue_drops_per_sec"] = float(flat["queue_drops"])
            if "interface_errors" in flat and "interface_crc_errors" not in flat:
                flat["interface_crc_errors"] = int(flat["interface_errors"])
            if "telemetry_origin" not in flat:
                flat["telemetry_origin"] = "GENERATED_TEST"
            raw = flat

        errors: List[str] = []

        if not raw.get("device_id"):
            errors.append("device_id is required and cannot be empty")

        # Range checks for physical realism
        lat = raw.get("latency_ms")
        if lat is not None:
            try:
                lat_f = float(lat)
                if lat_f < 0:
                    errors.append(f"latency_ms cannot be negative ({lat_f})")
            except (ValueError, TypeError):
                errors.append(f"Invalid latency_ms value '{lat}'")

        loss = raw.get("packet_loss_pct")
        if loss is not None:
            try:
                loss_f = float(loss)
                if loss_f < 0 or loss_f > 100:
                    errors.append(f"packet_loss_pct must be between 0 and 100 ({loss_f})")
            except (ValueError, TypeError):
                errors.append(f"Invalid packet_loss_pct value '{loss}'")

        cpu = raw.get("cpu_utilization_pct")
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
            return TelemetryRecord(**raw)
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
