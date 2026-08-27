from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .render import render_html


def china_timestamp(now: datetime | None = None) -> str:
    current = now.astimezone(ZoneInfo('Asia/Shanghai')) if now else datetime.now(ZoneInfo('Asia/Shanghai'))
    return current.strftime('%Y-%m-%d %H:%M:%S')


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def write_outputs(
    projects: list[dict[str, Any]],
    *,
    html_path: Path | str,
    data_path: Path | str,
    generated_at: str | None = None,
    now: datetime | None = None,
) -> str:
    timestamp = generated_at or china_timestamp(now)
    snapshot = {'generatedAt': timestamp, 'count': len(projects), 'projects': projects}

    _atomic_write(Path(html_path), render_html(projects, generated_at=timestamp))
    _atomic_write(
        Path(data_path),
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
    )
    return timestamp
