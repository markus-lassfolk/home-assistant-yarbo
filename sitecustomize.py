"""Test harness stubs to avoid background DNS threads.

Python auto-imports sitecustomize when present on sys.path. We use this
hook to stub aiodns/pycares before any Home Assistant imports occur.
"""

from __future__ import annotations

import sys
import types

if "pycares" not in sys.modules:
    sys.modules["pycares"] = types.ModuleType("pycares")

if "aiodns" not in sys.modules:
    aiodns = types.ModuleType("aiodns")

    class DNSResolver:  # noqa: D401 - small stub
        """Stub for aiodns.DNSResolver."""

        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

    aiodns.DNSResolver = DNSResolver
    sys.modules["aiodns"] = aiodns
