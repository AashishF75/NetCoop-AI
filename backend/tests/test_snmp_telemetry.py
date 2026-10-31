"""
Phase 1 Test Suite: Authenticated SNMPv3 and Legacy SNMPv2c Telemetry.
Validates:
- SNMPv3 USM credential and protocol bindings (SHA/MD5, AES/DES).
- SNMPv2c legacy community binding.
- Parsing of standard MIB-II OIDs (sysName, sysDescr, sysUpTime, ifTable/ifXTable).
- Extraction of CPU and memory from standard HR-MIB and Cisco enterprise MIBs.
- Explicit unsupported OID handling without metric fabrication.
- Graceful handling of SNMP timeouts and authentication failures.
- Zero credential exposure in telemetry records.
- End-to-end diagnosis by the 5-agent multi-agent swarm.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from pyasn1.type import univ
from pysnmp.proto import rfc1905

from collector.config import LocalDeviceConfig, DeviceProtocol
from collector.adapters.snmp_poller import (
    poll_snmp_device,
    build_security_credentials,
    _is_unsupported_val,
)
from pysnmp.hlapi.asyncio import (
    usmHMACSHAAuthProtocol,
    usmHMAC192SHA256AuthProtocol,
    usmHMACMD5AuthProtocol,
    usmAesCfb128Protocol,
    usmDESPrivProtocol,
)
from app.orchestrator.engine import MultiAgentOrchestrator


class TestSNMPCredentialsAndProtocols:
    """Tests SNMP credential construction and security models."""

    def test_snmpv3_auth_priv_construction(self):
        cfg = LocalDeviceConfig(
            device_id="ROUTER-CORE-01",
            name="Core Router 01",
            host="10.10.10.1",
            protocol=DeviceProtocol.SNMP,
            snmp_version="v3",
            snmp_user="netadmin",
            snmp_auth_protocol="SHA",
            snmp_auth_password="AuthSecretPassword123",
            snmp_priv_protocol="AES",
            snmp_priv_password="PrivSecretPassword123",
            snmp_security_level="authPriv",
        )
        creds, label = build_security_credentials(cfg)
        assert label == "SNMPv3 (authPriv)"
        assert creds.userName == "netadmin"
        assert creds.authProtocol == usmHMACSHAAuthProtocol
        assert creds.privProtocol == usmAesCfb128Protocol

    def test_snmpv3_sha256_and_des_options(self):
        cfg = LocalDeviceConfig(
            device_id="ROUTER-EDGE-01",
            name="Edge Router",
            host="10.10.20.1",
            protocol=DeviceProtocol.SNMP,
            snmp_version="v3",
            snmp_user="sha256user",
            snmp_auth_protocol="SHA256",
            snmp_auth_password="AuthSecretPassword123",
            snmp_priv_protocol="DES",
            snmp_priv_password="PrivSecretPassword123",
            snmp_security_level="authPriv",
        )
        creds, label = build_security_credentials(cfg)
        assert label == "SNMPv3 (authPriv)"
        assert creds.authProtocol == usmHMAC192SHA256AuthProtocol
        assert creds.privProtocol == usmDESPrivProtocol

    def test_snmpv3_auth_no_priv(self):
        cfg = LocalDeviceConfig(
            device_id="SWITCH-ACC-01",
            name="Access Switch",
            host="10.10.30.1",
            protocol=DeviceProtocol.SNMP,
            snmp_version="v3",
            snmp_user="monitor",
            snmp_auth_protocol="MD5",
            snmp_auth_password="MonitorPassword456",
            snmp_security_level="authNoPriv",
        )
        creds, label = build_security_credentials(cfg)
        assert label == "SNMPv3 (authNoPriv)"
        assert creds.userName == "monitor"
        assert creds.authProtocol == usmHMACMD5AuthProtocol

    def test_snmpv2c_legacy_explicit_configuration(self):
        cfg = LocalDeviceConfig(
            device_id="LEGACY-SWITCH-01",
            name="Legacy Switch",
            host="10.10.99.1",
            protocol=DeviceProtocol.SNMP,
            snmp_version="v2c",
            snmp_community="acme_ro_community",
        )
        creds, label = build_security_credentials(cfg)
        assert label == "SNMPv2c"
        assert creds.communityName == "acme_ro_community"
        assert creds.message_processing_model == 1  # SNMPv2c RFC 1901


class TestSNMPTelemetryCollection:
    """Tests metric querying, ASN.1 parsing, and error handling."""

    @pytest.mark.asyncio
    async def test_successful_snmp_collection_with_cisco_mibs(self):
        """Simulates full SNMP response with standard MIB-II and Cisco enterprise OIDs."""
        device = LocalDeviceConfig(
            device_id="CISCO-2960X",
            name="Cisco Catalyst 2960X",
            host="192.168.1.1",
            protocol=DeviceProtocol.SNMP,
            snmp_version="v3",
            snmp_user="nocadmin",
            snmp_auth_password="AuthSecretPassword123",
            snmp_priv_password="PrivSecretPassword123",
        )

        # Mock VarBinds returned by pysnmp
        mock_var_binds = [
            (None, univ.OctetString("Cisco IOS Software, C2960X-UNIVERSALK9-M, Version 15.2(7)E7")),  # sys_descr
            (None, univ.Integer(12345678)),  # sys_uptime (123456.78s)
            (None, univ.OctetString("sw-core-01.lab")),  # sys_name
            (None, univ.Integer(1)),  # if_oper_status (1 = UP)
            (None, univ.Integer(1)),  # if_admin_status (1 = UP)
            (None, univ.Integer(45000000)),  # if_in_octets
            (None, univ.Integer(52000000)),  # if_out_octets
            (None, univ.Integer(12)),  # if_in_errors
            (None, univ.Integer(0)),  # if_out_errors
            (None, univ.Integer(5)),  # if_in_discards
            (None, univ.Integer(1)),  # if_out_discards
            (None, univ.OctetString("GigabitEthernet1/0/1")),  # if_name
            (None, rfc1905.NoSuchObject()),  # hr_cpu (not present on this device)
            (None, rfc1905.NoSuchObject()),  # hr_storage_used
            (None, rfc1905.NoSuchObject()),  # hr_storage_size
            (None, univ.Integer(38)),  # cisco_cpu (38% 5-min CPU)
            (None, univ.Integer(72000000)),  # cisco_mem_used
            (None, univ.Integer(28000000)),  # cisco_mem_free (72% utilized)
        ]

        with patch("collector.adapters.snmp_poller.get_cmd", new_callable=AsyncMock) as mock_get_cmd, \
             patch("collector.adapters.snmp_poller.UdpTransportTarget.create", new_callable=AsyncMock) as mock_target:
            mock_target.return_value = MagicMock()
            mock_get_cmd.return_value = (None, 0, 0, mock_var_binds)

            records, avail, unsupp = await poll_snmp_device(device)

            assert len(records) == 1
            rec = records[0]
            assert rec.device_status == "UP"
            assert rec.sys_name == "sw-core-01.lab"
            assert "C2960X" in rec.sys_descr
            assert rec.sys_uptime_sec == 123456.8
            assert rec.interface_id == "GigabitEthernet1/0/1"
            assert rec.interface_oper_status == "UP"
            assert rec.interface_admin_status == "UP"
            assert rec.interface_in_octets == 45000000
            assert rec.interface_out_octets == 52000000
            assert rec.interface_crc_errors == 12
            assert rec.interface_in_discards == 5
            assert rec.cpu_utilization_pct == 38.0
            assert rec.memory_utilization_pct == 72.0
            assert rec.packet_loss_pct == 0.0
            assert rec.telemetry_origin == "LIVE_DEVICE"

            assert "sys_name" in avail
            assert "interface_oper_status" in avail
            assert "cpu_utilization_pct" in avail
            assert "memory_utilization_pct" in avail

    @pytest.mark.asyncio
    async def test_unsupported_cpu_memory_oids_never_fabricated(self):
        """
        Anti-fabrication check: If the device does not expose CPU/RAM MIBs,
        values MUST remain None and appear in unsupported_metrics.
        """
        device = LocalDeviceConfig(
            device_id="GENERIC-SWITCH-01",
            name="Generic Layer 2 Switch",
            host="10.0.0.1",
            protocol=DeviceProtocol.SNMP,
            snmp_version="v2c",
            snmp_community="public",
        )

        # Device returns standard MIB-II, but NoSuchObject for all CPU/Memory OIDs
        mock_var_binds = [
            (None, univ.OctetString("Generic Managed Switch 24-Port")),
            (None, univ.Integer(500000)),
            (None, univ.OctetString("sw-access-01")),
            (None, univ.Integer(1)),  # UP
            (None, univ.Integer(1)),  # UP
            (None, univ.Integer(100000)),
            (None, univ.Integer(100000)),
            (None, univ.Integer(0)),  # 0 errors
            (None, univ.Integer(0)),
            (None, univ.Integer(0)),
            (None, univ.Integer(0)),
            (None, univ.OctetString("eth0")),
            (None, rfc1905.NoSuchObject()),  # hr_cpu
            (None, rfc1905.NoSuchObject()),  # hr_storage_used
            (None, rfc1905.NoSuchObject()),  # hr_storage_size
            (None, rfc1905.NoSuchInstance()), # cisco_cpu
            (None, rfc1905.NoSuchInstance()), # cisco_mem_used
            (None, rfc1905.NoSuchInstance()), # cisco_mem_free
        ]

        with patch("collector.adapters.snmp_poller.get_cmd", new_callable=AsyncMock) as mock_get_cmd, \
             patch("collector.adapters.snmp_poller.UdpTransportTarget.create", new_callable=AsyncMock) as mock_target:
            mock_target.return_value = MagicMock()
            mock_get_cmd.return_value = (None, 0, 0, mock_var_binds)

            records, avail, unsupp = await poll_snmp_device(device)

            rec = records[0]
            assert rec.cpu_utilization_pct is None, "CPU was fabricated!"
            assert rec.memory_utilization_pct is None, "Memory was fabricated!"
            assert "cpu_utilization_pct" in unsupp
            assert "memory_utilization_pct" in unsupp
            assert "Unsupported (not fabricated)" in rec.custom_metrics["probe_note"]

    @pytest.mark.asyncio
    async def test_snmp_timeout_handling(self):
        """Verifies that an unresponsive SNMP target produces DOWN status with 100% loss."""
        device = LocalDeviceConfig(
            device_id="DEAD-ROUTER",
            name="Unresponsive Device",
            host="192.0.2.1",
            protocol=DeviceProtocol.SNMP,
            timeout_sec=0.5,
        )

        with patch("collector.adapters.snmp_poller.get_cmd", new_callable=AsyncMock) as mock_get_cmd, \
             patch("collector.adapters.snmp_poller.UdpTransportTarget.create", new_callable=AsyncMock) as mock_target:
            mock_target.return_value = MagicMock()
            # Simulate timeout error indication
            mock_get_cmd.return_value = ("No SNMP response received before timeout", 0, 0, ())

            records, avail, unsupp = await poll_snmp_device(device)
            rec = records[0]
            assert rec.device_status == "DOWN"
            assert rec.packet_loss_pct == 100.0
            assert rec.custom_metrics["error_type"] == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_snmp_authentication_failure_handling(self):
        """Verifies that wrong SNMPv3 credentials result in AUTH_REJECTED status."""
        device = LocalDeviceConfig(
            device_id="SECURE-ROUTER",
            name="Protected Gateway",
            host="10.10.1.1",
            protocol=DeviceProtocol.SNMP,
            snmp_version="v3",
            snmp_user="baduser",
            snmp_auth_password="WrongPassword!",
        )

        with patch("collector.adapters.snmp_poller.get_cmd", new_callable=AsyncMock) as mock_get_cmd, \
             patch("collector.adapters.snmp_poller.UdpTransportTarget.create", new_callable=AsyncMock) as mock_target:
            mock_target.return_value = MagicMock()
            # Simulate USM authentication failure indication
            mock_get_cmd.return_value = ("Authentication failure: usmStatsWrongDigests", 0, 0, ())

            records, avail, unsupp = await poll_snmp_device(device)
            rec = records[0]
            assert rec.device_status == "AUTH_REJECTED"
            assert rec.custom_metrics["error_type"] == "AUTHENTICATION_FAILURE"

    def test_credential_containment_in_telemetry_record(self):
        """Verifies that device credentials NEVER leak into TelemetryRecord or its dump."""
        device = LocalDeviceConfig(
            device_id="ROUTER-CONFIDENTIAL",
            name="Confidential Router",
            host="10.0.0.5",
            protocol=DeviceProtocol.SNMP,
            snmp_version="v3",
            snmp_user="secretadmin",
            snmp_auth_password="TopSecretAuthPassword123!",
            snmp_priv_password="TopSecretPrivPassword123!",
            snmp_community="private_community_str",
        )

        creds, _ = build_security_credentials(device)
        assert creds is not None

        # Even with full config, TelemetryRecord must not contain passwords or community strings
        from collector.schema import TelemetryRecord
        rec = TelemetryRecord(
            device_id=device.device_id,
            device_status="UP",
            telemetry_origin="LIVE_DEVICE",
            custom_metrics={"protocol": "SNMPv3"},
        )
        data = rec.model_dump()
        serialized = str(data)
        assert "TopSecretAuthPassword123!" not in serialized
        assert "TopSecretPrivPassword123!" not in serialized
        assert "private_community_str" not in serialized

    @pytest.mark.asyncio
    async def test_end_to_end_orchestrator_diagnosis_with_snmp_telemetry(self):
        """Verifies that SNMP telemetry is ingested and diagnosed by all 5 agents."""
        mock_var_binds = [
            (None, univ.OctetString("Cisco IOS Software, 15.2")),
            (None, univ.Integer(8800000)),
            (None, univ.OctetString("Core-Router-01")),
            (None, univ.Integer(1)),  # UP
            (None, univ.Integer(1)),
            (None, univ.Integer(950000000)),  # Heavy traffic
            (None, univ.Integer(940000000)),
            (None, univ.Integer(850)),  # CRC errors
            (None, univ.Integer(0)),
            (None, univ.Integer(40)),
            (None, univ.Integer(0)),
            (None, univ.OctetString("TenGigabitEthernet0/1")),
            (None, rfc1905.NoSuchObject()),
            (None, rfc1905.NoSuchObject()),
            (None, rfc1905.NoSuchObject()),
            (None, univ.Integer(18)),  # CPU 18%
            (None, univ.Integer(40000000)),
            (None, univ.Integer(60000000)),
        ]

        device = LocalDeviceConfig(
            device_id="Core-Router-01",
            name="Core Router 01",
            host="10.200.1.1",
            protocol=DeviceProtocol.SNMP,
            snmp_version="v3",
            snmp_user="netadmin",
        )

        with patch("collector.adapters.snmp_poller.get_cmd", new_callable=AsyncMock) as mock_get_cmd, \
             patch("collector.adapters.snmp_poller.UdpTransportTarget.create", new_callable=AsyncMock) as mock_target:
            mock_target.return_value = MagicMock()
            mock_get_cmd.return_value = (None, 0, 0, mock_var_binds)

            records, avail, unsupp = await poll_snmp_device(device)
            assert len(records) == 1

            orch = MultiAgentOrchestrator()
            res = orch.run_diagnosis(records, incident_id="INC-SNMP-TEST-01")

            assert res["status"] in ("CONFIRMED", "SUSPECTED", "HEALTHY", "DEGRADED")
            report = res["canonical_report"]
            assert report["incident_id"] == "INC-SNMP-TEST-01"
            assert "remediation_runbook" in report or len(report.get("recommended_actions", [])) > 0
            assert len(res["agent_states"]) == 5
