from __future__ import annotations

from os import getenv
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from .cache import ResponseCache
from .client import (
    DEFAULT_CITY_ID,
    DEFAULT_MAX_PAGES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_ROOM_PAGE_SIZE,
    DEFAULT_TIMEOUT_SECONDS,
    SaleApiClient,
    SaleApiError,
)
from .generate import china_timestamp
from .render import render_html
from .service import DashboardService
from .site import render_project_page


def _default_service() -> DashboardService:
    token = getenv('WFT_TOKEN', '').strip()
    if not token:
        raise HTTPException(status_code=503, detail='WFT_TOKEN is not configured')

    page_size = int(getenv('WFT_PAGE_SIZE', str(DEFAULT_PAGE_SIZE)))
    room_page_size = int(getenv('WFT_ROOM_PAGE_SIZE', str(DEFAULT_ROOM_PAGE_SIZE)))
    max_pages = int(getenv('WFT_MAX_PAGES', str(DEFAULT_MAX_PAGES)))
    timeout_seconds = float(getenv('WFT_REQUEST_TIMEOUT_SECONDS', str(DEFAULT_TIMEOUT_SECONDS)))
    ttl_seconds = float(getenv('WFT_CACHE_TTL_SECONDS', '21600'))
    cache_path = getenv('WFT_CACHE_PATH', '.wft-cache/responses.sqlite3')

    client = SaleApiClient(
        token=token,
        city_id=getenv('WFT_CITY_ID', DEFAULT_CITY_ID),
        page_size=page_size,
        room_page_size=room_page_size,
        max_pages=max_pages,
        timeout_seconds=timeout_seconds,
    )
    return DashboardService(client, ResponseCache(cache_path), ttl_seconds=ttl_seconds)


def get_service(request: Request) -> DashboardService:
    service = getattr(request.app.state, 'service', None)
    if service is None:
        service = _default_service()
        request.app.state.service = service
    return service


def create_app(service: DashboardService | None = None) -> FastAPI:
    app = FastAPI(title='Pekaboo 武汉楼盘实时销控 API', version='1.0')
    app.state.service = service

    def run_upstream(call) -> Any:
        try:
            return call()
        except SaleApiError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get('/health')
    def health(service: DashboardService = Depends(get_service)) -> dict[str, Any]:
        return {
            'status': 'ok',
            'upstreamConfigured': True,
            'warm': service.warm_status(),
        }

    @app.get('/api/projects')
    def projects(
        service: DashboardService = Depends(get_service),
        refresh: bool = Query(default=False),
    ) -> dict[str, Any]:
        values = run_upstream(lambda: service.projects(refresh=refresh))
        return {'count': len(values), 'projects': values, 'fetchedAt': china_timestamp()}

    @app.get('/api/projects/{project_id}')
    def project(
        project_id: str,
        service: DashboardService = Depends(get_service),
    ) -> dict[str, Any]:
        value = run_upstream(lambda: service.project(project_id))
        if value is None:
            raise HTTPException(status_code=404, detail='Project not found')
        return value

    @app.get('/api/projects/{project_id}/one-price')
    def project_one_price(
        project_id: str,
        service: DashboardService = Depends(get_service),
        refresh: bool = Query(default=False),
    ) -> dict[str, Any]:
        if run_upstream(lambda: service.project(project_id)) is None:
            raise HTTPException(status_code=404, detail='Project not found')
        return run_upstream(lambda: service.one_price(project_id, refresh=refresh))

    @app.get('/api/projects/{project_id}/room-types')
    def project_room_types(
        project_id: str,
        service: DashboardService = Depends(get_service),
        refresh: bool = Query(default=False),
    ) -> dict[str, Any]:
        if run_upstream(lambda: service.project(project_id)) is None:
            raise HTTPException(status_code=404, detail='Project not found')
        return run_upstream(lambda: service.room_types(project_id, refresh=refresh))

    @app.get('/', response_class=HTMLResponse)
    def home(service: DashboardService = Depends(get_service)) -> str:
        values = run_upstream(service.projects)
        return render_html(values, generated_at=china_timestamp())

    @app.get('/projects/{project_id}/', response_class=HTMLResponse)
    def project_page(
        project_id: str,
        service: DashboardService = Depends(get_service),
        refresh: bool = Query(default=False),
    ) -> str:
        projects = run_upstream(service.projects)
        index = next(
            (i for i, item in enumerate(projects) if str(item.get('id')) == project_id),
            None,
        )
        if index is None:
            raise HTTPException(status_code=404, detail='Project not found')

        project = projects[index]
        one_price_snapshot = run_upstream(lambda: service.one_price(project_id, refresh=refresh))
        room_type_snapshot = run_upstream(lambda: service.room_types(project_id, refresh=refresh))
        return render_project_page(
            project,
            generated_at=china_timestamp(),
            all_count=len(projects),
            previous_project=projects[index - 1] if index > 0 else None,
            next_project=projects[index + 1] if index + 1 < len(projects) else None,
            one_price_snapshot=one_price_snapshot,
            one_price_url=f'/api/projects/{project_id}/one-price',
            room_type_snapshot=room_type_snapshot,
            room_type_url=f'/api/projects/{project_id}/room-types',
        )

    @app.post('/api/warm', status_code=202)
    def start_warm(service: DashboardService = Depends(get_service)) -> dict[str, Any]:
        return service.start_warm()

    @app.post('/api/warm/stop')
    def stop_warm(service: DashboardService = Depends(get_service)) -> dict[str, Any]:
        return service.stop_warm()

    @app.get('/api/warm/status')
    def warm_status(service: DashboardService = Depends(get_service)) -> dict[str, Any]:
        return service.warm_status()

    return app


app = create_app()
