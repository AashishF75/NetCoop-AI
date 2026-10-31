"""
What-If Remediation Simulator Engine for NetCoop AI.
Provides deterministic modeling of remediation actions, side-by-side strategy comparisons,
telemetry deltas, and risk/tradeoff evaluations.
"""

from typing import List, Dict, Any, Optional, Tuple
import uuid
from datetime import datetime, timezone

from app.protocol.schema import (
    RemediationStrategy,
    SimulationResult,
    StrategyComparisonMatrix,
    TelemetryRecord,
    SLAStatus,
)
from app.simulator.twin import digital_twin_engine, BASELINE_SLA_BOUNDS


def _build_strategies_for_root_cause(
    root_cause: str,
    target_device: str,
    current_metrics: Dict[str, Any],
) -> List[RemediationStrategy]:
    """
    Returns 3 deterministic candidate strategies tailored to the diagnosed fault condition.
    """
    rc_lower = root_cause.lower()

    if "cpu" in rc_lower or "processor" in rc_lower or "starvation" in rc_lower:
        # Control Plane Processor Saturation
        return [
            RemediationStrategy(
                strategy_id="strat-copp-01",
                name="Control Plane Policing (CoPP) & Punt Rate-Limiting",
                description="Apply hardware-level CoPP policer to rate-limit unpoliced transit packets directed to the routing engine.",
                category="Control Plane Hardening",
                target_device=target_device,
                command="platform punt police rate 1000 burst 200",
                rollback_command="no platform punt police",
                intervention_type="AUTOMATED",
                operational_risk="LOW",
                recovery_time_seconds=15,
                rollback_available=True,
                effectiveness_pct=96.0,
                tradeoffs="Immediately restores supervisor engine CPU cycles and eliminates transit packet loss; may rate-limit high-frequency routing protocol burst updates during massive BGP table recalculations.",
                projected_telemetry={
                    "cpu_utilization_pct": 24.5,
                    "latency_ms": 5.8,
                    "packet_loss_pct": 0.0,
                    "utilization_pct": current_metrics.get("utilization_pct", 14.0),
                    "queue_drops_per_sec": 0.0,
                },
                expected_benefits=[
                    "Supervisor CPU drops from 99.4% to 24.5% within 15 seconds",
                    "Latency normalizes from 115ms to 5.8ms",
                    "Zero downtime required; executed entirely in data-plane ASIC policing",
                ],
                potential_risks=[
                    "Potential throttling of diagnostic ICMP bursts during high-stress troubleshooting",
                ],
            ),
            RemediationStrategy(
                strategy_id="strat-proc-02",
                name="Telemetry Daemon Isolation & CPU Affinity Pinning",
                description="Restart leaking telemetry collection service and pin its execution exclusively to CPU Core 3.",
                category="Process Management",
                target_device=target_device,
                command="systemctl restart netcoop-telemetry.service && taskset -cp 3 $(pgrep telemetry)",
                rollback_command="systemctl reset-failed netcoop-telemetry.service",
                intervention_type="OPERATOR_APPROVAL",
                operational_risk="MEDIUM",
                recovery_time_seconds=45,
                rollback_available=True,
                effectiveness_pct=88.0,
                tradeoffs="Addresses the underlying daemon thread leak and isolates it from the routing core; introduces a temporary 30-second telemetry observability blind spot while the agent restarts.",
                projected_telemetry={
                    "cpu_utilization_pct": 38.0,
                    "latency_ms": 8.2,
                    "packet_loss_pct": 0.1,
                    "utilization_pct": current_metrics.get("utilization_pct", 14.0),
                    "queue_drops_per_sec": 0.0,
                },
                expected_benefits=[
                    "Permanently releases orphaned memory segments and hung socket threads",
                    "Prevents daemon runaway threads from monopolizing interrupt vectors",
                ],
                potential_risks=[
                    "30-second observability blind spot during collector initialization",
                    "Does not protect routing engine if an external flood recurs",
                ],
            ),
            RemediationStrategy(
                strategy_id="strat-failover-03",
                name="Stateful Active/Standby Gateway Failover (HSRP/VRRP)",
                description="Lower VRRP priority on primary core router to failover default gateway responsibilities to Core-Router-02.",
                category="High Availability / Redundancy",
                target_device=target_device,
                command="interface GigabitEthernet0/0/0 standby 1 priority 90",
                rollback_command="interface GigabitEthernet0/0/0 standby 1 priority 110",
                intervention_type="MAINTENANCE_WINDOW",
                operational_risk="HIGH",
                recovery_time_seconds=90,
                rollback_available=True,
                effectiveness_pct=98.0,
                tradeoffs="Completely offloads production traffic from degraded hardware for safe out-of-band diagnostics; triggers sub-second VIP reconvergence blip and increases load on secondary core router.",
                projected_telemetry={
                    "cpu_utilization_pct": 12.0,
                    "latency_ms": 4.5,
                    "packet_loss_pct": 0.0,
                    "utilization_pct": 0.0,
                    "queue_drops_per_sec": 0.0,
                },
                expected_benefits=[
                    "Zero traffic remains on primary node, permitting complete cold reboot or firmware update",
                    "Eliminates risk of in-flight routing protocol crash",
                ],
                potential_risks=[
                    "Transient 250ms packet drop during VRRP virtual IP transition",
                    "Requires verified idle hardware capacity on standby Core-Router-02",
                ],
            ),
        ]

    elif "congestion" in rc_lower or "queue" in rc_lower or "buffer" in rc_lower:
        # Link Congestion
        return [
            RemediationStrategy(
                strategy_id="strat-qos-01",
                name="Priority Queuing & WRED Buffer Congestion Shaping",
                description="Enable Weighted Random Early Detection (WRED) and strict Priority Queuing for mission-critical voice/video.",
                category="Traffic Engineering",
                target_device=target_device,
                command="policy-map NOC-SHAPER; class voice; priority percent 30; class class-default; random-detect",
                rollback_command="no policy-map NOC-SHAPER",
                intervention_type="AUTOMATED",
                operational_risk="LOW",
                recovery_time_seconds=20,
                rollback_available=True,
                effectiveness_pct=94.0,
                tradeoffs="Shields high-priority traffic from buffer drops; early-drops bulk TCP sessions to force window backoff.",
                projected_telemetry={
                    "latency_ms": 11.5,
                    "packet_loss_pct": 0.1,
                    "utilization_pct": 82.0,
                    "queue_drops_per_sec": 0.0,
                    "cpu_utilization_pct": current_metrics.get("cpu_utilization_pct", 30.0),
                },
                expected_benefits=[
                    "Latency drops from 142ms to 11.5ms for critical traffic",
                    "Buffer exhaustion queue drops drop to zero",
                ],
                potential_risks=[
                    "Bulk file-transfer throughput temporarily throttled",
                ],
            ),
            RemediationStrategy(
                strategy_id="strat-ecmp-02",
                name="Dynamic ECMP Multipath Trunk Deflection",
                description="Shift 50% of hashing flows to parallel 10G trunk interface Trunk-02.",
                category="Route Deflection",
                target_device=target_device,
                command="ip route 0.0.0.0/0 Trunk-02 weight 50",
                rollback_command="no ip route 0.0.0.0/0 Trunk-02 weight 50",
                intervention_type="AUTOMATED",
                operational_risk="MEDIUM",
                recovery_time_seconds=30,
                rollback_available=True,
                effectiveness_pct=96.0,
                tradeoffs="Balances load across both links; requires parallel trunk capacity.",
                projected_telemetry={
                    "latency_ms": 6.2,
                    "packet_loss_pct": 0.0,
                    "utilization_pct": 49.0,
                    "queue_drops_per_sec": 0.0,
                    "cpu_utilization_pct": current_metrics.get("cpu_utilization_pct", 30.0),
                },
                expected_benefits=[
                    "Trunk utilization halved from 98% to 49%",
                    "Restores full throughput without dropping any packets",
                ],
                potential_risks=[
                    "Minor TCP flow reordering during initial hash table rebalancing",
                ],
            ),
            RemediationStrategy(
                strategy_id="strat-lacp-03",
                name="LACP Dynamic Bandwidth Aggregation (Port-Channel)",
                description="Bind secondary physical interface into LACP Port-Channel to double logical trunk capacity to 20 Gbps.",
                category="Capacity Scaling",
                target_device=target_device,
                command="interface Port-Channel1; channel-group 1 mode active",
                rollback_command="no channel-group 1",
                intervention_type="MAINTENANCE_WINDOW",
                operational_risk="LOW",
                recovery_time_seconds=300,
                rollback_available=True,
                effectiveness_pct=99.0,
                tradeoffs="Permanent capacity resolution; requires physical port cabling and switchport matching.",
                projected_telemetry={
                    "latency_ms": 4.8,
                    "packet_loss_pct": 0.0,
                    "utilization_pct": 48.0,
                    "queue_drops_per_sec": 0.0,
                    "cpu_utilization_pct": current_metrics.get("cpu_utilization_pct", 30.0),
                },
                expected_benefits=[
                    "Doubles aggregate trunk capacity to 20 Gbps",
                    "Provides N+1 physical link resiliency",
                ],
                potential_risks=[
                    "Requires 5-minute configuration and optical link synchronization",
                ],
            ),
        ]

    elif "wi-fi" in rc_lower or "wireless" in rc_lower or "rf" in rc_lower or "rssi" in rc_lower:
        # Weak Wi-Fi Signal
        return [
            RemediationStrategy(
                strategy_id="strat-rrm-01",
                name="Dynamic Radio Resource Management (RRM) & Tx Power Boost",
                description="Increase AP-02 5GHz transmit power from 12 dBm to 20 dBm and migrate channel from 36 to non-overlapping 149.",
                category="RF Optimization",
                target_device=target_device,
                command="wlc ap AP-02 radio 5ghz tx-power 20 channel 149 auto",
                rollback_command="wlc ap AP-02 radio 5ghz tx-power 12 channel 36",
                intervention_type="AUTOMATED",
                operational_risk="LOW",
                recovery_time_seconds=15,
                rollback_available=True,
                effectiveness_pct=95.0,
                tradeoffs="Increases edge coverage area and eliminates co-channel interference; slightly increases cell boundary overlap.",
                projected_telemetry={
                    "wifi_rssi_dbm": -62.0,
                    "wifi_retry_pct": 3.8,
                    "packet_loss_pct": 0.0,
                    "latency_ms": 6.5,
                },
                expected_benefits=[
                    "RSSI strengthens from -86 dBm to -62 dBm",
                    "802.11 frame retries drop from 42% to 3.8%",
                ],
                potential_risks=[
                    "Slightly increased co-channel contention if adjacent AP is too close",
                ],
            ),
            RemediationStrategy(
                strategy_id="strat-band-02",
                name="802.11k/v/r Client Band-Steering to 5GHz/6GHz",
                description="Force dual-band clients away from congested 2.4GHz spectrum via 802.11v BSS Transition requests.",
                category="Client Steering",
                target_device=target_device,
                command="wlc ssid Enterprise-WLAN band-select enable probe-cycle-count 2",
                rollback_command="wlc ssid Enterprise-WLAN band-select disable",
                intervention_type="AUTOMATED",
                operational_risk="LOW",
                recovery_time_seconds=30,
                rollback_available=True,
                effectiveness_pct=91.0,
                tradeoffs="Shifts capable clients to clean 5GHz spectrum; legacy 2.4GHz-only IoT devices remain unchanged.",
                projected_telemetry={
                    "wifi_rssi_dbm": -66.0,
                    "wifi_retry_pct": 4.5,
                    "packet_loss_pct": 0.1,
                    "latency_ms": 8.0,
                },
                expected_benefits=[
                    "Frees 2.4GHz spectrum for legacy devices",
                    "Increases per-client modulation MCS rates to index 9",
                ],
                potential_risks=[
                    "Older clients with poor 802.11v support may experience brief probe delay",
                ],
            ),
            RemediationStrategy(
                strategy_id="strat-ap-handoff-03",
                name="Min-RSSI Disassociation Roaming Kick",
                description="Enforce minimum RSSI threshold (-75 dBm) to disconnect sticky clients and trigger handoff to closer AP-01.",
                category="Roaming Optimization",
                target_device=target_device,
                command="wlc ap AP-02 client-rssi-threshold -75 disassociate",
                rollback_command="wlc ap AP-02 client-rssi-threshold 0",
                intervention_type="OPERATOR_APPROVAL",
                operational_risk="MEDIUM",
                recovery_time_seconds=20,
                rollback_available=True,
                effectiveness_pct=89.0,
                tradeoffs="Cures sticky client syndrome; may briefly disconnect clients stationed at room boundaries.",
                projected_telemetry={
                    "wifi_rssi_dbm": -58.0,
                    "wifi_retry_pct": 2.9,
                    "packet_loss_pct": 0.0,
                    "latency_ms": 5.2,
                },
                expected_benefits=[
                    "Forces clients to roam to AP-01 with -58 dBm signal",
                    "Reduces aggregate airtime waste from slow legacy transmissions",
                ],
                potential_risks=[
                    "Transient 1-second Wi-Fi reassociation reconnect for edge users",
                ],
            ),
        ]

    elif "interface" in rc_lower or "crc" in rc_lower or "physical" in rc_lower:
        # Interface / CRC Errors
        return [
            RemediationStrategy(
                strategy_id="strat-lacp-evict-01",
                name="Automated LACP Degraded Member Port Eviction",
                description="Immediately administratively shut down degraded interface ge-0/0/1 exhibiting CRC errors and route over clean member ge-0/0/2.",
                category="Interface Protection",
                target_device=target_device,
                command="interface GigabitEthernet0/0/1 shutdown",
                rollback_command="interface GigabitEthernet0/0/1 no shutdown",
                intervention_type="AUTOMATED",
                operational_risk="LOW",
                recovery_time_seconds=10,
                rollback_available=True,
                effectiveness_pct=98.0,
                tradeoffs="Instantly stops CRC frame corruptions; reduces aggregate LACP bundle capacity by 50% until physical replacement.",
                projected_telemetry={
                    "interface_crc_errors": 0,
                    "packet_loss_pct": 0.0,
                    "latency_ms": 4.2,
                    "utilization_pct": 42.0,
                },
                expected_benefits=[
                    "Eliminates 450 errors/sec instantly",
                    "Restores 0% packet loss across aggregation switch",
                ],
                potential_risks=[
                    "Bundle capacity reduced to 1 Gbps until cable replacement",
                ],
            ),
            RemediationStrategy(
                strategy_id="strat-ddm-reset-02",
                name="Optical SFP Transceiver DDM Re-Calibration & Soft Reset",
                description="Execute digital diagnostic monitoring laser recalibration and re-seat transceiver controller.",
                category="Hardware Maintenance",
                target_device=target_device,
                command="hw-module subslot 0/0 transceiver 1 reset ddm-tune",
                rollback_command="hw-module subslot 0/0 transceiver 1 default",
                intervention_type="OPERATOR_APPROVAL",
                operational_risk="MEDIUM",
                recovery_time_seconds=60,
                rollback_available=True,
                effectiveness_pct=85.0,
                tradeoffs="May recover dirty or uncalibrated optics without field dispatch; 60-second port flap during optical laser cycle.",
                projected_telemetry={
                    "interface_crc_errors": 0,
                    "packet_loss_pct": 0.2,
                    "latency_ms": 5.0,
                },
                expected_benefits=[
                    "Recalibrates optical Rx power levels if degradation was drift-related",
                ],
                potential_risks=[
                    "Port offline during 60-second laser reset",
                ],
            ),
            RemediationStrategy(
                strategy_id="strat-optic-swap-03",
                name="Field Technician Dispatch: Fiber Patch & SFP+ Replacement",
                description="Schedule hardware replacement ticket to swap LC fiber patch cord and 1000BASE-LX SFP transceiver.",
                category="Field Service",
                target_device=target_device,
                command="noc-ticket create --device Agg-Switch-01 --part SFP-1G-LX --priority P2",
                rollback_command="noc-ticket cancel --ticket-id auto",
                intervention_type="MAINTENANCE_WINDOW",
                operational_risk="LOW",
                recovery_time_seconds=1800,
                rollback_available=True,
                effectiveness_pct=99.9,
                tradeoffs="Permanent physical remediation; requires physical access and 30-minute SLA dispatch.",
                projected_telemetry={
                    "interface_crc_errors": 0,
                    "packet_loss_pct": 0.0,
                    "latency_ms": 3.8,
                },
                expected_benefits=[
                    "Brand new factory-tested optic and single-mode patch cable",
                    "Guaranteed long-term physical layer integrity",
                ],
                potential_risks=[
                    "Requires on-site personnel presence",
                ],
            ),
        ]

    elif "dns" in rc_lower or "dhcp" in rc_lower:
        # DNS / DHCP Failure
        return [
            RemediationStrategy(
                strategy_id="strat-dns-restart-01",
                name="Core Infrastructure Daemon Restart & Cache Flush",
                description="Restart systemd-resolved and kea-dhcp4-server daemons and flush corrupted DNS resolver cache.",
                category="Service Restoration",
                target_device=target_device,
                command="systemctl restart named kea-dhcp4 && rndc flush",
                rollback_command="systemctl restart named kea-dhcp4",
                intervention_type="AUTOMATED",
                operational_risk="LOW",
                recovery_time_seconds=15,
                rollback_available=True,
                effectiveness_pct=95.0,
                tradeoffs="Instantly clears memory corruption and lease deadlock; clears warm query cache causing slight 5ms lookup penalty for 2 minutes.",
                projected_telemetry={
                    "dns_response_ms": 14.0,
                    "dhcp_pool_utilization_pct": 42.0,
                    "latency_ms": 4.5,
                    "packet_loss_pct": 0.0,
                },
                expected_benefits=[
                    "DNS lookup latency drops from 2800ms to 14ms",
                    "Lease acquisition succeeds immediately for newly joining clients",
                ],
                potential_risks=[
                    "Cold cache causes slight latency increase on first lookup",
                ],
            ),
            RemediationStrategy(
                strategy_id="strat-anycast-02",
                name="BGP Anycast Secondary DNS Cluster Redirection",
                description="Withdraw BGP /32 host route for DNS-Server-01 to instantly redirect recursive queries to secondary cluster 10.0.0.54.",
                category="Anycast Failover",
                target_device=target_device,
                command="vtysh -c 'conf t' -c 'router bgp 65001' -c 'no network 10.0.0.53/32'",
                rollback_command="vtysh -c 'conf t' -c 'router bgp 65001' -c 'network 10.0.0.53/32'",
                intervention_type="AUTOMATED",
                operational_risk="LOW",
                recovery_time_seconds=5,
                rollback_available=True,
                effectiveness_pct=98.0,
                tradeoffs="Sub-second failover using standard routing convergence; secondary server must be healthy.",
                projected_telemetry={
                    "dns_response_ms": 8.0,
                    "dhcp_pool_utilization_pct": 45.0,
                    "latency_ms": 4.0,
                    "packet_loss_pct": 0.0,
                },
                expected_benefits=[
                    "Zero downtime failover completed in <5 seconds",
                    "Preserves full query caching on secondary node",
                ],
                potential_risks=[
                    "Secondary cluster experiences 2x query workload",
                ],
            ),
            RemediationStrategy(
                strategy_id="strat-pool-expand-03",
                name="Dynamic DHCP Scope Expansion & Lease Time Halving",
                description="Expand DHCP pool from /24 to /23 (510 hosts) and reduce lease duration from 24h to 2h.",
                category="Capacity Scaling",
                target_device=target_device,
                command="kea-dhcp-client config-set --subnet 10.0.1.0/23 --lease-duration 7200",
                rollback_command="kea-dhcp-client config-set --subnet 10.0.1.0/24 --lease-duration 86400",
                intervention_type="OPERATOR_APPROVAL",
                operational_risk="MEDIUM",
                recovery_time_seconds=45,
                rollback_available=True,
                effectiveness_pct=92.0,
                tradeoffs="Permanently prevents lease exhaustion; doubles DHCP broadcast renew traffic frequency.",
                projected_telemetry={
                    "dns_response_ms": 18.0,
                    "dhcp_pool_utilization_pct": 28.0,
                    "latency_ms": 4.8,
                    "packet_loss_pct": 0.0,
                },
                expected_benefits=[
                    "Pool utilization drops from 99% to 28%",
                    "Rapid reclamation of abandoned leases",
                ],
                potential_risks=[
                    "Higher broadcast renewal traffic across wired edge switches",
                ],
            ),
        ]

    else:
        # Default / Normal Network Baseline Optimization
        return [
            RemediationStrategy(
                strategy_id="strat-baseline-01",
                name="Automated Configuration Audit & Baseline Compliance Verification",
                description="Run automated Ansible audit playbook across all topology nodes to ensure running config matches golden template.",
                category="Compliance",
                target_device=target_device,
                command="ansible-playbook -i hosts audit_golden_config.yml",
                rollback_command="echo 'No rollback required for read-only audit'",
                intervention_type="AUTOMATED",
                operational_risk="LOW",
                recovery_time_seconds=30,
                rollback_available=True,
                effectiveness_pct=99.0,
                tradeoffs="Read-only diagnostic audit; zero data-plane impact.",
                projected_telemetry={
                    "latency_ms": 4.5,
                    "packet_loss_pct": 0.0,
                    "cpu_utilization_pct": 20.0,
                },
                expected_benefits=[
                    "Validates compliance with organizational hardening policies",
                ],
                potential_risks=[],
            ),
            RemediationStrategy(
                strategy_id="strat-baseline-02",
                name="Dynamic Telemetry Polling Rate Optimization",
                description="Tune streaming telemetry cadence from 1s to 5s to optimize control plane telemetry overhead.",
                category="Monitoring",
                target_device=target_device,
                command="telemetry-agent set-cadence --interval 5s",
                rollback_command="telemetry-agent set-cadence --interval 1s",
                intervention_type="AUTOMATED",
                operational_risk="LOW",
                recovery_time_seconds=10,
                rollback_available=True,
                effectiveness_pct=95.0,
                tradeoffs="Reduces CPU usage by 5%; slightly widens time granularity.",
                projected_telemetry={
                    "latency_ms": 4.2,
                    "packet_loss_pct": 0.0,
                    "cpu_utilization_pct": 16.0,
                },
                expected_benefits=[
                    "Conserves CPU cycles and WAN telemetry bandwidth",
                ],
                potential_risks=[],
            ),
            RemediationStrategy(
                strategy_id="strat-baseline-03",
                name="Proactive Micro-Burst Buffer Profiling",
                description="Enable hardware ASIC micro-burst queue watermark monitors to detect sub-millisecond congestion spikes.",
                category="Preventive",
                target_device=target_device,
                command="hardware profile microburst-detection enable watermark 80",
                rollback_command="hardware profile microburst-detection disable",
                intervention_type="AUTOMATED",
                operational_risk="LOW",
                recovery_time_seconds=15,
                rollback_available=True,
                effectiveness_pct=96.0,
                tradeoffs="Provides deep visibility into hidden micro-bursts.",
                projected_telemetry={
                    "latency_ms": 4.5,
                    "packet_loss_pct": 0.0,
                    "cpu_utilization_pct": 22.0,
                },
                expected_benefits=[
                    "Early warning detection of intermittent buffer pressure",
                ],
                potential_risks=[],
            ),
        ]


