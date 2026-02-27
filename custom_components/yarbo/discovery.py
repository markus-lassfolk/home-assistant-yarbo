"""Discover Yarbo MQTT endpoints via python-yarbo (Rover vs DC).

This module only delegates to the python-yarbo library. All discovery logic,
Rover/DC classification, and broker verification live in the library.
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
            results = await yarbo_discover(port=port)
        else:
            results = await asyncio.to_thread(yarbo_discover, port=port)
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
