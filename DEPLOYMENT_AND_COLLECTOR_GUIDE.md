# NetCoop AI — Deployment & Network Collector Integration Guide
**IIT Bhubaneswar Agentic AI Grand Finale — Production Architecture & Live Deployment Manual**

---

## 1. Executive Summary & Architecture Overview

NetCoop AI is designed as a hybrid enterprise network observability and fault diagnosis platform. When deploying in real-world infrastructure, a fundamental networking constraint arises:

> **The Inbound Private IP Wall**: A cloud instance hosted on Render (`https://netcoop-backend.onrender.com`), AWS, or GCP resides in a public cloud subnet and **cannot initiate inbound connections** to private RFC-1918 subnets (`192.168.1.0/24`, `10.0.0.0/8`, `172.16.0.0/12`) behind residential or corporate NAT firewalls. Demanding that network administrators open port forwarding on WAN ports for SNMP (UDP 161) or RESTCONF is an unacceptable security violation and impractical in multi-site deployments.

### NetCoop AI Solution: The Zero-Inbound Local Collector Agent
NetCoop AI resolves this via a lightweight, autonomous **Local Network Collector Agent** (`collector/`):
- Runs inside the target LAN on a Windows machine, Linux server, Docker container, or Raspberry Pi.
- Polls LAN switches, routers, and Wi-Fi access points directly via local protocols (SNMP v2c/v3, RESTCONF, active TCP reachability probes, and LAN Syslog UDP 5140).
- Keeps all sensitive credentials (passwords, SNMP communities, API keys) strictly on the local machine — credentials **never** leave the LAN.
- Establishes a **secure outbound HTTPS connection** to the deployed Cloud Backend using an enrollment token.
- Normalizes telemetry into the **Canonical Interoperability Protocol (`TelemetryRecord`)** and tags provenance with `telemetry_origin="LIVE_DEVICE"`.
- Streams telemetry up to the cloud orchestrator where the 5 specialized agents diagnose real faults without synthetic fallbacks.

```
+-----------------------------------------------------------------------------------------+
|                                    PRIVATE LOCAL LAN                                    |
|                                                                                         |
|  +--------------------+         SNMP v2c/v3 (UDP 161)         +----------------------+  |
|  | Cisco Core Switch  | <-----------------------------------+ |                      |  |
|  | 192.168.1.1        |                                       |                      |  |
|  +--------------------+         RESTCONF YANG (HTTPS 443)     |                      |  |
|  +--------------------+ <-----------------------------------+ |  Local Network       |  |
|  | Edge Router        |                                       |  Collector Agent     |  |
|  | 192.168.1.254      |         TCP Connect Latency Probe     |  (`collector/run.py`)|  |
|  +--------------------+ <-----------------------------------+ |                      |  |
|  +--------------------+                                       |  - Zero inbound ports|  |
|  | Wi-Fi AP Controller|         Syslog Stream (UDP 5140)      |  - Local credentials |  |
|  | 192.168.1.50       | ------------------------------------> |  - Anti-scan guard   |  |
|  +--------------------+                                       +----------+-----------+  |
+--------------------------------------------------------------------------|--------------+
                                                                           |
                                            Outbound HTTPS POST /telemetry |
                                            Encrypted TLS + Session Token  |
                                                                           v
+-----------------------------------------------------------------------------------------+
|                                  PUBLIC CLOUD (Render.com)                              |
|                                                                                         |
|   +---------------------------------------------------------------------------------+   |
|   |                       FastAPI Multi-Agent Backend Service                       |   |
|   |                                                                                 |   |
|   |  - CollectorHub (Session auth, device inventory, stale data cutoff >300s)       |   |
|   |  - 5 Autonomous Specialized Diagnostic Agents                                   |   |
|   |     * PerformanceAgent (Congestion, RTT, bufferbloat)                           |   |
|   |     * InfrastructureAgent (CRC errors, interface discards, hardware fault)      |   |
|   |     * ConnectivityAgent (Wi-Fi RSSI, SNR, client disconnects)                   |   |
|   |     * FaultCorrelationAgent (Cross-device root-cause propagation)               |   |
|   |     * RecommendationAgent (Remediation playbook & CLI scripts)                  |   |
|   |  - Digital Twin Engine & What-If Remediation Simulator                          |   |
|   +---------------------------------------------------------------------------------+   |
|                                            ^                                            |
|                                            | REST API & Real-time Replay                |
|   +----------------------------------------+----------------------------------------+   |
|   |                 React + Vite NOC Operations Center Dashboard                    |   |
|   |  - Interactive React Flow Topology                                              |   |
|   |  - Collector Hub Dashboard & Device Health Badges (`STREAMING_LIVE`)            |   |
|   |  - Truthful Provenance Badges (`🟢 LIVE DEVICE`, `🟡 CUSTOM IMPORT`, `🟣 SIM`)   |   |
|   +---------------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Deploying NetCoop AI to Render Cloud

The repository includes a ready-to-deploy **Render Blueprint** (`render.yaml`).

### Step 1: Push Repository to GitHub / GitLab
Ensure your workspace changes are committed and pushed to your remote git repository:
```bash
git add .
git commit -m "feat: implement deployable collector hub and network integration"
git push origin main
```

### Step 2: Deploy Blueprint on Render
1. Navigate to the [Render Dashboard](https://dashboard.render.com).
2. Click **Blueprints** -> **New Blueprint Instance**.
3. Connect your repository (`TeamFusionNetCoopAI`).
4. Render automatically parses `render.yaml` and provisions two services:
   - `netcoop-ai-backend` (Python Web Service)
   - `netcoop-ai-frontend` (Static Site)
5. Under `netcoop-ai-frontend` Environment Variables, verify:
   ```env
   VITE_API_URL=https://netcoop-ai-backend.onrender.com
   ```
6. Click **Apply**. Both services will build and deploy in ~3 minutes.

---

## 3. Pairing the Local Collector with Cloud Backend

Once the Cloud Backend is running (or running locally on `http://127.0.0.1:8000` for judging demonstrations), follow this pairing workflow:

