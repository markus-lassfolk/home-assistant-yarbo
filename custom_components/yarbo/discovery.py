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


def _from_library_result(r: object, port: int) -> YarboEndpoint | None:
    """Map a single result from python-yarbo discover() to YarboEndpoint."""
    if isinstance(r, dict):
        h = r.get("host") or r.get("ip")
        p = r.get("port", port)
        mac = r.get("mac")
        t = r.get("type") or r.get("endpoint_type") or ENDPOINT_TYPE_UNKNOWN
        rec = bool(r.get("recommended", (t or "").lower() in ("dc", "data_center")))
    else:
        h = getattr(r, "host", None) or getattr(r, "ip", None)
        p = getattr(r, "port", port)
        mac = getattr(r, "mac", None)
        t = getattr(r, "type", None) or getattr(r, "endpoint_type", None) or ENDPOINT_TYPE_UNKNOWN
        rec = getattr(r, "recommended", None)
        if rec is None:
            rec = (str(t).lower() if t else "") in ("dc", "data_center")
    if not h:
        return None
    return YarboEndpoint(
        host=str(h),
        port=int(p),
        mac=str(mac) if mac else None,
        endpoint_type=str(t) if t else ENDPOINT_TYPE_UNKNOWN,
        recommended=bool(rec),
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
    return out if out else (
        [YarboEndpoint(host=seed_host, port=port, mac=seed_mac, endpoint_type=ENDPOINT_TYPE_UNKNOWN, recommended=False)]
        if seed_host else []
    )
