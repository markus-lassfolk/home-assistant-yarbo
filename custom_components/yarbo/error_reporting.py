"""GlitchTip/Sentry error reporting for the Yarbo Home Assistant integration."""

from __future__ import annotations

import logging
import os

_LOGGER = logging.getLogger(__name__)

# Default DSN for the Yarbo HA integration GlitchTip project.
# Opt-out: set YARBO_SENTRY_DSN="" to disable error reporting.
_DEFAULT_DSN = "https://c9d816d9a8714ac288e86b49c683b533@villapolly.duckdns.org/4"


def init_error_reporting(
    dsn: str | None = None,
    environment: str = "production",
    enabled: bool = True,
    tags: dict[str, str] | None = None,
) -> None:
    """Initialize Sentry/GlitchTip error reporting for the Yarbo HA integration.

    Enabled by default during the beta — errors are reported to help identify
    and fix bugs. No PII is collected; credentials are scrubbed before sending.

    To disable, set the YARBO_SENTRY_DSN environment variable to an empty string.
    To use a custom DSN, set YARBO_SENTRY_DSN to your project DSN.

    Args:
        dsn: Sentry DSN override. If None, falls back to YARBO_SENTRY_DSN env var,
             then to the built-in default DSN.
        environment: Environment tag (production/development/testing).
        enabled: Master switch. If False, no SDK initialization occurs.
        tags: Optional extra tags (e.g. robot_serial, ha_version, integration_version).
    """
    if not enabled:
        return

    # Resolve DSN: explicit arg > YARBO_SENTRY_DSN env var > built-in default
    env_dsn = os.environ.get("YARBO_SENTRY_DSN")
    if env_dsn is not None and env_dsn == "":
        # Explicit opt-out: YARBO_SENTRY_DSN="" disables reporting
        _LOGGER.debug("Error reporting explicitly disabled via YARBO_SENTRY_DSN=\"\"")
        return
    effective_dsn = dsn or env_dsn or _DEFAULT_DSN

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
    except Exception as exc:
        _LOGGER.warning("Failed to initialize error reporting: %s", exc)


# Non-sensitive field names that contain "_key" but must not be redacted.
_KEY_ALLOWLIST: frozenset[str] = frozenset({"entity_key"})


def _scrub_event(event: dict, hint: dict) -> dict:  # type: ignore[type-arg]
    """Remove sensitive data before sending."""
    if "extra" in event:
        for key in list(event["extra"]):
            key_lower = key.lower()
            if any(s in key_lower for s in ("password", "token", "secret", "credential")):
                event["extra"][key] = "[REDACTED]"
            elif (
                key_lower == "key"
                or "_key" in key_lower
                or key_lower.startswith("key_")
                or key_lower.endswith("key")
            ) and key_lower not in _KEY_ALLOWLIST:
                # Catches bare "key", suffix "_key" (api_key), prefix "key_" (key_material,
                # key_data, key_pair), concatenated suffix "key" (apikey, privatekey), and
                # compound forms. Allowlist exempts known non-sensitive fields like entity_key.
                event["extra"][key] = "[REDACTED]"
    return event
