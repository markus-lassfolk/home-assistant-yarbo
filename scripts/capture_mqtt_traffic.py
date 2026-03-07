#!/usr/bin/env python3
"""
Record raw MQTT traffic to a JSONL file for analysis.

Connects to the broker, subscribes to device topics, and optionally sends
get_device_msg every 10s to trigger data_feedback. Every received message
is appended to the log file (topic + decoded payload per line).

Requires python-yarbo: uv sync --extra scripts  (or run from python-yarbo repo).

Usage:
  uv run --extra scripts python scripts/capture_mqtt_traffic.py --broker 192.168.1.55 --sn 24400102L8HO5227 --output /tmp/yarbo_capture.jsonl --duration 45
  python scripts/analyze_mqtt_capture.py /tmp/yarbo_capture.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import time

from yarbo.local import YarboLocalClient

# Publish to app topic to request device message; response arrives on data_feedback
TOPIC_LEAF_GET_DEVICE_MSG = "get_device_msg"


async def run_capture(
    broker: str,
    sn: str,
    output_path: str,
    duration_sec: float,
    poll_interval: float,
) -> None:
    print(f"Connecting to {broker} (sn={sn}) ...")
    print(f"Recording ALL MQTT traffic to {output_path}")
    print(f"Duration {duration_sec:.0f}s, get_device_msg every {poll_interval:.0f}s\n")

    client = YarboLocalClient(broker=broker, sn=sn, mqtt_log_path=output_path)
    await client.connect()

    t0 = time.monotonic()
    sent = 0
    while time.monotonic() - t0 < duration_sec:
        await client._transport.publish(TOPIC_LEAF_GET_DEVICE_MSG, {})
        sent += 1
        print(f"   T+{time.monotonic()-t0:.0f}s  get_device_msg #{sent}  (responses written to log)")
        await asyncio.sleep(poll_interval)

    await client.disconnect()
    print(f"\nDone. Recorded to {output_path}. Run: python scripts/analyze_mqtt_capture.py {output_path}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Record raw MQTT traffic to JSONL for payload analysis"
    )
    ap.add_argument("--broker", default="192.168.1.55", help="Broker IP")
    ap.add_argument("--sn", required=True, help="Robot serial number")
    ap.add_argument("--output", "-o", default="/tmp/yarbo_mqtt_capture.jsonl", help="Output JSONL path")
    ap.add_argument("--duration", type=float, default=45.0, help="Capture duration (default 45s)")
    ap.add_argument("--poll-interval", type=float, default=10.0, help="get_device_msg interval (default 10s)")
    args = ap.parse_args()
    asyncio.run(run_capture(args.broker, args.sn, args.output, args.duration, args.poll_interval))


if __name__ == "__main__":
    main()
