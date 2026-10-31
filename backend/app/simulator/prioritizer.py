"""
Incident Prioritization Engine for NetCoop AI.
Ranks detected network incidents by operational priority using deterministic multi-factor scoring:
Severity (40%), SLA Breach (25%), Downstream Topological Impact (15%), Confidence (10%), Propagation Risk (10%).
"""

from typing import List, Dict, Any, Optional
from app.protocol.schema import (
    IncidentPriority,
    IncidentPriorityItem,
    DigitalTwinSnapshot,
)
from app.simulator.twin import DEVICE_DEPENDENCY_GRAPH, digital_twin_engine


def calculate_priority_score(
    severity: str,
    sla_breached: bool,
    affected_count: int,
    confidence: float,
    propagation_risk: str,
) -> float:
    score = 0.0

    # Severity factor (max 40 pts)
    sev_upper = severity.upper()
    if "CRITICAL" in sev_upper or "HIGH" in sev_upper:
        score += 40.0
    elif "WARNING" in sev_upper or "MEDIUM" in sev_upper:
        score += 25.0
    else:
        score += 10.0

    # SLA breach factor (max 25 pts)
    if sla_breached:
        score += 25.0

    # Affected devices / topological blast radius (max 15 pts)
    # 1 device = 5 pts, 2 devices = 10 pts, >= 3 devices = 15 pts
    if affected_count >= 3:
        score += 15.0
    elif affected_count == 2:
        score += 10.0
    elif affected_count == 1:
        score += 5.0

    # Confidence factor (max 10 pts)
    score += min(10.0, round(confidence * 10.0, 1))

    # Propagation risk factor (max 10 pts)
    prop_upper = propagation_risk.upper()
    if prop_upper == "HIGH":
        score += 10.0
    elif prop_upper == "MEDIUM":
        score += 5.0
    else:
        score += 2.0

    return min(100.0, round(score, 1))