### Step 1: Generate Enrollment Token from NOC Dashboard
1. Open the NetCoop AI Dashboard.
2. Click the **🔌 Live Integrations** tab in the top navigation bar.
3. Under the **📡 On-Premise Network Collectors** section, click **+ Pair New Collector**.
4. Enter a name (e.g., `IIT-BBS-Lab-Collector-01`) and click **Generate Enrollment Token**.
5. The UI displays the unique enrollment token (`nc_coll_...`) valid for 24 hours and provides copyable commands.

### Step 2: Run Collector on Local Windows Machine
Open PowerShell in `TeamFusionNetCoopAI` and launch the collector:
```powershell
# Set backend URL to your cloud deployment or local backend
$env:PYTHONPATH="."
python -m collector.run --backend https://netcoop-ai-backend.onrender.com --token nc_coll_your_token_here
```
For local hackathon testing:
```powershell
$env:PYTHONPATH="."
python -m collector.run --backend http://127.0.0.1:8000 --token nc_coll_your_token_here
```

### Step 3: Run Collector on Linux / Raspberry Pi (Systemd Service)
For permanent 24/7 on-premise monitoring:
```bash
# Clone collector or install standalone dependencies
pip install pydantic httpx

# Launch collector daemon
python3 -m collector.run --backend https://netcoop-ai-backend.onrender.com --token nc_coll_your_token_here
```

