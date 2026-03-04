"""Discover Yarbo MQTT endpoints (Rover vs DC).

This module attempts to discover Yarbo MQTT brokers using the python-yarbo
library's discover() API when available. When the library provides no discovery,
it falls back to scanning the local ARP table via 'ip neigh' and probing each
host for an MQTT broker on the configured port. This approach is MAC-agnostic
and works with any Yarbo hardware revision regardless of WiFi chipset vendor.

Discovered hosts are normalized to YarboEndpoint objects with colon-delimited
MACs and a canonical endpoint_type. If discovery yields no results, a seed_host
(e.g. from DHCP) is used as a single fallback endpoint so the config flow can
still proceed.

See: https://github.com/markus-lassfolk/home-assistant-yarbo/issues/50
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from .const import (
    DEFAULT_BROKER_PORT,
    ENDPOINT_TYPE_DC,
    ENDPOINT_TYPE_ROVER,
    ENDPOINT_TYPE_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)

# Timeout for each MQTT port probe (seconds).
# Connection-refused is instant; only unreachable hosts hit the timeout.
_PROBE_TIMEOUT = 1.5

# Maximum number of parallel probes to avoid flooding the network.
_MAX_CONCURRENT_PROBES = 30


@dataclass
class YarboEndpoint:
    """One MQTT endpoint from python-yarbo discovery (for config flow UI)."""

    host: str
    port: int
    mac: str | None = None
    endpoint_type: str = ENDPOINT_TYPE_UNKNOWN
    recommended: bool = False

    @property
    def label(self) -> str:
        if self.endpoint_type == ENDPOINT_TYPE_DC:
            return "Data Center (LAN → HaLow)"
        if self.endpoint_type == ENDPOINT_TYPE_ROVER:
            return "Rover (direct WiFi)"
        return "MQTT endpoint"


def _normalize_endpoint_type(raw_type: object) -> str:
    """Normalize the endpoint type string from the library to a canonical value."""
    if not raw_type:
        return ENDPOINT_TYPE_UNKNOWN
    t = str(raw_type).lower().strip()
    if t in ("dc", "data_center", "datacenter"):
        return ENDPOINT_TYPE_DC
    if t in ("rover", "direct", "wifi"):
        return ENDPOINT_TYPE_ROVER
    return ENDPOINT_TYPE_UNKNOWN


def _from_library_result(r: object, port: int) -> YarboEndpoint | None:
    """Map a single result from python-yarbo discover() to YarboEndpoint."""
    if isinstance(r, dict):
        h = r.get("host") or r.get("ip")
        p = r.get("port", port)
        mac = r.get("mac")
        raw_type = r.get("type") or r.get("endpoint_type")
        rec = bool(r.get("recommended", False))
    else:
        h = getattr(r, "host", None) or getattr(r, "ip", None)
        p = getattr(r, "port", port)
        mac = getattr(r, "mac", None)
        raw_type = getattr(r, "type", None) or getattr(r, "endpoint_type", None)
        rec = bool(getattr(r, "recommended", False))
    if not h:
        return None
    endpoint_type = _normalize_endpoint_type(raw_type)
    return YarboEndpoint(
        host=str(h),
        port=int(p),
        mac=str(mac) if mac else None,
        endpoint_type=endpoint_type,
        recommended=rec,
    )


async def _probe_mqtt(host: str, port: int) -> bool:
    """Try to open a TCP connection to host:port.

    Returns True if the port is open (MQTT broker likely running).
    Fails fast on connection-refused; times out on unreachable hosts.
    """
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=_PROBE_TIMEOUT,
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (OSError, TimeoutError):
        return False


async def _discover_from_arp(port: int = DEFAULT_BROKER_PORT) -> list[YarboEndpoint]:
    """Scan the ARP table and probe each neighbour for an MQTT broker.

    Reads 'ip neigh' to get all known hosts on the local network, then
    probes each one in parallel for an open MQTT port. No MAC filtering —
    works with any Yarbo hardware revision regardless of chipset vendor.
    """
    # Collect all ARP neighbours with their MACs
    neighbours: list[tuple[str, str]] = []  # (ip, mac)
    try:
        proc = await asyncio.create_subprocess_exec(
            "ip",
            "neigh",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        for line in stdout.decode(errors="replace").splitlines():
            parts = line.split()
            if len(parts) >= 5 and "lladdr" in parts:
                ip = parts[0]
                mac_idx = parts.index("lladdr") + 1
                if mac_idx < len(parts):
                    mac = parts[mac_idx].lower()
                    neighbours.append((ip, mac))
    except (FileNotFoundError, TimeoutError, OSError) as err:
        _LOGGER.debug("ARP scan failed: %s", err)
        return []

    if not neighbours:
        return []

    _LOGGER.debug(
        "ARP discovery: probing %d neighbours for MQTT on port %d",
        len(neighbours),
        port,
    )

    # Probe all neighbours in parallel with concurrency limit
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_PROBES)

    async def _limited_probe(ip: str) -> bool:
        async with semaphore:
            return await _probe_mqtt(ip, port)

    results = await asyncio.gather(*[_limited_probe(ip) for ip, _mac in neighbours])

    endpoints: list[YarboEndpoint] = []
    for (ip, mac), is_open in zip(neighbours, results, strict=True):
        if is_open:
            _LOGGER.debug("ARP discovery: found MQTT broker at %s (MAC %s)", ip, mac)
            endpoints.append(
                YarboEndpoint(
                    host=ip,
                    port=port,
                    mac=mac,
                    endpoint_type=ENDPOINT_TYPE_UNKNOWN,
                    recommended=False,
                )
            )

    return endpoints


async def async_discover_endpoints(
    seed_host: str | None = None,
    seed_mac: str | None = None,
    port: int = DEFAULT_BROKER_PORT,
) -> list[YarboEndpoint]:
    """Discover endpoints using python-yarbo only.

    Calls the library's discover API (sync or async). If the library has no
    discovery or returns nothing, returns a single endpoint from seed_host
    so the config flow can still proceed (type/recommended left default).
    """
    # Prefer async discover if the library exposes it
    try:
        from yarbo import discover as yarbo_discover
    except ImportError:
        yarbo_discover = None

    if yarbo_discover is None:
        # Library has no discover() yet — fall back to ARP + MQTT probe
        endpoints = await _discover_from_arp(port)
        if endpoints:
            return endpoints
        if seed_host:
            return [
                YarboEndpoint(
                    host=seed_host,
                    port=port,
                    mac=seed_mac,
                    endpoint_type=ENDPOINT_TYPE_UNKNOWN,
                    recommended=False,
                )
            ]
        return []

    try:
        # Library may expose sync or async discover
        if asyncio.iscoroutinefunction(yarbo_discover):
            results = await asyncio.wait_for(yarbo_discover(port=port), timeout=10.0)
        else:
            results = await asyncio.wait_for(
                asyncio.to_thread(yarbo_discover, port=port), timeout=10.0
            )
    except Exception as err:
        _LOGGER.debug("yarbo.discover() failed: %s", err)
        results = []

    if not results:
        if seed_host:
            return [
                YarboEndpoint(
                    host=seed_host,
                    port=port,
                    mac=seed_mac,
                    endpoint_type=ENDPOINT_TYPE_UNKNOWN,
                    recommended=False,
                )
            ]
        return []

    out: list[YarboEndpoint] = []
    for r in results:
        ep = _from_library_result(r, port)
        if ep:
            out.append(ep)
    if out:
        return out
    if seed_host:
        return [
            YarboEndpoint(
                host=seed_host,
                port=port,
                mac=seed_mac,
                endpoint_type=ENDPOINT_TYPE_UNKNOWN,
                recommended=False,
            )
        ]
    return []
