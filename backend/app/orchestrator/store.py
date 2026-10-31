"""
Investigation Store for NetCoop AI.
Provides lightweight persistence for past autonomous investigation sessions,
allowing instant replay and inspection of event streams.
"""

from typing import Dict, Any, List, Optional
import os
import json
from datetime import datetime, timezone

_env_data_dir = os.environ.get("NETCOOP_DATA_DIR")
DATA_DIR = _env_data_dir if _env_data_dir else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
STORAGE_FILE = os.path.join(DATA_DIR, "investigations.json")


class InvestigationStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InvestigationStore, cls).__new__(cls)
            cls._instance._investigations = {}
            cls._instance._init_storage()
        return cls._instance

    def _init_storage(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._investigations = data
            except Exception as e:
                print(f"[InvestigationStore] Warning loading storage: {e}")
                self._investigations = {}
        else:
            self._investigations = {}

    def _persist(self):
        try:
            with open(STORAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._investigations, f, indent=2)
        except Exception as e:
            print(f"[InvestigationStore] Warning persisting storage: {e}")

    def save_investigation(self, record: Dict[str, Any]):
        incident_id = record.get("incident_id") or record.get("investigation_id")
        if not incident_id:
            return
        self._investigations[incident_id] = record
        self._persist()

    def get_investigation(self, incident_id: str) -> Optional[Dict[str, Any]]:
        return self._investigations.get(incident_id)

    def list_investigations(self) -> List[Dict[str, Any]]:
        summaries = []
        for inc_id, rec in self._investigations.items():
            report = rec.get("canonical_report", {})
            timeline = rec.get("timeline_events", [])
            summaries.append({
                "incident_id": inc_id,
                "investigation_id": rec.get("investigation_id", inc_id),
                "timestamp": rec.get("timestamp") or report.get("timestamp"),
                "scenario_id": rec.get("scenario_id", "custom"),
                "status": rec.get("status") or report.get("status"),
                "suspected_root_cause": rec.get("suspected_root_cause") or report.get("suspected_root_cause"),
                "confidence": rec.get("confidence") or report.get("confidence"),
                "affected_devices": rec.get("affected_devices", []),
                "event_count": len(timeline),
                "execution_time_ms": rec.get("execution_time_ms", 0),
            })
        # Sort newest first
        summaries.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
        return summaries


investigation_store = InvestigationStore()