To create a `systemd` background service:
```ini
# /etc/systemd/system/netcoop-collector.service
[Unit]
Description=NetCoop AI LAN Telemetry Collector
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/netcoop
ExecStart=/usr/bin/python3 -m collector.run --backend https://netcoop-ai-backend.onrender.com --token nc_coll_...
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
Enable and start:
```bash
sudo systemctl enable --now netcoop-collector
```

---

## 4. Configuring Physical Network Devices for Real Telemetry

To collect genuine telemetry, network devices on your LAN must have telemetry interfaces enabled. Below are the exact vendor configuration commands:

### A. Cisco IOS-XE / Catalyst (Routers & Switches)
1. **Enable SNMP v2c / v3**:
```cisco
configure terminal
! Configure read-only community string with ACL restriction
snmp-server community NetCoopRO RO
snmp-server enable traps
! Specify collector host for SNMP traps
snmp-server host 192.168.1.100 version 2c NetCoopRO
end
write memory
```

2. **Enable RESTCONF (YANG Data Model Interface)**:
```cisco
configure terminal
! Enable HTTP secure server and RESTCONF endpoint
ip http secure-server
ip http authentication local
restconf
username netcoop privilege 15 secret StrongPassword123!
end
write memory
```

3. **Enable Syslog Forwarding to Collector**:
```cisco
configure terminal
logging buffered 64000
logging trap informational
! Forward syslog packets directly to Collector UDP port 5140
logging host 192.168.1.100 transport udp port 5140
end
write memory
```

---

### B. Juniper Junos (SRX / EX Series)
```junos
set snmp community NetCoopRO authorization read-only
set snmp community NetCoopRO clients 192.168.1.100/32
set system syslog host 192.168.1.100 any any
set system syslog host 192.168.1.100 port 5140
commit
```

---

### C. MikroTik RouterOS
```routeros
/snmp community add name=NetCoopRO addresses=192.168.1.100/32 read-access=yes
/snmp set enabled=yes
/system logging action add name=netcoop target=remote remote=192.168.1.100 remote-port=5140
/system logging add action=netcoop topics=critical,error,warning,interface
```

---

### D. Consumer / Small Office Wi-Fi Routers (TP-Link, ASUS, Netgear)
Most consumer Wi-Fi routers do not expose SNMP or RESTCONF due to firmware restrictions. For these devices:
1. **Active TCP Reachability Probe**:
   Register the router IP (`192.168.1.1`) with `protocol="TCP_PROBE"` targeting port 80 (HTTP) or 443 (HTTPS) or 53 (DNS). The collector executes non-blocking TCP socket handshakes, accurately recording real packet loss and transport latency.
2. **Syslog Logging**:
   In the router's web admin UI (typically **System Tools** -> **System Log**), set **Remote Syslog Server** to the collector's IP (`192.168.1.100`) and port `5140`.

---

## 5. Metric Availability & Limitations by Protocol

Judges require absolute transparency regarding what physical metrics can and cannot be collected per protocol:

| Metric | Active TCP Probe | SNMP v2c/v3 | RESTCONF (YANG) | Syslog Ingestion | Wi-Fi Controller |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Round-Trip Latency** | **Yes** (Real TCP handshake) | No (Poller overhead) | No (Poller overhead) | No | No |
| **Packet Loss %** | **Yes** (Socket timeouts) | No | No | No | No |
| **Device Status (UP/DOWN)** | **Yes** | **Yes** (`ifOperStatus`) | **Yes** (`oper-status`) | **Yes** (`LINK-DOWN`) | **Yes** |
| **CPU Utilization %** | *Null* (Impossible via TCP) | **Yes** (Vendor MIB) | **Yes** (Cisco process) | **Yes** (Threshold alert) | *Null* |
| **RAM Utilization %** | *Null* (Impossible via TCP) | **Yes** (Vendor MIB) | **Yes** (Cisco memory) | *Null* | *Null* |
| **CRC Frame Errors** | *Null* | **Yes** (`ifInErrors`) | **Yes** (`in-errors`) | **Yes** (`CRC_ERR`) | *Null* |
| **Throughput In/Out** | *Null* | **Yes** (`ifIn/OutOctets`)| **Yes** (`in/out-octets`)| *Null* | **Yes** |
| **Wi-Fi RSSI / SNR** | *Null* | *Null* | *Null* | *Null* | **Yes** (dBm/dB) |
| **Active Wi-Fi Clients** | *Null* | *Null* | *Null* | *Null* | **Yes** (Count) |

> **Audit Assurance**: If an active TCP probe is configured for a router, NetCoop AI reports `latency_ms` and `packet_loss_pct`, but leaves `cpu_utilization_pct=None` and `crc_errors_delta=None`. It **never** manufactures synthetic CPU or CRC metrics.

---

## 6. End-to-End Verification Checklist

Run through this checklist to demonstrate live network integration to hackathon judges:

1. **Verify Backend Health**:
   ```bash
   curl http://127.0.0.1:8000/api/health
   # Returns: {"status": "ok", "service": "NetCoop AI Multi-Agent Diagnostic Engine"}
   ```
2. **Verify Collector Enrollment & Device Registration**:
   ```bash
   curl http://127.0.0.1:8000/api/collectors/inventory
   # Returns list of paired collectors and devices with status: "STREAMING_LIVE"
   ```
3. **Verify Stale Data Guard**:
   If a collector stops streaming for > 300 seconds, its devices automatically transition to `STALE_TELEMETRY` and are excluded from live diagnosis.
4. **Trigger Live Multi-Agent Diagnosis**:
   In the UI, click **Run Live Network Diagnosis** under the Live Integrations tab. The top badge updates to `🟢 LIVE DEVICE`. The report displays:
   - Genuine latency and packet loss metrics measured from live packets
   - Zero fallback to synthetic scenario files
   - Clear confidence scores grounded solely in collected records

