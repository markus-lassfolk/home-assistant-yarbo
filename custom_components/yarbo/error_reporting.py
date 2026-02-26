"""GlitchTip/Sentry error reporting for the Yarbo Home Assistant integration."""
from __future__ import annotations

import logging
import os

_LOGGER = logging.getLogger(__name__)

_DEFAULT_DSN = "http://c9d816d9a8714ac288e86b49c683b533@192.168.1.99:8000/4"


def init_error_reporting(
    dsn: str | None = None,
    environment: str = "production",
    enabled: bool = True,
    tags: dict[str, str] | None = None,
) -> None:
    """Initialize Sentry/GlitchTip error reporting for the Yarbo HA integration.

    Enabled by default (opt-out). To disable, set YARBO_SENTRY_DSN="" or pass enabled=False.

    Args:
        dsn: Sentry DSN. Defaults to the home-assistant-yarbo GlitchTip project.
             Set YARBO_SENTRY_DSN="" to explicitly disable.
        environment: Environment tag (production/development/testing).
        enabled: Master switch. If False, no SDK initialization occurs.
        tags: Optional extra tags (e.g. robot_serial, ha_version, integration_version).
    """
    if not enabled:
        return

    # Check for explicit disable via empty env var
    env_dsn = os.environ.get("YARBO_SENTRY_DSN")
    if env_dsn is not None and env_dsn == "":
        return  # Explicitly disabled

    effective_dsn = dsn or env_dsn or os.environ.get("SENTRY_DSN") or _DEFAULT_DSN

    if not effective_dsn:
        return

    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=effective_dsn,
            environment=environment,
            traces_sample_rate=0.1,
            send_default_pii=False,
            before_send=_scrub_event,
        )

        if tags:
            for key, value in tags.items():
                sentry_sdk.set_tag(key, value)

        _LOGGER.debug("Error reporting initialized (dsn=%s...)", effective_dsn[:30])
    except ImportError:
        _LOGGER.debug("sentry-sdk not installed; error reporting disabled")
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Failed to initialize error reporting: %s", exc)


def _scrub_event(event: dict, hint: dict) -> dict:  # type: ignore[type-arg]
    """Remove sensitive data before sending."""
    if "extra" in event:
        for key in list(event["extra"]):
            if any(s in key.lower() for s in ("password", "token", "secret", "credential", "key")):
                event["extra"][key] = "[REDACTED]"
    return event
