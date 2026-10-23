from __future__ import annotations

import gzip
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .render import render_html
from .site import render_project_page
from .wangqian import render_wangqian_page


def china_timestamp(now: datetime | None = None) -> str:
    current = now.astimezone(ZoneInfo('Asia/Shanghai')) if now else datetime.now(ZoneInfo('Asia/Shanghai'))
    return current.strftime('%Y-%m-%d %H:%M:%S')


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _atomic_write(path: Path, content: str) -> None:
    _atomic_write_bytes(path, content.encode('utf-8'))


def _write_json(path: Path, value: Any) -> None:
    _atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def _write_gzip_json(path: Path, value: Any) -> None:
    payload = json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True).encode('utf-8')
    _atomic_write_bytes(path, gzip.compress(payload, compresslevel=9, mtime=0))


def safe_project_id(project: dict[str, Any], index: int) -> str:
    raw_id = str(project.get('id') or f'missing-{index}')
    return ''.join(character if character.isalnum() else '-' for character in raw_id).strip('-') or f'project-{index}'


def _project_snapshot(
    project: dict[str, Any],
    snapshots: dict[Any, dict[str, Any]],
) -> dict[str, Any] | None:
    project_id = project.get('id')
    candidates: list[Any] = [project_id, str(project_id)]
    if str(project_id).isdigit():
        candidates.append(int(project_id))
    for candidate in candidates:
        snapshot = snapshots.get(candidate)
        if isinstance(snapshot, dict):
            return snapshot
    return None


def _wangqian_slug(snapshot: dict[str, Any]) -> str:
    value = str(snapshot.get('date') or snapshot.get('time') or 'latest')
    match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', value)
    if match:
        year, month, day = (int(part) for part in match.groups())
        return f'{year:04d}-{month:02d}-{day:02d}'
    try:
        return datetime.fromisoformat(value).strftime('%Y-%m-%d')
    except ValueError:
        return ''.join(character if character.isalnum() else '-' for character in value[:10]).strip('-') or 'latest'


def write_site(
    projects: list[dict[str, Any]],
    *,
    site_dir: Path | str,
    generated_at: str | None = None,
    now: datetime | None = None,
    one_price_snapshots: dict[Any, dict[str, Any]] | None = None,
    room_type_snapshots: dict[Any, dict[str, Any]] | None = None,
    wangqian_snapshot: dict[str, Any] | None = None,
    enrichment_state: dict[str, Any] | None = None,
    featured_keys: list[str] | None = None,
) -> list[Path]:
    timestamp = generated_at or china_timestamp(now)
    root = Path(site_dir)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    snapshots = one_price_snapshots or {}
    room_snapshots = room_type_snapshots or {}

    output_paths: list[Path] = []
    _atomic_write(
        root / 'index.html',
        render_html(
            projects,
            generated_at=timestamp,
            one_price_snapshots=snapshots or None,
            featured_keys=featured_keys,
        ),
    )
    output_paths.append(Path('index.html'))

    for index, project in enumerate(projects):
        safe_id = safe_project_id(project, index)
        relative_path = Path('projects', safe_id, 'index.html')
        snapshot = _project_snapshot(project, snapshots)
        data_relative_path = Path('data', 'projects', safe_id, 'one-price.json.gz')
        if snapshot is not None:
            enriched_snapshot = dict(snapshot)
            enriched_snapshot.setdefault('projectId', project.get('id'))
            enriched_snapshot.setdefault('generatedAt', timestamp)
            _write_gzip_json(root / data_relative_path, enriched_snapshot)
        room_snapshot = _project_snapshot(project, room_snapshots)
        room_data_relative_path = Path('data', 'projects', safe_id, 'room-types.json')
        if room_snapshot is not None:
            enriched_room_snapshot = dict(room_snapshot)
            enriched_room_snapshot.setdefault('projectId', project.get('id'))
            enriched_room_snapshot.setdefault('generatedAt', timestamp)
            _write_json(root / room_data_relative_path, enriched_room_snapshot)
        _atomic_write(
            root / relative_path,
            render_project_page(
                project,
                generated_at=timestamp,
                all_count=len(projects),
                previous_project=projects[index - 1] if index > 0 else None,
                next_project=projects[index + 1] if index + 1 < len(projects) else None,
                one_price_snapshot=snapshot,
                one_price_url=f'../../{data_relative_path.as_posix()}' if snapshot is not None else None,
                room_type_snapshot=room_snapshot,
                room_type_url=(
                    f'../../{room_data_relative_path.as_posix()}'
                    if room_snapshot is not None
                    else None
                ),
            ),
        )
        output_paths.append(relative_path)

    if wangqian_snapshot is not None:
        relative_path = Path('wangqian', 'index.html')
        _atomic_write(root / relative_path, render_wangqian_page(wangqian_snapshot, generated_at=timestamp))
        output_paths.append(relative_path)
        _write_json(root / 'data' / 'wangqian' / f'{_wangqian_slug(wangqian_snapshot)}.json', wangqian_snapshot)

    if enrichment_state is not None:
        state = dict(enrichment_state)
        state.setdefault('lastRunAt', timestamp)
        _write_json(root / 'data' / 'enrichment-state.json', state)

    snapshot_data = {'generatedAt': timestamp, 'count': len(projects), 'projects': projects}
    _write_json(root / 'data' / 'sale-data.json', snapshot_data)
    return output_paths


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
    _write_json(Path(data_path), snapshot)
    return timestamp