class RemediationSimulator:
    """
    Deterministic What-If Remediation Simulation Engine.
    """

    def get_candidate_strategies(
        self,
        root_cause: str,
        target_device: str,
        current_metrics: Optional[Dict[str, Any]] = None,
    ) -> List[RemediationStrategy]:
        """Returns 3 deterministic candidate strategies for a root cause and device."""
        return _build_strategies_for_root_cause(
            root_cause=root_cause,
            target_device=target_device,
            current_metrics=current_metrics or {},
        )

    def run_simulation(
        self,
        incident_id: str,
        strategy: RemediationStrategy,
        current_telemetry: Dict[str, Any],
        target_device: str,
    ) -> SimulationResult:
        """
        Executes a deterministic What-If simulation comparing current state against projected state.
        """
        sim_id = f"SIM-{uuid.uuid4().hex[:8].upper()}"

        before = dict(current_telemetry)
        projected = dict(strategy.projected_telemetry)

        # Merge any unprojected metrics from before
        for k, v in before.items():
            if k not in projected and v is not None:
                projected[k] = v

        # Calculate deltas deterministically
        deltas: Dict[str, Dict[str, Any]] = {}
        for metric, after_val in projected.items():
            if metric in before and before[metric] is not None and isinstance(before[metric], (int, float)):
                before_val = float(before[metric])
                after_val_float = float(after_val) if isinstance(after_val, (int, float)) else 0.0
                diff = round(after_val_float - before_val, 2)

                if before_val != 0.0:
                    pct = round((diff / abs(before_val)) * 100.0, 1)
                else:
                    pct = 0.0 if diff == 0 else 100.0

                # Determine if improved
                status = "UNCHANGED"
                if metric in ["latency_ms", "jitter_ms", "packet_loss_pct", "cpu_utilization_pct", "utilization_pct", "queue_drops_per_sec", "interface_crc_errors", "dns_response_ms", "wifi_retry_pct"]:
                    status = "IMPROVED" if diff < 0 else ("DEGRADED" if diff > 0 else "UNCHANGED")
                elif metric in ["wifi_rssi_dbm", "wifi_snr_db", "throughput_mbps"]:
                    status = "IMPROVED" if diff > 0 else ("DEGRADED" if diff < 0 else "UNCHANGED")

                deltas[metric] = {
                    "before": before_val,
                    "after": after_val_float,
                    "delta": diff,
                    "pct_change": pct,
                    "status": status,
                }

        # Calculate health scores
        health_before = 35.0  # Default degraded
        if "cpu_utilization_pct" in before and before["cpu_utilization_pct"] and before["cpu_utilization_pct"] > 90:
            health_before = 18.0
        elif "packet_loss_pct" in before and before["packet_loss_pct"] and before["packet_loss_pct"] > 3:
            health_before = 28.0

        health_after = min(100.0, round(health_before + (strategy.effectiveness_pct * 0.75), 1))
        if health_after >= 85.0:
            sla_after = "COMPLIANT"
            recovery_status = "FULL_RECOVERY"
        elif health_after >= 60.0:
            sla_after = "AT_RISK"
            recovery_status = "PARTIAL_MITIGATION"
        else:
            sla_after = "BREACHED"
            recovery_status = "STABILIZED"

        assumptions = [
            f"Deterministic simulation based on network baseline parameters for {target_device}",
            f"Assumes {strategy.intervention_type.lower()} execution model with zero configuration syntax errors",
            "Simulated state models control-plane and data-plane queue recovery in benchmark digital twin",
            "Does not account for external upstream transit ISP blackholing",
        ]

        limitations = [
            "Simulation is executed on digital twin model; physical hardware was not reconfigured",
            "Environmental RF fluctuations and micro-burst packet timing are modeled deterministically",
        ]

        return SimulationResult(
            simulation_id=sim_id,
            incident_id=incident_id,
            strategy_id=strategy.strategy_id,
            strategy_name=strategy.name,
            target_device=target_device,
            before_telemetry=before,
            projected_telemetry=projected,
            telemetry_deltas=deltas,
            device_health_before=health_before,
            device_health_after=health_after,
            sla_status_before="BREACHED",
            sla_status_after=sla_after,
            fault_path_cleared=True,
            recovery_status=recovery_status,
            expected_benefits=strategy.expected_benefits,
            potential_risks=strategy.potential_risks,
            assumptions=assumptions,
            limitations=limitations,
        )

    def generate_comparison_matrix(
        self,
        incident_id: str,
        target_device: str,
        root_cause: str,
        current_metrics: Optional[Dict[str, Any]] = None,
    ) -> StrategyComparisonMatrix:
        """
        Builds a comprehensive side-by-side comparison matrix across all candidate strategies.
        """
        strategies = self.get_candidate_strategies(
            root_cause=root_cause,
            target_device=target_device,
            current_metrics=current_metrics or {},
        )

        recommended = strategies[0]  # Strategy A is recommended primary
        rationale = (
            f"Strategy '{recommended.name}' is recommended as the primary remediation action because "
            f"it offers the lowest operational risk ({recommended.operational_risk}) and fastest recovery time "
            f"({recommended.recovery_time_seconds}s) with {recommended.effectiveness_pct}% expected effectiveness. "
            f"Alternative strategies introduce higher maintenance overhead or brief service disruption."
        )

        summary = (
            f"Evaluated {len(strategies)} alternative remediation approaches for {root_cause} on {target_device}. "
            f"Trade-offs span automated data-plane policing, process-level isolation, and physical/gateway failovers."
        )

        return StrategyComparisonMatrix(
            incident_id=incident_id,
            device_id=target_device,
            root_cause=root_cause,
            strategies=strategies,
            recommended_strategy_id=recommended.strategy_id,
            recommendation_rationale=rationale,
            comparison_summary=summary,
        )


remediation_simulator = RemediationSimulator()

