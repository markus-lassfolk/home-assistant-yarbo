#!/usr/bin/env python3
"""
Analyze a MQTT capture JSONL file and report payload shapes.

Use this after capture_mqtt_traffic.py to see the exact structure of
data_feedback (and other) payloads so we can handle real traffic instead of guessing.

Usage:
  python scripts/analyze_mqtt_capture.py /tmp/yarbo_mqtt_capture.jsonl
  python scripts/analyze_mqtt_capture.py /tmp/yarbo_mqtt_capture.jsonl --data-feedback-only
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict


def leaf(topic: str) -> str:
    return topic.split("/")[-1] if "/" in topic else topic


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Analyze MQTT capture JSONL and report payload shapes"
    )
    ap.add_argument("log_file", help="Path to JSONL from capture_mqtt_traffic.py")
    ap.add_argument(
        "--data-feedback-only",
        action="store_true",
        help="Only print data_feedback payload analysis",
    )
    ap.add_argument(
        "--max-payloads",
        type=int,
        default=20,
        help="Max data_feedback payloads to show (default 20)",
    )
    args = ap.parse_args()

    counts: dict[str, int] = defaultdict(int)
    data_feedback_payloads: list[dict] = []
    data_feedback_top_keys: list[set[str]] = []

    with open(args.log_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Skip invalid JSON: {e}", file=sys.stderr)
                continue
            topic = rec.get("topic", "")
            payload = rec.get("payload", {})
            if not isinstance(payload, dict):
                payload = {}
            leaf_name = leaf(topic)
            counts[leaf_name] += 1

            if leaf_name == "data_feedback":
                data_feedback_payloads.append(payload)
                data_feedback_top_keys.append(set(payload.keys()))
                if len(data_feedback_payloads) >= args.max_payloads:
                    break

    print("=== Message counts by topic ===")
    for k in sorted(counts.keys()):
        print(f"  {k}: {counts[k]}")
    print()

    if not data_feedback_payloads:
        print("No data_feedback messages in capture. Run capture longer or check broker/sn.")
        return 1

    print("=== data_feedback payload analysis ===")
    print(
        f"Total data_feedback messages: {len(data_feedback_payloads)} (showing up to {args.max_payloads})\n"
    )

    # Union of all top-level keys seen
    all_top = set()
    for s in data_feedback_top_keys:
        all_top.update(s)
    print("Top-level keys seen in data_feedback payloads:")
    for k in sorted(all_top):
        print(f"  {k}")
    print()

    # Check for DeviceMSG-like content (BatteryMSG / StateMSG) at top level or under a wrapper
    device_msg_like: list[tuple[int, str, set[str]]] = []
    for i, p in enumerate(data_feedback_payloads):
        if p.get("BatteryMSG") is not None or p.get("StateMSG") is not None:
            device_msg_like.append((i, "top_level", set(p.keys())))
            continue
        for key in ("data", "result", "message", "body"):
            inner = p.get(key)
            if isinstance(inner, dict) and (
                inner.get("BatteryMSG") is not None or inner.get("StateMSG") is not None
            ):
                device_msg_like.append((i, key, set(inner.keys())))
                break
        else:
            device_msg_like.append((i, "??? (no BatteryMSG/StateMSG)", set(p.keys())))

    print("DeviceMSG-like content (BatteryMSG/StateMSG):")
    for i, path, keys in device_msg_like[:10]:
        klist = sorted(keys)[:15]
        suffix = "..." if len(keys) > 15 else ""
        print(f"  payload[{i}]: path={path!r}, keys={klist}{suffix}")
    if len(device_msg_like) > 10:
        print(f"  ... and {len(device_msg_like) - 10} more")
    print()

    # Show first data_feedback payload structure (one level deep)
    print("=== First data_feedback payload (structure) ===")
    p0 = data_feedback_payloads[0]
    for k, v in sorted(p0.items()):
        if isinstance(v, dict):
            sub_keys = list(v.keys())[:12]
            print(f"  {k}: dict with keys {sub_keys}{'...' if len(v) > 12 else ''}")
        else:
            print(f"  {k}: {type(v).__name__} = {repr(v)[:60]}")
    print()

    if args.data_feedback_only:
        return 0

    # DeviceMSG payloads if any
    device_msg_count = counts.get("DeviceMSG", 0)
    if device_msg_count:
        print("=== DeviceMSG count ===")
        print(f"  {device_msg_count} DeviceMSG messages in capture")
    return 0


if __name__ == "__main__":
    sys.exit(main())
