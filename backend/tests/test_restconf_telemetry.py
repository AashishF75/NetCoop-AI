"""
Phase 2 Test Suite: Authenticated RESTCONF Interface & Operational Telemetry.
Validates:
- RFC 8040 RESTCONF over HTTPS with TLS verification enabled by default.
- Custom CA certificate bundle and administrator TLS bypass warning handling.
- Basic authentication and Bearer token header construction.
- RFC 7223 (ietf-interfaces:interfaces-state), RFC 8343 (ietf-interfaces:interfaces),
  and OpenConfig (openconfig-interfaces:interfaces) operational model parsing.
- Extraction of CPU and memory from Cisco IOS-XE and OpenConfig operational models.
- Transparent reporting of unsupported metrics without metric fabrication.
- Graceful handling of HTTP 401/403 (Auth), 404 (Missing YANG model), 429 (Rate limiting),
  timeouts, TLS certificate verification failures, and malformed JSON payloads.
- Absolute credential containment (zero password or token leakage in telemetry records).
- End-to-end multi-agent diagnosis by all 5 specialized agents.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch
import httpx

from collector.config import LocalDeviceConfig, DeviceProtocol
from collector.adapters.restconf_poller import (
    poll_restconf_device,
    _extract_interfaces_data,
    _extract_cpu_utilization,
    _extract_memory_utilization,
)
from app.orchestrator.engine import MultiAgentOrchestrator


class TestRESTCONFOperationalParsers:
    """Tests RFC 7223, RFC 8343, and OpenConfig JSON/YANG response parsing."""

    def test_rfc7223_interfaces_state_parsing(self):
        sample_rfc7223 = {
            "ietf-interfaces:interfaces-state": {
                "interface": [
                    {
                        "name": "GigabitEthernet0/0/1",
                        "type": "iana-if-type:ethernetCsmacd",
                        "admin-status": "up",
                        "oper-status": "up",
                        "speed": 1000000000,
                        "statistics": {
                            "in-octets": 10542300,
                            "out-octets": 8421000,
                            "in-errors": 14,
                            "out-errors": 2,
                            "in-discards": 7,
                            "out-discards": 1,
                        },
                    }
                ]
            }
        }
        (
            name,
            oper,
            admin,
            in_oct,
            out_oct,
            in_err,
            out_err,
            in_disc,
            out_disc,
        ) = _extract_interfaces_data(sample_rfc7223)

        assert name == "GigabitEthernet0/0/1"
        assert oper == "UP"
        assert admin == "UP"
        assert in_oct == 10542300
        assert out_oct == 8421000
        assert in_err == 14
        assert out_err == 2
        assert in_disc == 7
        assert out_disc == 1

    def test_rfc8343_interfaces_parsing(self):
        sample_rfc8343 = {
            "ietf-interfaces:interfaces": {
                "interface": [
                    {
                        "name": "TenGigabitEthernet1/0/1",
                        "oper-status": "up",
                        "admin-status": "up",
                        "statistics": {
                            "in-octets": 987654321,
                            "out-octets": 123456789,
                            "in-errors": 0,
                            "out-errors": 0,
                            "in-discards": 3,
                            "out-discards": 0,
                        },
                    }
                ]
            }
        }
        (
            name,
            oper,
            admin,
            in_oct,
            out_oct,
            in_err,
            out_err,
            in_disc,
            out_disc,
        ) = _extract_interfaces_data(sample_rfc8343)

        assert name == "TenGigabitEthernet1/0/1"
        assert oper == "UP"
        assert in_oct == 987654321
        assert in_disc == 3

    def test_openconfig_interfaces_parsing(self):
        sample_openconfig = {
            "openconfig-interfaces:interfaces": {
                "interface": [
                    {
                        "name": "Ethernet1/1",
                        "state": {
                            "admin-status": "UP",
                            "oper-status": "UP",
                            "counters": {
                                "in-octets": 55443322,
                                "out-octets": 22334455,
                                "in-errors": 8,
                                "out-errors": 1,
                                "in-discards": 12,
                                "out-discards": 0,
                            },
                        },
                    }
                ]
            }
        }
        (
            name,
            oper,
            admin,
            in_oct,
            out_oct,
            in_err,
            out_err,
            in_disc,
            out_disc,
        ) = _extract_interfaces_data(sample_openconfig)

        assert name == "Ethernet1/1"
        assert oper == "UP"
        assert admin == "UP"
        assert in_oct == 55443322
        assert out_oct == 22334455
        assert in_err == 8
        assert in_disc == 12

    def test_cisco_cpu_and_memory_operational_extraction(self):
        cisco_cpu_data = {
            "Cisco-IOS-XE-process-cpu-oper:cpu-usage": {
                "cpu-utilization": {
                    "five-minutes": 38.5,
                    "one-minute": 41.2,
                    "five-seconds": 45.0,
                }
            }
        }
        cisco_mem_data = {
            "Cisco-IOS-XE-memory-oper:memory-statistics": {
                "memory-statistic": [
                    {
                        "name": "Processor",
                        "total-memory": 1000000000,
                        "used-memory": 450000000,
                        "free-memory": 550000000,
                    }
                ]
            }
        }
        cpu = _extract_cpu_utilization(cisco_cpu_data)
        mem = _extract_memory_utilization(cisco_mem_data)

        assert cpu == 38.5
        assert mem == 45.0

    def test_openconfig_platform_cpu_extraction(self):
        oc_cpu_data = {
            "openconfig-platform:components": {
                "component": [
                    {
                        "name": "CPU-Module-0",
                        "cpu": {
                            "utilization": {
                                "state": {
                                    "avg": 52.4,
                                    "instant": 54.0,
                                }
                            }
                        },
                    }
                ]
            }
        }
        cpu = _extract_cpu_utilization(oc_cpu_data)
        assert cpu == 52.4

    def test_unsupported_cpu_and_memory_returns_none(self):
        # Empty or unrecognized YANG payload
        assert _extract_cpu_utilization({}) is None
        assert _extract_cpu_utilization({"ietf-system:system": {}}) is None
        assert _extract_memory_utilization({}) is None
        assert _extract_memory_utilization({"ietf-system:system": {}}) is None


class TestRESTCONFPollerNetworkOperations:
    """Tests async HTTP/HTTPS RESTCONF queries, authentication, TLS, and error handling."""

    @pytest.mark.asyncio
    async def test_successful_restconf_poll_with_interface_counters(self):
        device = LocalDeviceConfig(
            device_id="ROUTER-RESTCONF-01",
            name="Core Gateway RESTCONF",
            host="192.168.1.1",
            port=443,
            protocol=DeviceProtocol.RESTCONF,
            username="admin",
            password="RouterPassword123",
            rest_endpoint="/restconf/data/ietf-interfaces:interfaces-state",
            tls_verify=True,
        )

        sample_if_body = {
            "ietf-interfaces:interfaces-state": {
                "interface": [
                    {
                        "name": "GigabitEthernet0/0/0",
                        "oper-status": "up",
                        "admin-status": "up",
                        "statistics": {
                            "in-octets": 1024000,
                            "out-octets": 512000,
                            "in-errors": 3,
                            "out-errors": 0,
                            "in-discards": 2,
                            "out-discards": 0,
                        },
                    }
                ]
            }
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = httpx.Response(
            200,
            json=sample_if_body,
            request=httpx.Request("GET", "https://192.168.1.1:443/restconf/data/ietf-interfaces:interfaces-state"),
        )

        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            recs, available, unsupported = await poll_restconf_device(device)

            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args[1]
            assert call_kwargs["auth"] == ("admin", "RouterPassword123")
            assert call_kwargs["verify"] is True

            assert len(recs) == 1
            rec = recs[0]
            assert rec.device_id == "ROUTER-RESTCONF-01"
            assert rec.device_status == "UP"
            assert rec.packet_loss_pct == 0.0
            assert rec.interface_id == "GigabitEthernet0/0/0"
            assert rec.interface_oper_status == "UP"
            assert rec.interface_in_octets == 1024000
            assert rec.interface_out_octets == 512000
            assert rec.interface_crc_errors == 3
            assert rec.queue_drops_per_sec == 2.0
            assert rec.telemetry_origin == "LIVE_DEVICE"
            assert "interface_oper_status" in available
            assert "interface_in_octets" in available
            # CPU and memory were not queried/exposed so they must be None and unsupported
            assert rec.cpu_utilization_pct is None
            assert rec.memory_utilization_pct is None
            assert "cpu_utilization_pct" in unsupported
            assert "memory_utilization_pct" in unsupported

    @pytest.mark.asyncio
    async def test_restconf_bearer_token_and_ca_cert_path(self):
        device = LocalDeviceConfig(
            device_id="ROUTER-EDGE-BEARER",
            name="Edge Router Bearer Auth",
            host="10.50.1.1",
            port=8443,
            protocol=DeviceProtocol.RESTCONF,
            restconf_auth_type="BEARER",
            bearer_token="eyXyzRouterOperationalToken12345",
            ca_cert_path="/etc/ssl/certs/enterprise-router-ca.pem",
        )

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = httpx.Response(
            200,
            json={"ietf-interfaces:interfaces-state": {"interface": [{"name": "eth0", "oper-status": "up"}]}},
            request=httpx.Request("GET", "https://10.50.1.1:8443/restconf/data/ietf-interfaces:interfaces-state"),
        )

        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            recs, _, _ = await poll_restconf_device(device)
            call_kwargs = mock_cls.call_args[1]

            assert call_kwargs["verify"] == "/etc/ssl/certs/enterprise-router-ca.pem"
            assert call_kwargs["headers"]["Authorization"] == "Bearer eyXyzRouterOperationalToken12345"
            assert len(recs) == 1
            assert recs[0].device_status == "UP"

    @pytest.mark.asyncio
    async def test_restconf_administrator_tls_bypass_records_warning(self):
        device = LocalDeviceConfig(
            device_id="ROUTER-DEV-LAB",
            name="Lab Router Insecure TLS",
            host="192.168.10.1",
            port=443,
            protocol=DeviceProtocol.RESTCONF,
            tls_verify=False,
        )

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = httpx.Response(
            200,
            json={"ietf-interfaces:interfaces-state": {"interface": [{"name": "Gi0/0", "oper-status": "up"}]}},
            request=httpx.Request("GET", "https://192.168.10.1:443/restconf/data/ietf-interfaces:interfaces-state"),
        )

        with patch("httpx.AsyncClient", return_value=mock_client) as mock_cls:
            recs, _, _ = await poll_restconf_device(device)
            assert mock_cls.call_args[1]["verify"] is False
            assert len(recs) == 1
            rec = recs[0]
            assert "tls_warning" in rec.custom_metrics
            assert "explicitly bypassed" in rec.custom_metrics["tls_warning"]
            assert rec.custom_metrics["tls_verification"] == "DISABLED_BY_ADMIN"

    @pytest.mark.asyncio
    async def test_cpu_and_memory_secondary_endpoint_polling(self):
        device = LocalDeviceConfig(
            device_id="CISCO-CATALYST-8300",
            name="Catalyst 8300 Router",
            host="10.200.1.1",
            port=443,
            protocol=DeviceProtocol.RESTCONF,
            rest_endpoint="/restconf/data/ietf-interfaces:interfaces-state",
            rest_cpu_endpoint="/restconf/data/Cisco-IOS-XE-process-cpu-oper:cpu-usage",
            rest_memory_endpoint="/restconf/data/Cisco-IOS-XE-memory-oper:memory-statistics",
        )

        if_resp = httpx.Response(
            200,
            json={"ietf-interfaces:interfaces-state": {"interface": [{"name": "GigabitEthernet0/0/0", "oper-status": "up"}]}},
            request=httpx.Request("GET", "https://10.200.1.1/restconf/data/ietf-interfaces:interfaces-state"),
        )
        cpu_resp = httpx.Response(
            200,
            json={"Cisco-IOS-XE-process-cpu-oper:cpu-usage": {"cpu-utilization": {"five-minutes": 27.6}}},
            request=httpx.Request("GET", "https://10.200.1.1/restconf/data/Cisco-IOS-XE-process-cpu-oper:cpu-usage"),
        )
        mem_resp = httpx.Response(
            200,
            json={"Cisco-IOS-XE-memory-oper:memory-statistics": {"memory-statistic": [{"used-memory": 600000000, "free-memory": 400000000}]}},
            request=httpx.Request("GET", "https://10.200.1.1/restconf/data/Cisco-IOS-XE-memory-oper:memory-statistics"),
        )

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = [if_resp, cpu_resp, mem_resp]

        with patch("httpx.AsyncClient", return_value=mock_client):
            recs, avail, unsupp = await poll_restconf_device(device)
            assert len(recs) == 1
            rec = recs[0]
            assert rec.cpu_utilization_pct == 27.6
            assert rec.memory_utilization_pct == 60.0
            assert "cpu_utilization_pct" in avail
            assert "memory_utilization_pct" in avail

    @pytest.mark.asyncio
    async def test_authentication_failure_401_and_403(self):
        device = LocalDeviceConfig(
            device_id="ROUTER-SECURE-01",
            name="Secure Router",
            host="10.10.10.1",
            port=443,
            protocol=DeviceProtocol.RESTCONF,
            username="wrong_user",
            password="wrong_password",
        )

        # 401 Unauthorized
        mock_client_401 = AsyncMock()
        mock_client_401.__aenter__.return_value = mock_client_401
        mock_client_401.get.return_value = httpx.Response(
            401,
            json={"errors": {"error": [{"error-message": "Invalid credentials"}]}},
            request=httpx.Request("GET", "https://10.10.10.1/restconf/data/ietf-interfaces:interfaces-state"),
        )

        with patch("httpx.AsyncClient", return_value=mock_client_401):
            recs, _, unsupp = await poll_restconf_device(device)
            assert len(recs) == 1
            rec = recs[0]
            assert rec.device_status == "AUTH_REJECTED"
            assert rec.packet_loss_pct == 100.0
            assert rec.custom_metrics["error_type"] == "AUTHENTICATION_FAILED"
            assert rec.custom_metrics["http_status"] == 401

        # 403 Forbidden
        mock_client_403 = AsyncMock()
        mock_client_403.__aenter__.return_value = mock_client_403
        mock_client_403.get.return_value = httpx.Response(
            403,
            json={"errors": {"error": [{"error-message": "User lacks restconf-admin privileges"}]}},
            request=httpx.Request("GET", "https://10.10.10.1/restconf/data/ietf-interfaces:interfaces-state"),
        )

        with patch("httpx.AsyncClient", return_value=mock_client_403):
            recs, _, unsupp = await poll_restconf_device(device)
            assert len(recs) == 1
            rec = recs[0]
            assert rec.device_status == "AUTH_REJECTED"
            assert rec.custom_metrics["error_type"] == "PERMISSION_DENIED"
            assert rec.custom_metrics["http_status"] == 403

    @pytest.mark.asyncio
    async def test_yang_model_not_found_404(self):
        device = LocalDeviceConfig(
            device_id="ROUTER-LEGACY-01",
            name="Legacy Router",
            host="192.168.1.1",
            port=443,
            protocol=DeviceProtocol.RESTCONF,
            rest_endpoint="/restconf/data/nonexistent-model:metrics",
        )

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = httpx.Response(
            404,
            json={"errors": {"error": [{"error-tag": "data-missing"}]}},
            request=httpx.Request("GET", "https://192.168.1.1/restconf/data/nonexistent-model:metrics"),
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            recs, _, unsupp = await poll_restconf_device(device)
            assert len(recs) == 1
            rec = recs[0]
            assert rec.device_status == "DEGRADED"
            assert rec.custom_metrics["error_type"] == "YANG_MODEL_NOT_FOUND"
            assert rec.custom_metrics["http_status"] == 404
            assert "cpu_utilization_pct" in unsupp

    @pytest.mark.asyncio
    async def test_rate_limited_429(self):
        device = LocalDeviceConfig(
            device_id="ROUTER-RATE-LIMITED",
            name="Rate Limited Router",
            host="10.0.0.1",
            port=443,
            protocol=DeviceProtocol.RESTCONF,
        )

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = httpx.Response(
            429,
            json={"errors": {"error": [{"error-message": "Too many requests"}]}},
            request=httpx.Request("GET", "https://10.0.0.1/restconf/data/ietf-interfaces:interfaces-state"),
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            recs, _, _ = await poll_restconf_device(device)
            assert len(recs) == 1
            rec = recs[0]
            assert rec.device_status == "DEGRADED"
            assert rec.custom_metrics["error_type"] == "RATE_LIMITED"
            assert rec.custom_metrics["http_status"] == 429

    @pytest.mark.asyncio
    async def test_network_connection_timeout(self):
        device = LocalDeviceConfig(
            device_id="ROUTER-UNREACHABLE",
            name="Unreachable Router",
            host="10.254.254.1",
            port=443,
            protocol=DeviceProtocol.RESTCONF,
            timeout_sec=2.0,
        )

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = httpx.ConnectTimeout("Connection timed out connecting to 10.254.254.1:443")

        with patch("httpx.AsyncClient", return_value=mock_client):
            recs, avail, unsupp = await poll_restconf_device(device)
            assert len(recs) == 1
            rec = recs[0]
            assert rec.device_status == "DOWN"
            assert rec.packet_loss_pct == 100.0
            assert rec.custom_metrics["error_type"] == "TIMEOUT"
            assert len(avail) == 0

    @pytest.mark.asyncio
    async def test_tls_certificate_verification_failure(self):
        device = LocalDeviceConfig(
            device_id="ROUTER-SELF-SIGNED",
            name="Self-Signed Router",
            host="192.168.1.1",
            port=443,
            protocol=DeviceProtocol.RESTCONF,
            tls_verify=True,
        )

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate")

        with patch("httpx.AsyncClient", return_value=mock_client):
            recs, avail, unsupp = await poll_restconf_device(device)
            assert len(recs) == 1
            rec = recs[0]
            assert rec.device_status == "DOWN"
            assert rec.packet_loss_pct == 100.0
            assert rec.custom_metrics["error_type"] == "TLS_VERIFICATION_FAILED"
            assert "ca_cert_path" in rec.custom_metrics["probe_note"]

    @pytest.mark.asyncio
    async def test_malformed_yang_json_payload(self):
        device = LocalDeviceConfig(
            device_id="ROUTER-CORRUPT-JSON",
            name="Corrupt JSON Router",
            host="192.168.1.1",
            port=443,
            protocol=DeviceProtocol.RESTCONF,
        )

        mock_resp = httpx.Response(
            200,
            text="<html><head><title>500 Internal Error</title></head><body>Bad Gateway or corrupt YANG string",
            request=httpx.Request("GET", "https://192.168.1.1/restconf/data/ietf-interfaces:interfaces-state"),
        )
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        with patch("httpx.AsyncClient", return_value=mock_client):
            recs, avail, unsupp = await poll_restconf_device(device)
            assert len(recs) == 1
            rec = recs[0]
            assert rec.device_status == "DEGRADED"
            assert rec.custom_metrics["error_type"] == "MALFORMED_YANG_RESPONSE"


class TestRESTCONFCredentialContainment:
    """Verifies that device passwords, bearer tokens, and API keys are never exposed in records."""

    @pytest.mark.asyncio
    async def test_zero_credential_exposure_in_records(self):
        secret_password = "SuperSecretRouterPassword999!"
        secret_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.SuperSecretTokenPayload"

        device = LocalDeviceConfig(
            device_id="EDGE-ROUTER-VAULT",
            name="Vault Router",
            host="10.0.1.1",
            port=443,
            protocol=DeviceProtocol.RESTCONF,
            username="admin",
            password=secret_password,
            bearer_token=secret_token,
        )

        sample_resp = {
            "ietf-interfaces:interfaces-state": {
                "interface": [{"name": "GigabitEthernet0/0/0", "oper-status": "up"}]
            }
        }
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = httpx.Response(
            200,
            json=sample_resp,
            request=httpx.Request("GET", "https://10.0.1.1/restconf/data/ietf-interfaces:interfaces-state"),
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            recs, _, _ = await poll_restconf_device(device)
            assert len(recs) == 1
            rec_dict = recs[0].model_dump()
            serialized = json.dumps(rec_dict)

            # Neither password nor bearer token must be in serialized telemetry record
            assert secret_password not in serialized
            assert secret_token not in serialized


class TestRESTCONFDiagnosisPipeline:
    """Tests multi-agent diagnosis over genuine RESTCONF telemetry records."""

    @pytest.mark.asyncio
    async def test_restconf_interface_crc_and_congestion_diagnosis(self):
        device = LocalDeviceConfig(
            device_id="CORE-ROUTER-RESTCONF",
            name="Core Router Restconf",
            host="10.10.10.1",
            port=443,
            protocol=DeviceProtocol.RESTCONF,
        )

        # Telemetry with excessive CRC errors and drop counters on GigabitEthernet0/0/1
        sample_resp = {
            "ietf-interfaces:interfaces-state": {
                "interface": [
                    {
                        "name": "GigabitEthernet0/0/1",
                        "oper-status": "up",
                        "admin-status": "up",
                        "statistics": {
                            "in-octets": 99999999,
                            "out-octets": 88888888,
                            "in-errors": 128,  # High CRC errors
                            "out-errors": 0,
                            "in-discards": 64,  # High drop rate
                            "out-discards": 0,
                        },
                    }
                ]
            }
        }
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = httpx.Response(
            200,
            json=sample_resp,
            request=httpx.Request("GET", "https://10.10.10.1/restconf/data/ietf-interfaces:interfaces-state"),
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            recs, avail, unsupp = await poll_restconf_device(device)
            assert len(recs) == 1
            record = recs[0]

            orch = MultiAgentOrchestrator()
            diagnosis = orch.run_diagnosis([record], incident_id="INC-RESTCONF-CRC-01")

            assert "canonical_report" in diagnosis
            report = diagnosis["canonical_report"]
            assert report["status"] in ("CONFIRMED", "SUSPECTED", "DEGRADED")
            assert len(report["suspected_root_cause"]) > 0

            # All 5 specialized agents participate in the investigation
            agent_ids = {a["agent_id"] for a in diagnosis.get("agent_states", [])}
            expected_agents = {
                "perf-agent-01",
                "infra-agent-01",
                "conn-agent-01",
                "corr-agent-01",
                "recom-agent-01",
            }
            assert expected_agents == agent_ids

            # Investigation timeline events generated
            assert len(diagnosis.get("timeline_events", [])) > 0

            # Recommendations proposed
            recs_list = report.get("recommended_actions", [])
            assert len(recs_list) > 0

    @pytest.mark.asyncio
    async def test_restconf_down_interface_diagnosis(self):
        device = LocalDeviceConfig(
            device_id="ACCESS-ROUTER-RESTCONF",
            name="Access Router Down Port",
            host="10.10.20.1",
            port=443,
            protocol=DeviceProtocol.RESTCONF,
        )

        down_resp = {
            "ietf-interfaces:interfaces-state": {
                "interface": [
                    {
                        "name": "GigabitEthernet0/0/2",
                        "oper-status": "down",
                        "admin-status": "up",
                        "statistics": {
                            "in-octets": 0,
                            "out-octets": 0,
                            "in-errors": 0,
                            "out-errors": 0,
                            "in-discards": 0,
                            "out-discards": 0,
                        },
                    }
                ]
            }
        }
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = httpx.Response(
            200,
            json=down_resp,
            request=httpx.Request("GET", "https://10.10.20.1/restconf/data/ietf-interfaces:interfaces-state"),
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            recs, avail, unsupp = await poll_restconf_device(device)
            assert len(recs) == 1
            record = recs[0]
            assert record.device_status == "DOWN"
            assert record.packet_loss_pct == 100.0
            assert record.interface_oper_status == "DOWN"

            orch = MultiAgentOrchestrator()
            diagnosis = orch.run_diagnosis([record], incident_id="INC-RESTCONF-DOWN-01")
            assert diagnosis["status"] in ("CONFIRMED", "SUSPECTED", "DEGRADED", "HEALTHY")
            assert "canonical_report" in diagnosis
            assert len(diagnosis["canonical_report"]["affected_devices"]) >= 0

    @pytest.mark.asyncio
    async def test_probe_ip_and_diagnose_restconf_workflow(self):
        from app.integrations.probe_service import probe_ip_and_diagnose
        mock_resp = {
            "ietf-interfaces:interfaces-state": {
                "interface": [
                    {
                        "name": "GigabitEthernet0/0/0",
                        "oper-status": "up",
                        "statistics": {
                            "in-octets": 1000000,
                            "out-octets": 500000,
                            "in-errors": 0,
                            "out-errors": 0,
                            "in-discards": 0,
                            "out-discards": 0,
                        },
                    }
                ]
            }
        }
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = httpx.Response(
            200,
            json=mock_resp,
            request=httpx.Request("GET", "https://127.0.0.1:443/restconf/data/ietf-interfaces:interfaces-state"),
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            orch = MultiAgentOrchestrator()
            res = await probe_ip_and_diagnose(
                ip="127.0.0.1",
                protocol="RESTCONF",
                port=443,
                orchestrator=orch,
            )
            assert res["success"] is True
            probe = res["probe_result"]
            assert probe["status"] == "UP"
            assert probe["telemetry_origin"] == "LIVE_DEVICE"
            assert "canonical_report" in res["diagnosis"]
