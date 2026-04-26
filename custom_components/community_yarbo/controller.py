"""Controller role acquisition (``get_controller``) helpers."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from yarbo.exceptions import YarboTimeoutError

_LOGGER = logging.getLogger(__name__)

# Shown in the HA UI when the robot does not acknowledge controller acquisition (GlitchTip #147).
CONTROLLER_ACQUIRE_TIMEOUT_MSG = (
    "Timed out waiting for the robot to grant controller access. Close the Yarbo "
    "mobile app completely if it is open, ensure the robot is online, then try again."
)


async def async_ensure_controller(client: Any, *, timeout: float = 5.0) -> None:
    """Call the library ``get_controller``; map timeouts to ``HomeAssistantError``."""
    try:
        await client.get_controller(timeout=timeout)
    except YarboTimeoutError as err:
        _LOGGER.info("get_controller timed out after %.1fs: %s", timeout, err)
        raise HomeAssistantError(CONTROLLER_ACQUIRE_TIMEOUT_MSG) from err