class IncidentPrioritizer:
    """
    Ranks active incidents deterministically for NOC operational dispatch.
    """

    def prioritize_incidents(
        self,
        active_incident: Optional[Dict[str, Any]] = None,
        twin_snapshot: Optional[DigitalTwinSnapshot] = None,
    ) -> List[IncidentPriorityItem]:
        """
        Produces a sorted list of prioritized incidents (P1 -> P4).
        """
        snapshot = twin_snapshot or digital_twin_engine.get_cached_or_default()
        items: List[IncidentPriorityItem] = []

        # If there's an active diagnosed incident from the main orchestrator, incorporate it with priority
        if active_incident:
            inc_id = active_incident.get("incident_id", "INC-CURRENT")
            dev_id = active_incident.get("device_id", "Core-Router-01")
            root_cause = active_incident.get("suspected_root_cause", "Network Incident")
            conf = float(active_incident.get("confidence", 0.90))
            affected = active_incident.get("affected_devices", [dev_id])
            sla_breached = True

            sev = "CRITICAL" if ("CPU" in root_cause or "Congestion" in root_cause or "Starvation" in root_cause) else "WARNING"
            prop = "HIGH" if dev_id in ["Core-Router-01", "Agg-Switch-01"] else "LOW"

            score = calculate_priority_score(
                severity=sev,
                sla_breached=sla_breached,
                affected_count=len(affected),
                confidence=conf,
                propagation_risk=prop,
            )

            p_level = IncidentPriority.P1 if score >= 80.0 else (
                IncidentPriority.P2 if score >= 65.0 else (
                    IncidentPriority.P3 if score >= 45.0 else IncidentPriority.P4
                )
            )

            rec_action = "Execute CoPP rate-limiting & punt traffic filtering" if "CPU" in root_cause else (
                "Apply WRED queue shaping & ECMP trunk deflection" if "Congestion" in root_cause else "Perform targeted agent diagnostic review"
            )

            items.append(
                IncidentPriorityItem(
                    incident_id=inc_id,
                    device_id=dev_id,
                    title=f"Active Incident: {root_cause}",
                    severity=sev,
                    priority=p_level,
                    priority_score=score,
                    sla_breached=sla_breached,
                    affected_devices_count=len(affected),
                    affected_devices=affected,
                    service_impact="Transit packet loss and latency elevation across downstream distribution and access switches",
                    confidence=conf,
                    propagation_risk=prop,
                    suspected_root_cause=root_cause,
                    recommended_action=rec_action,
                    status="OPEN",
                )
            )

        # Standard benchmark incidents representing wider network status
        standard_benchmarks = [
            {
                "incident_id": "INC-7021",
                "device_id": "Core-Router-01",
                "title": "Control Plane CPU Starvation on Core Gateway",
                "severity": "CRITICAL",
                "sla_breached": True,
                "affected": ["Core-Router-01", "Agg-Switch-01", "Edge-Switch-01"],
                "impact": "Degrades BGP protocol timers and causes packet drops across enterprise gateway",
                "confidence": 0.92,
                "propagation": "HIGH",
                "root_cause": "Control Plane Processor Saturation",
                "action": "Deploy CoPP hardware policing on GigabitEthernet0/0/0",
            },
            {
                "incident_id": "INC-6044",
                "device_id": "Agg-Switch-01",
                "title": "Interface CRC Discard Rate on Trunk ge-0/0/1",
                "severity": "WARNING",
                "sla_breached": True,
                "affected": ["Agg-Switch-01", "Edge-Switch-01"],
                "impact": "450 frame corruptions/sec triggering TCP window shrinkage",
                "confidence": 0.88,
                "propagation": "MEDIUM",
                "root_cause": "Degraded SFP+ Transceiver Optics / Cable Fault",
                "action": "Evict degraded port from LACP bundle and soft reset DDM optics",
            },
            {
                "incident_id": "INC-5188",
                "device_id": "DNS-Server-01",
                "title": "DNS Lookup Latency Spike (2800ms) & DHCP Pool Exhaustion",
                "severity": "WARNING",
                "sla_breached": True,
                "affected": ["DNS-Server-01"],
                "impact": "Slow client hostname lookups and IP lease acquisition delays",
                "confidence": 0.85,
                "propagation": "LOW",
                "root_cause": "Core Infrastructure Server Thread Deadlock",
                "action": "Restart named/kea daemons and flush resolver cache",
            },
            {
                "incident_id": "INC-4920",
                "device_id": "AP-02",
                "title": "802.11 RF Signal Attenuation (-86 dBm RSSI)",
                "severity": "WARNING",
                "sla_breached": True,
                "affected": ["AP-02"],
                "impact": "Excessive 802.11 retries (42%) and throughput drop for wireless clients",
                "confidence": 0.82,
                "propagation": "LOW",
                "root_cause": "Weak Wireless RF Coverage / Co-Channel Interference",
                "action": "Boost 5GHz radio transmit power to 20 dBm and change channel to 149",
            },
        ]

        seen_ids = {item.incident_id for item in items}

        for bench in standard_benchmarks:
            if bench["incident_id"] not in seen_ids:
                sc = calculate_priority_score(
                    severity=bench["severity"],
                    sla_breached=bench["sla_breached"],
                    affected_count=len(bench["affected"]),
                    confidence=bench["confidence"],
                    propagation_risk=bench["propagation"],
                )
                pl = IncidentPriority.P1 if sc >= 80.0 else (
                    IncidentPriority.P2 if sc >= 65.0 else (
                        IncidentPriority.P3 if sc >= 45.0 else IncidentPriority.P4
                    )
                )

                items.append(
                    IncidentPriorityItem(
                        incident_id=bench["incident_id"],
                        device_id=bench["device_id"],
                        title=bench["title"],
                        severity=bench["severity"],
                        priority=pl,
                        priority_score=sc,
                        sla_breached=bench["sla_breached"],
                        affected_devices_count=len(bench["affected"]),
                        affected_devices=bench["affected"],
                        service_impact=bench["impact"],
                        confidence=bench["confidence"],
                        propagation_risk=bench["propagation"],
                        suspected_root_cause=bench["root_cause"],
                        recommended_action=bench["action"],
                        status="OPEN",
                    )
                )

        # Sort descending by priority score
        items.sort(key=lambda x: x.priority_score, reverse=True)
        return items


incident_prioritizer = IncidentPrioritizer()
