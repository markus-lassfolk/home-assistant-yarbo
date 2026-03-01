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

    Opt-in error reporting — only enabled when YARBO_SENTRY_DSN is explicitly set.
    No PII is collected; credentials are scrubbed before sending.

    To enable, set the YARBO_SENTRY_DSN environment variable to your project DSN.

    Args:
        dsn: Sentry DSN override. If None, falls back to YARBO_SENTRY_DSN env var.
        environment: Environment tag (production/development/testing).
        enabled: Master switch. If False, no SDK initialization occurs.
        tags: Optional extra tags (e.g. robot_serial, ha_version, integration_version).
    """
    if not enabled:
        return

    # Resolve DSN: explicit arg > YARBO_SENTRY_DSN env var
    env_dsn = os.environ.get("YARBO_SENTRY_DSN")
    effective_dsn = dsn or env_dsn

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


def _is_sensitive_key(key: str) -> bool:
    """Return True if the key name looks like it holds a secret."""
    key_lower = key.lower()
    if any(s in key_lower for s in ("password", "token", "secret", "credential")):
        return True
    if (
        key_lower == "key"
        or "_key" in key_lower
        or key_lower.startswith("key_")
        or key_lower.endswith("key")
    ) and key_lower not in _KEY_ALLOWLIST:
        return True
    return False


def _scrub_dict(data: dict) -> None:  # type: ignore[type-arg]
    """Redact sensitive values in a dict in-place."""
    for key in list(data):
        if _is_sensitive_key(key):
            data[key] = "[REDACTED]"


def _scrub_event(event: dict, hint: dict) -> dict:  # type: ignore[type-arg]
    """Remove sensitive data before sending."""
    if "extra" in event:
        _scrub_dict(event["extra"])

    for crumb in event.get("breadcrumbs", {}).get("values", []):
        if "data" in crumb and isinstance(crumb["data"], dict):
            _scrub_dict(crumb["data"])

    if "request" in event and isinstance(event["request"], dict):
        for field in ("headers", "query_string", "cookies", "data"):
            if field in event["request"] and isinstance(event["request"][field], dict):
                _scrub_dict(event["request"][field])

    if "contexts" in event and isinstance(event["contexts"], dict):
        for _ctx_name, ctx_data in event["contexts"].items():
            if isinstance(ctx_data, dict):
                _scrub_dict(ctx_data)

    return event
