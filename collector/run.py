"""
CLI Entry Point for NetCoop AI Local Network Collector.
Usage:
    python -m collector.run --backend http://127.0.0.1:8000 --token nc_coll_xxx
    python collector/run.py --backend https://your-backend.onrender.com --token nc_coll_xxx
"""

import sys
import os
import argparse
import asyncio
import signal
import logging

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from collector.config import (
    load_collector_config,
    save_collector_config,
    CollectorSettings,
    LocalDeviceConfig,
    DeviceProtocol,
)
from collector.agent import NetworkCollectorAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("NetCoopCollector")


def parse_args():
    parser = argparse.ArgumentParser(
        description="NetCoop AI Local Network Collector Agent — Secure Outbound Telemetry Streamer"
    )
    parser.add_argument("--backend", type=str, default=None, help="Backend API URL (e.g. http://127.0.0.1:8000)")
    parser.add_argument("--token", type=str, default=None, help="Enrollment token generated in NOC Dashboard")
    parser.add_argument("--collector-id", type=str, default=None, help="Collector ID (if provided with token)")
    parser.add_argument("--name", type=str, default=None, help="Human-readable name for this collector")
    parser.add_argument("--syslog-port", type=int, default=5140, help="Local UDP syslog port (default 5140)")
    parser.add_argument("--config", type=str, default="collector_config.json", help="Path to local config file")
    return parser.parse_args()


async def main():
    args = parse_args()
    settings = load_collector_config()

    if args.backend:
        settings.backend_url = args.backend
    if args.token:
        settings.enrollment_token = args.token
    if args.collector_id:
        settings.collector_id = args.collector_id
    if args.name:
        settings.collector_name = args.name
    if args.syslog_port:
        settings.syslog_port = args.syslog_port

    # If no devices configured, seed a default local gateway reachability probe
    if not settings.devices:
        default_device = LocalDeviceConfig(
            device_id="LAN-Gateway-01",
            name="Default Local Gateway",
            device_type="router",
            host="127.0.0.1",
            protocol=DeviceProtocol.TCP_PROBE,
            port=80,
            polling_interval_sec=15,
        )
        settings.devices.append(default_device)

    save_collector_config(settings)

    print("==================================================================")
    print("   NetCoop AI — Local Network Collector Agent v1.0.0             ")
    print("==================================================================")
    print(f"  Backend URL    : {settings.backend_url}")
    print(f"  Collector Name : {settings.collector_name}")
    print(f"  Syslog Listener: UDP port {settings.syslog_port}")
    print(f"  Devices Monitored: {len(settings.devices)}")
    for d in settings.devices:
        print(f"    - [{d.protocol}] {d.device_id} ({d.host}:{d.port})")
    print("==================================================================")
    print("Press Ctrl+C to terminate collector gracefully.\n")

    agent = NetworkCollectorAgent(settings)
    loop = asyncio.get_event_loop()

    # Handle graceful exit
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Signal received. Stopping collector...")
        stop_event.set()

    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

    await agent.start()

    try:
        if sys.platform == "win32":
            # On Windows loop.run_forever or sleep loop
            while not stop_event.is_set():
                await asyncio.sleep(1)
        else:
            await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await agent.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCollector terminated.")

