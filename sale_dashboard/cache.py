from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class ResponseCache:
    """A small persistent JSON cache for safe upstream response bodies."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._lock = threading.RLock()
        self._connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS responses (
                key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
            '''
        )
        self._connection.commit()

    def get(self, key: str, *, ttl_seconds: float | None = 300) -> Any | None:
        if ttl_seconds is not None and ttl_seconds <= 0:
            return None
        with self._lock:
            row = self._connection.execute(
                'SELECT payload, updated_at FROM responses WHERE key = ?',
                (key,),
            ).fetchone()
        if row is None:
            return None
        payload, updated_at = row
        if ttl_seconds is not None and time.time() - updated_at >= ttl_seconds:
            return None
        return json.loads(payload)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._connection.execute(
                '''
                INSERT INTO responses (key, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
            ''',
                (key, json.dumps(value, ensure_ascii=False, separators=(',', ':')), int(time.time())),
            )
            self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.close()
