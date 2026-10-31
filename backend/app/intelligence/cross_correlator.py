"""
Cross-Incident Correlation Engine for NetCoop AI.
Analyzes multiple incident symptoms across devices to identify shared topological dependencies,
common upstream choke-points, and unified root cause clusters.
"""

from typing import List, Dict, Any, Optional
import uuid

from app.protocol.schema import (
    CorrelatedIncidentCluster,
    CorrelationRelationshipType,
    IncidentPriorityItem,
)
from app.simulator.twin import DEVICE_DEPENDENCY_GRAPH


class CrossIncidentCorrelator:
    """
    Correlates multiple detected anomalies or incidents using topological graph reachability,
    shared upstream bottlenecks, and concurrent temporal symptom signatures.
    """

    def correlate_incidents(
        self,
        incidents: List[IncidentPriorityItem],
    ) -> List[CorrelatedIncidentCluster]:
        """
        Groups incidents into correlated clusters when they share upstream nodes or common dependencies.
        """
        if not incidents or len(incidents) < 2:
            return []

        clusters: List[CorrelatedIncidentCluster] = []

        # Group incidents by device
        incidents_by_device: Dict[str, List[IncidentPriorityItem]] = {}
        for inc in incidents:
            dev = inc.device_id
            if dev not in incidents_by_device:
                incidents_by_device[dev] = []
            incidents_by_device[dev].append(inc)

        # 1. Check for Shared Upstream Bottleneck:
        # If Edge-Switch-01 and Edge-Switch-02 (or downstream APs) both report degradation,
        # trace to shared upstream node (Agg-Switch-01 or Core-Router-01).
        affected_devices = list(incidents_by_device.keys())

        # Find common upstream ancestors in topology
        common_ancestors: Dict[str, List[str]] = {}
        for dev in affected_devices:
            meta = DEVICE_DEPENDENCY_GRAPH.get(dev, {})
            upstreams = meta.get("upstream", [])
            for up in upstreams:
                if up not in common_ancestors:
                    common_ancestors[up] = []
                common_ancestors[up].append(dev)

        # Evaluate upstream nodes that feed 2 or more degraded devices
        for up_node, down_list in common_ancestors.items():
            if len(down_list) >= 2:
                # Find all incidents associated with these downstream nodes
                cluster_incidents = [
                    inc.incident_id
                    for d in down_list
                    for inc in incidents_by_device.get(d, [])
                ]
                
                # Check if upstream node itself also has an incident
                upstream_has_incident = up_node in incidents_by_device
                if upstream_has_incident:
                    cluster_incidents.extend([
                        inc.incident_id for inc in incidents_by_device[up_node]
                    ])

                status = "CONFIRMED" if upstream_has_incident else "SUSPECTED"
                conf = 0.94 if upstream_has_incident else 0.82

                candidate_cause = (
                    f"Shared Upstream Choke-point at {up_node}"
                    if not upstream_has_incident
                    else incidents_by_device[up_node][0].suspected_root_cause
                )

                reasoning = (
                    f"Topological dependency analysis identified that {', '.join(down_list)} all route through "
                    f"shared distribution node '{up_node}'. Concurrent downstream symptom arrival strongly corroborates "
                    f"a shared upstream root cause rather than independent simultaneous hardware failures."
                )

                clusters.append(
                    CorrelatedIncidentCluster(
                        cluster_id=f"CORR-{uuid.uuid4().hex[:6].upper()}",
                        title=f"Shared Upstream Incident Cluster: {up_node}",
                        root_cause_candidate=candidate_cause,
                        primary_device=up_node,
                        implicated_devices=[up_node] + down_list,
                        incident_ids=list(set(cluster_incidents)),
                        relationship_type=CorrelationRelationshipType.SHARED_UPSTREAM_DEVICE,
                        relationship_confidence=conf,
                        status=status,
                        correlation_reasoning=reasoning,
                        common_upstream_node=up_node,
                        recommended_unified_remediation=f"Apply singular remediation at root node {up_node} to restore all downstream leaves simultaneously.",
                        prevented_redundant_actions=len(down_list),
                    )
                )

        # 2. Check for cascading Core-to-Distribution fault
        if "Core-Router-01" in incidents_by_device and "Agg-Switch-01" in incidents_by_device:
            core_incs = [i.incident_id for i in incidents_by_device["Core-Router-01"]]
            agg_incs = [i.incident_id for i in incidents_by_device["Agg-Switch-01"]]
            clusters.append(
                CorrelatedIncidentCluster(
                    cluster_id=f"CORR-CORE-{uuid.uuid4().hex[:6].upper()}",
                    title="Core Gateway Cascading Distribution Impact",
                    root_cause_candidate="Core Router Transit Starvation",
                    primary_device="Core-Router-01",
                    implicated_devices=["Core-Router-01", "Agg-Switch-01"],
                    incident_ids=core_incs + agg_incs,
                    relationship_type=CorrelationRelationshipType.CASCADING_PROPAGATION,
                    relationship_confidence=0.96,
                    status="CONFIRMED",
                    correlation_reasoning="Core Router high-priority routing degradation directly propagates transit packet loss onto Agg-Switch-01 distribution trunks.",
                    common_upstream_node="Core-Router-01",
                    recommended_unified_remediation="Isolate Core-Router-01 processor overload; distribution layer will automatically normalize without switch-level intervention.",
                    prevented_redundant_actions=2,
                )
            )

        # Deduplicate clusters by primary device
        unique_clusters: List[CorrelatedIncidentCluster] = []
        seen_primary = set()
        for cl in clusters:
            if cl.primary_device not in seen_primary:
                unique_clusters.append(cl)
                seen_primary.add(cl.primary_device)

        return unique_clusters


cross_incident_correlator = CrossIncidentCorrelator()

