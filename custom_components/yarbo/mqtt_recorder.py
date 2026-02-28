"""MQTT message recorder for Yarbo diagnostics.

Records all sent and received MQTT messages to a rotating log file.
Users can share this file to help debug issues with different firmware
versions, head types, or attachments that the developers don't own.

File format: JSONL (one JSON object per line) for easy parsing.
Each line: {"ts": ISO8601, "dir": "TX"|"RX", "topic": "...", "payload": {...}, "raw_len": N}
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

_LOGGER = logging.getLogger(__name__)


class MqttRecorder:
    """Records MQTT messages to a size-limited JSONL file."""

    def __init__(
        self,
        storage_dir: Path,
        serial_number: str,
        max_size_bytes: int = 10 * 1024 * 1024,  # 10 MB
    ) -> None:
        self._dir = storage_dir / "yarbo_recordings"
        self._serial = serial_number
        self._max_size = max_size_bytes
        self._enabled = False
        self._file = None
        self._current_path: Path | None = None
        self._bytes_written = 0
        self._write_lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def recording_path(self) -> Path | None:
        return self._current_path

    def start(self) -> Path:
        if self._enabled and self._current_path:
            return self._current_path

        self._dir.mkdir(parents=True, exist_ok=True)
        safe_serial = self._serial[-8:] if len(self._serial) > 8 else self._serial
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        self._current_path = self._dir / f"yarbo_{safe_serial}_{ts}.jsonl"
        self._file = open(self._current_path, "a", encoding="utf-8")
        self._bytes_written = (
            self._current_path.stat().st_size if self._current_path.exists() else 0
        )
        self._enabled = True

        _LOGGER.info("MQTT recording started: %s", self._current_path)
        self._write_entry(
            "META",
            "recording_start",
            {
                "serial": self._serial,
                "max_size_bytes": self._max_size,
                "started_at": datetime.now(UTC).isoformat(),
            },
        )
        return self._current_path

    def stop(self) -> None:
        with self._write_lock:
            if not self._enabled:
                return

            if self._file:
                entry = {
                    "ts": datetime.now(UTC).isoformat(),
                    "dir": "META",
                    "topic": "recording_stop",
                    "payload": {
                        "stopped_at": datetime.now(UTC).isoformat(),
                        "bytes_written": self._bytes_written,
                    },
                }
                line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
                try:
                    self._file.write(line)
                    self._file.flush()
                    self._bytes_written += len(line.encode("utf-8"))
                except OSError as err:
                    _LOGGER.warning("Failed to write final MQTT recording entry: %s", err)

                self._file.close()
                self._file = None

            self._enabled = False
            _LOGGER.info(
                "MQTT recording stopped: %s (%.1f KB)",
                self._current_path,
                self._bytes_written / 1024,
            )

    def record_rx(self, topic: str, payload: dict | str | bytes, raw_len: int = 0) -> None:
        if not self._enabled:
            return
        self._write_entry("RX", topic, payload, raw_len)

    def record_tx(self, topic: str, payload: dict | str | bytes, raw_len: int = 0) -> None:
        if not self._enabled:
            return
        self._write_entry("TX", topic, payload, raw_len)

    def _write_entry(
        self,
        direction: str,
        topic: str,
        payload: dict | str | bytes,
        raw_len: int = 0,
    ) -> None:
        with self._write_lock:
            if not self._file:
                return

            try:
                if self._bytes_written >= self._max_size:
                    self._rotate()
            except OSError as err:
                _LOGGER.warning("Failed to rotate MQTT recording: %s", err)
                self._enabled = False
                if self._file:
                    self._file.close()
                    self._file = None
                return

            if isinstance(payload, bytes):
                try:
                    payload_out: dict | str = json.loads(payload)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    payload_out = payload.hex()
            elif isinstance(payload, str):
                try:
                    payload_out = json.loads(payload)
                except json.JSONDecodeError:
                    payload_out = payload
            else:
                payload_out = payload

            entry: dict = {
                "ts": datetime.now(UTC).isoformat(),
                "dir": direction,
                "topic": topic,
                "payload": payload_out,
            }
            if raw_len:
                entry["raw_len"] = raw_len

            line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
            try:
                self._file.write(line)
                self._file.flush()
                self._bytes_written += len(line.encode("utf-8"))
            except OSError as err:
                _LOGGER.warning("Failed to write MQTT recording: %s", err)

    def _rotate(self) -> None:
        if self._file:
            self._file.close()

        if self._current_path:
            rotated = self._current_path.with_suffix(".1.jsonl")
            old_rotated = self._current_path.with_suffix(".2.jsonl")
            if old_rotated.exists():
                old_rotated.unlink()
            if rotated.exists():
                rotated.rename(old_rotated)
            if self._current_path.exists():
                self._current_path.rename(rotated)

        self._file = open(self._current_path, "a", encoding="utf-8")
        self._bytes_written = 0
        _LOGGER.info("MQTT recording rotated: %s", self._current_path)

    def list_recordings(self) -> list[Path]:
        if not self._dir.exists():
            return []
        safe_serial = self._serial[-8:] if len(self._serial) > 8 else self._serial
        return sorted(self._dir.glob(f"yarbo_{safe_serial}_*.jsonl"), reverse=True)

    def cleanup(self) -> None:
        for path in self.list_recordings():
            try:
                path.unlink()
            except OSError:
                pass
