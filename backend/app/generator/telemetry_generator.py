"""
Official Telemetry Generator & Canonical Protocol Adapter.
Integrates the exact problem-statement generator and normalizes records for multi-agent diagnosis.
"""

import json
import random
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List

from app.protocol.schema import TelemetryRecord


# =====================================================================
# 1. REQUIRED OFFICIAL TELEMETRY GENERATOR (Problem Statement Specification)
# =====================================================================

def generate_telemetry(fault_type="normal"):
    timestamp = datetime.now(timezone.utc).isoformat()
    device_id = f"SW_CAMPUS_{random.randint(1, 10)}"

    if fault_type == "latency_spike":
        metrics = {
            "cpu_utilization": round(random.uniform(40, 70), 2),
            "link_utilization_pct": round(random.uniform(60, 85), 2),
            "packet_loss_pct": round(random.uniform(0.1, 1.5), 2),
            "latency_ms": round(random.uniform(150, 400), 2),
            "jitter_ms": round(random.uniform(30, 80), 2),
            "queue_drops": random.randint(0, 50)
        }
        status = "Warning"

    elif fault_type == "hardware_failure":
        metrics = {
            "cpu_utilization": 99.9,
            "link_utilization_pct": 100,
            "packet_loss_pct": round(random.uniform(15, 30), 2),
            "latency_ms": round(random.uniform(500, 1000), 2),
            "queue_drops": random.randint(5000, 15000),
            "interface_errors": random.randint(100, 500)
        }
        status = "Critical"

    else:
        metrics = {
            "cpu_utilization": round(random.uniform(10, 35), 2),
            "link_utilization_pct": round(random.uniform(20, 50), 2),
            "packet_loss_pct": 0.0,
            "latency_ms": round(random.uniform(5, 20), 2),
            "jitter_ms": round(random.uniform(1, 5), 2),
            "queue_drops": 0
        }
        status = "Healthy"

    return {
        "device_id": device_id,
        "timestamp": timestamp,
        "metrics": metrics,
        "status": status
    }


# =====================================================================
# 2. VALIDATION & ADAPTER TO CANONICAL INTEROPERABILITY PROTOCOL
# =====================================================================

VALID_FAULT_TYPES = {"normal", "latency_spike", "hardware_failure"}


def validate_generated_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates that a telemetry dictionary strictly conforms to the generator specification.
    """
    if not isinstance(data, dict):
        return False, "Payload must be a JSON object"

    if "timestamp" not in data or not isinstance(data["timestamp"], str):
        return False, "Missing or invalid 'timestamp' field"

    if "device_id" not in data or not isinstance(data["device_id"], str):
        return False, "Missing or invalid 'device_id' field"

    if not data["device_id"].startswith("SW_CAMPUS_"):
        return False, f"Invalid device_id '{data['device_id']}', expected prefix 'SW_CAMPUS_'"

    if "status" not in data or not isinstance(data.get("status"), str):
        return False, "Missing required root key 'status'"

    if data["status"] not in ("Healthy", "Warning", "Critical"):
        return False, f"Invalid 'status' field: {data.get('status')}"

    if "metrics" not in data or not isinstance(data["metrics"], dict):
        return False, "Missing or invalid 'metrics' dictionary"

    metrics = data["metrics"]
    
    cpu_val = metrics.get("cpu_utilization", metrics.get("cpu_utilization_pct"))
    if cpu_val is None or not isinstance(cpu_val, (int, float)):
        return False, "Missing metric 'cpu_utilization' or non-numeric value"

    required_metrics = ["link_utilization_pct", "packet_loss_pct", "latency_ms", "queue_drops"]
    for m in required_metrics:
        if m not in metrics or not isinstance(metrics[m], (int, float)):
            return False, f"Missing metric '{m}' or non-numeric value in metrics dictionary"

    # Range validations
    if not (0.0 <= cpu_val <= 100.0):
        return False, f"cpu_utilization out of bounds: {cpu_val}"

    if not (0.0 <= metrics["link_utilization_pct"] <= 100.0):
        return False, f"link_utilization_pct out of bounds: {metrics['link_utilization_pct']}"

    if not (0.0 <= metrics["packet_loss_pct"] <= 100.0):
        return False, f"packet_loss_pct out of bounds: {metrics['packet_loss_pct']}"

    if metrics["latency_ms"] < 0:
        return False, f"latency_ms cannot be negative: {metrics['latency_ms']}"

    if metrics["queue_drops"] < 0:
        return False, f"queue_drops cannot be negative: {metrics['queue_drops']}"

    return True, None


def adapt_to_canonical_record(data: Dict[str, Any], fault_type: Optional[str] = None) -> TelemetryRecord:
    """
    Transforms the official problem-statement telemetry payload into a Canonical TelemetryRecord.
    Strictly tags the record with telemetry_origin='GENERATED_TEST' to preserve provenance.
    Preserves original raw data inside custom_metrics for transparency.
    """
    valid, err = validate_generated_payload(data)
    if not valid:
        raise ValueError(f"Invalid problem statement telemetry: {err}")

    metrics = data["metrics"]
    status_str = data.get("status", "Healthy")

    # Map status string to canonical device status
    device_status_map = {
        "Healthy": "UP",
        "Warning": "DEGRADED",
        "Critical": "DOWN",
    }
    canonical_status = device_status_map.get(status_str, "UP")

    cpu_val = float(metrics.get("cpu_utilization", metrics.get("cpu_utilization_pct", 0.0)))
    jitter_val = float(metrics["jitter_ms"]) if "jitter_ms" in metrics and metrics["jitter_ms"] is not None else None
    crc_val = int(metrics.get("interface_errors", 0))

    record = TelemetryRecord(
        timestamp=data.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        device_id=data["device_id"],
        device_type="switch",
        device_status=canonical_status,
        latency_ms=float(metrics["latency_ms"]),
        jitter_ms=jitter_val,
        packet_loss_pct=float(metrics["packet_loss_pct"]),
        utilization_pct=float(metrics["link_utilization_pct"]),
        queue_drops_per_sec=float(metrics["queue_drops"]),
        cpu_utilization_pct=cpu_val,
        interface_crc_errors=crc_val,
        telemetry_origin="GENERATED_TEST",
        custom_metrics={
            "official_status": status_str,
            "fault_type_requested": fault_type,
            "raw_payload": data,
        },
    )
    return record
