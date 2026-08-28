from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any


def _normalize(value: Any) -> str:
    text = '' if value is None else str(value)
    text = unicodedata.normalize('NFKC', text).strip()
    return ' '.join(text.split()).casefold()


def load_featured_project_keys(path: Path | str) -> list[str]:
    try:
        lines = Path(path).read_text(encoding='utf-8').splitlines()
    except OSError:
        return []

    keys: list[str] = []
    seen: set[str] = set()
    for line in lines:
        value = line.split('#', 1)[0].strip()
        if not value:
            continue
        key = _normalize(value)
        if key and key not in seen:
            seen.add(key)
            keys.append(value)
    return keys


def _project_keys(project: dict[str, Any]) -> set[str]:
    keys = {_normalize(project.get('id')), _normalize(project.get('name'))}
    return {key for key in keys if key}


def split_featured_projects(
    projects: Sequence[dict[str, Any]],
    featured_keys: Iterable[str] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized = [_normalize(key) for key in featured_keys or []]
    wanted = {key for key in normalized if key}

    featured_by_key: dict[str, dict[str, Any]] = {}
    standard: list[dict[str, Any]] = []
    for project in projects:
        matched_key = next((key for key in _project_keys(project) if key in wanted), None)
        if matched_key is None:
            standard.append(project)
        elif matched_key not in featured_by_key:
            featured_by_key[matched_key] = project

    featured: list[dict[str, Any]] = []
    used: set[str] = set()
    for key in normalized:
        if key in featured_by_key and key not in used:
            featured.append(featured_by_key[key])
            used.add(key)
    return featured, standard
