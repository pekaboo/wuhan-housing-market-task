from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_API_URL = 'https://xcx.wufangtong.com/api/v1/data/GetLouPanSaleImages'
DEFAULT_CITY_ID = '4201'
DEFAULT_PAGE_SIZE = 10
DEFAULT_MAX_PAGES = 100
DEFAULT_TIMEOUT_SECONDS = 20.0
USER_AGENT = (
    'Mozilla/5.0 (iPhone; CPU iPhone OS 26_6 like Mac OS X) '
    'AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 '
    'MicroMessenger/8.0.75(0x18004b64) NetType/WIFI Language/zh_CN'
)
REFERER = 'https://servicewechat.com/wxc1d3d24083486c2b/118/page-frame.html'


class SaleApiError(RuntimeError):
    """A safe, token-free upstream API error."""


@dataclass(slots=True)
class ApiRequest:
    url: str
    payload: dict[str, int]
    headers: dict[str, str]


@dataclass(slots=True)
class ApiResponse:
    status_code: int
    body: bytes
    content_type: str


Transport = Callable[[ApiRequest], ApiResponse]


def urllib_transport(timeout_seconds: float) -> Transport:
    def send(request: ApiRequest) -> ApiResponse:
        outgoing = Request(
            request.url,
            data=json.dumps(request.payload, separators=(',', ':')).encode('utf-8'),
            headers=request.headers,
            method='POST',
        )
        try:
            with urlopen(outgoing, timeout=timeout_seconds) as response:
                return ApiResponse(
                    status_code=response.status,
                    body=response.read(),
                    content_type=response.headers.get_content_type(),
                )
        except HTTPError as exc:
            body = exc.read()
            raise SaleApiError(f'Upstream API returned HTTP {exc.code}.') from exc
        except (URLError, TimeoutError) as exc:
            raise SaleApiError(f'Could not reach upstream API: {exc}') from exc

    return send


class SaleApiClient:
    def __init__(
        self,
        *,
        token: str,
        api_url: str = DEFAULT_API_URL,
        city_id: str = DEFAULT_CITY_ID,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        transport: Transport | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not token:
            raise ValueError('A wfTToken is required')
        if page_size < 1 or max_pages < 1:
            raise ValueError('page_size and max_pages must be positive')

        self.api_url = api_url.rstrip('/')
        self.city_id = city_id
        self.page_size = page_size
        self.max_pages = max_pages
        self.token = token
        self.transport = transport or urllib_transport(timeout_seconds)

    def fetch_all_projects(self) -> list[dict[str, Any]]:
        projects_by_id: dict[Any, dict[str, Any]] = {}

        for page_int in range(1, self.max_pages + 1):
            result = self.fetch_page(page_int)
            for item in result:
                project_id = item.get('id')
                key = project_id if project_id is not None else f'missing-id-{len(projects_by_id)}'
                projects_by_id.setdefault(key, item)

            if len(result) < self.page_size:
                return list(projects_by_id.values())

        raise SaleApiError(
            f'Upstream pagination did not stop before the configured page limit ({self.max_pages}). '
            'Increase the limit or inspect the API response.'
        )

    def fetch_page(self, page_int: int) -> list[dict[str, Any]]:
        request = ApiRequest(
            url=self.api_url,
            payload={'pageInt': page_int, 'pageSize': self.page_size},
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-City-Id': self.city_id,
                'wfTToken': self.token,
                'User-Agent': USER_AGENT,
                'Referer': REFERER,
            },
        )
        response = self.transport(request)
        if response.status_code != 200:
            raise SaleApiError(f'Upstream API returned HTTP {response.status_code}.')

        try:
            payload = json.loads(response.body.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SaleApiError(f'Upstream API returned invalid JSON on page {page_int}.') from exc

        if not payload.get('success') or payload.get('code') != 0:
            message = str(payload.get('message') or 'unknown upstream error')
            raise SaleApiError(f'Upstream API error on page {page_int}: {message}')

        result = payload.get('result')
        if not isinstance(result, list):
            raise SaleApiError(f'Upstream API result is not a list on page {page_int}.')

        return result
