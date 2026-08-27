from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, Protocol

from .cache import ResponseCache
from .client import SaleApiError
from .enrichment import build_one_price_snapshot, build_room_type_snapshot


class UpstreamClient(Protocol):
    def fetch_all_projects(self) -> list[dict[str, Any]]: ...

    def fetch_presale_certificates(self, project_id: int | str) -> list[dict[str, Any]]: ...

    def fetch_room_types(self, project_id: int | str) -> list[dict[str, Any]]: ...

    def fetch_room_items(
        self, project_id: int | str, evidence_id: int | str
    ) -> list[dict[str, Any]]: ...


class _CachedEnrichmentClient:
    def __init__(self, service: 'DashboardService') -> None:
        self.service = service

    def fetch_presale_certificates(self, project_id: int | str) -> list[dict[str, Any]]:
        return self.service._cached(
            f'presale-certificates:{project_id}',
            lambda: self.service.client.fetch_presale_certificates(project_id),
        )

    def fetch_room_items(self, project_id: int | str, evidence_id: int | str) -> list[dict[str, Any]]:
        return self.service._cached(
            f'room-items:{project_id}:{evidence_id}',
            lambda: self.service.client.fetch_room_items(project_id, evidence_id),
        )


class DashboardService:
    """Caches upstream responses and resumes enrichment across service restarts."""

    def __init__(
        self,
        client: UpstreamClient,
        cache: ResponseCache,
        *,
        ttl_seconds: float = 21600,
    ) -> None:
        self.client = client
        self.cache = cache
        self.ttl_seconds = ttl_seconds
        city_id = str(getattr(client, 'city_id', ''))
        page_size = str(getattr(client, 'page_size', ''))
        max_pages = str(getattr(client, 'max_pages', ''))
        self.namespace = f'v1:{city_id}:{page_size}:{max_pages}'
        self.cached_enrichment_client = _CachedEnrichmentClient(self)

        self._warm_thread: threading.Thread | None = None
        self._warm_stop = threading.Event()
        self._warm_lock = threading.Lock()
        self._warm_status: dict[str, Any] = {
            'state': 'idle',
            'total': 0,
            'completed': 0,
            'failed': 0,
            'currentProject': None,
            'error': None,
        }

    def _cached(self, key: str, fetch: Callable[[], Any]) -> Any:
        cached = self.cache.get(f'{self.namespace}:{key}', ttl_seconds=self.ttl_seconds)
        if cached is not None:
            return cached
        value = fetch()
        self.cache.set(f'{self.namespace}:{key}', value)
        return value

    def projects(self, *, refresh: bool = False) -> list[dict[str, Any]]:
        if refresh:
            projects = self.client.fetch_all_projects()
            self.cache.set(f'{self.namespace}:projects', projects)
            return projects
        return self._cached('projects', self.client.fetch_all_projects)

    def project(self, project_id: int | str) -> dict[str, Any] | None:
        return next(
            (item for item in self.projects() if str(item.get('id')) == str(project_id)),
            None,
        )

    def one_price(self, project_id: int | str, *, refresh: bool = False) -> dict[str, Any]:
        if refresh:
            snapshot = build_one_price_snapshot(self.client, project_id)
            self.cache.set(f'{self.namespace}:one-price:{project_id}', snapshot)
            return snapshot
        return self._cached(
            f'one-price:{project_id}',
            lambda: build_one_price_snapshot(self.cached_enrichment_client, project_id),
        )

    def room_types(self, project_id: int | str, *, refresh: bool = False) -> dict[str, Any]:
        if refresh:
            snapshot = build_room_type_snapshot(self.client, project_id)
            self.cache.set(f'{self.namespace}:room-types:{project_id}', snapshot)
            return snapshot
        return self._cached(
            f'room-types:{project_id}',
            lambda: build_room_type_snapshot(self.client, project_id),
        )

    def warm_status(self) -> dict[str, Any]:
        with self._warm_lock:
            return dict(self._warm_status)

    def start_warm(self) -> dict[str, Any]:
        with self._warm_lock:
            if self._warm_thread is not None and self._warm_thread.is_alive():
                return dict(self._warm_status)
            self._warm_stop.clear()
            self._warm_status = {
                'state': 'starting',
                'total': 0,
                'completed': 0,
                'failed': 0,
                'currentProject': None,
                'error': None,
            }
            self._warm_thread = threading.Thread(
                target=self._warm_worker,
                name='wft-dashboard-warm',
                daemon=True,
            )
            self._warm_thread.start()
            return dict(self._warm_status)

    def stop_warm(self) -> dict[str, Any]:
        self._warm_stop.set()
        return self.warm_status()

    def _set_warm_status(self, **values: Any) -> None:
        with self._warm_lock:
            self._warm_status.update(values)

    def _warm_worker(self) -> None:
        try:
            projects = self.projects()
        except SaleApiError as exc:
            self._set_warm_status(state='failed', error=str(exc))
            return

        self._set_warm_status(state='running', total=len(projects))
        for index, project in enumerate(projects, 1):
            if self._warm_stop.is_set():
                self._set_warm_status(state='stopped', currentProject=None)
                return

            project_id = project.get('id')
            current = {
                'index': index,
                'id': project_id,
                'name': project.get('name'),
            }
            self._set_warm_status(state='running', currentProject=current)
            if project_id is None:
                self._set_warm_status(failed=self.warm_status()['failed'] + 1)
                continue

            try:
                one_price = self.one_price(project_id)
                room_types = self.room_types(project_id)
                failed = 1 if one_price.get('status') == 'error' or room_types.get('status') == 'error' else 0
                self._set_warm_status(
                    completed=self.warm_status()['completed'] + 1,
                    failed=self.warm_status()['failed'] + failed,
                )
            except SaleApiError as exc:
                self._set_warm_status(
                    failed=self.warm_status()['failed'] + 1,
                    error=str(exc),
                )

        self._set_warm_status(state='completed', currentProject=None)
