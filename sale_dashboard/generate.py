from __future__ import annotations

import json
import os
import math
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .render import render_html
from .site import render_project_page


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


def safe_project_id(project: dict[str, Any], index: int) -> str:
    raw_id = str(project.get("id") or f"missing-{index}")
    return "".join(character if character.isalnum() else "-" for character in raw_id).strip("-") or f"project-{index}"


def write_site(
    projects: list[dict[str, Any]],
    *,
    site_dir: Path | str,
    generated_at: str | None = None,
    per_page: int = 6,
    now: datetime | None = None,
) -> list[Path]:
    timestamp = generated_at or china_timestamp(now)
    root = Path(site_dir)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    page_count = max(1, math.ceil(len(projects) / per_page))
    output_paths: list[Path] = []
    for page_number in range(1, page_count + 1):
        page_projects = projects[(page_number - 1) * per_page : page_number * per_page]
        relative_path = Path("index.html") if page_number == 1 else Path("page", str(page_number), "index.html")
        absolute_path = root / relative_path
        _atomic_write(
            absolute_path,
            render_html(
                page_projects,
                generated_at=timestamp,
                summary_projects=projects,
                current_page=page_number,
                page_count=page_count,
                root_prefix="" if page_number == 1 else "../../",
            ),
        )
        output_paths.append(relative_path)

    for index, project in enumerate(projects):
        relative_path = Path("projects", safe_project_id(project, index), "index.html")
        _atomic_write(
            root / relative_path,
            render_project_page(
                project,
                generated_at=timestamp,
                all_count=len(projects),
                previous_project=projects[index - 1] if index > 0 else None,
                next_project=projects[index + 1] if index + 1 < len(projects) else None,
            ),
        )
        output_paths.append(relative_path)

    snapshot = {"generatedAt": timestamp, "count": len(projects), "projects": projects}
    _atomic_write(
        root / "data" / "sale-data.json",
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
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
    _atomic_write(
        Path(data_path),
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
    )
    return timestamp
