"""GlitchTip/Sentry error reporting for the Yarbo Home Assistant integration."""

from __future__ import annotations

import logging
import os

_LOGGER = logging.getLogger(__name__)


def init_error_reporting(
    dsn: str | None = None,
    environment: str = "production",
    enabled: bool = True,
    tags: dict[str, str] | None = None,
) -> None:
    """Initialize Sentry/GlitchTip error reporting for the Yarbo HA integration.

    Opt-in only: no data is sent unless YARBO_SENTRY_DSN is explicitly set.
    To enable, set the YARBO_SENTRY_DSN environment variable to your project DSN.

    Args:
        dsn: Sentry DSN. If None, falls back to YARBO_SENTRY_DSN env var.
             No default is provided — reporting is disabled unless DSN is explicitly set.
        environment: Environment tag (production/development/testing).
        enabled: Master switch. If False, no SDK initialization occurs.
        tags: Optional extra tags (e.g. robot_serial, ha_version, integration_version).
    """
    if not enabled:
        return

    # Resolve DSN: explicit arg > YARBO_SENTRY_DSN env var
    # No hardcoded default — opt-in only
    effective_dsn = dsn or os.environ.get("YARBO_SENTRY_DSN")

    if not effective_dsn:
        # No DSN configured — error reporting disabled (opt-in model)
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
    except Exception as exc:
        _LOGGER.warning("Failed to initialize error reporting: %s", exc)


def _scrub_event(event: dict, hint: dict) -> dict:  # type: ignore[type-arg]
    """Remove sensitive data before sending."""
    if "extra" in event:
        for key in list(event["extra"]):
            if any(s in key.lower() for s in ("password", "token", "secret", "credential", "key")):
                event["extra"][key] = "[REDACTED]"
    return event
