from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

DEFAULT_API_URL = 'https://xcx.wufangtong.com/api/v1/data/GetLouPanSaleImages'
DEFAULT_CITY_ID = '4201'
DEFAULT_PAGE_SIZE = 50
DEFAULT_ROOM_PAGE_SIZE = 500
DEFAULT_MAX_PAGES = 100
DEFAULT_TIMEOUT_SECONDS = 20.0
USER_AGENT = (
    'Mozilla/5.0 (iPhone; CPU iPhone OS 26_6 like Mac OS X) '
    'AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 '
    'MicroMessenger/8.0.75(0x18004b64) NetType/WIFI Language/zh_CN'
)
REFERER = 'https://servicewechat.com/wxc1d3d24083486c2b/118/page-frame.html'
API_PATH_PREFIX = '/api/v1/data/'


class SaleApiError(RuntimeError):
    """A safe, token-free upstream API error."""


@dataclass(slots=True)
class ApiRequest:
    url: str
    payload: dict[str, Any]
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
        room_page_size: int = DEFAULT_ROOM_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        transport: Transport | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        if not token:
            raise ValueError('A wfTToken is required')
        if page_size < 1 or room_page_size < 1 or max_pages < 1:
            raise ValueError('page_size, room_page_size and max_pages must be positive')

        self.api_url = api_url.rstrip('/')
        split_url = urlsplit(self.api_url)
        self.api_origin = f'{split_url.scheme}://{split_url.netloc}'
        self.city_id = city_id
        self.page_size = page_size
        self.room_page_size = room_page_size
        self.max_pages = max_pages
        self.token = token
        self.transport = transport or urllib_transport(timeout_seconds)
        self.progress = progress

    def _report_progress(self, message: str) -> None:
        if self.progress is not None:
            self.progress(message)

    def _headers(self) -> dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-City-Id': self.city_id,
            'wfTToken': self.token,
            'User-Agent': USER_AGENT,
            'Referer': REFERER,
        }

    def _post(self, endpoint: str, payload: dict[str, Any], *, context: str) -> Any:
        request = ApiRequest(
            url=f'{self.api_origin}{API_PATH_PREFIX}{endpoint}',
            payload=payload,
            headers=self._headers(),
        )
        self._report_progress(f'requesting {context}')
        response = self.transport(request)
        if response.status_code != 200:
            raise SaleApiError(f'Upstream API returned HTTP {response.status_code} ({context}).')

        try:
            body = json.loads(response.body.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SaleApiError(f'Upstream API returned invalid JSON ({context}).') from exc

        if not body.get('success') or body.get('code') != 0:
            message = str(body.get('message') or 'unknown upstream error')
            raise SaleApiError(f'Upstream API error ({context}): {message}')
        return body.get('result')

    def fetch_all_projects(self) -> list[dict[str, Any]]:
        projects_by_id: dict[Any, dict[str, Any]] = {}

        for page_int in range(1, self.max_pages + 1):
            result = self.fetch_page(page_int)
            for item in result:
                project_id = item.get('id')
                key = project_id if project_id is not None else f'missing-id-{len(projects_by_id)}'
                projects_by_id.setdefault(key, item)

            if not result:
                return list(projects_by_id.values())

        raise SaleApiError(
            f'Upstream pagination did not stop before the configured page limit ({self.max_pages}). '
            'Increase the limit or inspect the API response.'
        )

    def fetch_page(self, page_int: int) -> list[dict[str, Any]]:
        request = ApiRequest(
            url=self.api_url,
            payload={'pageInt': page_int, 'pageSize': self.page_size},
            headers=self._headers(),
        )
        self._report_progress(f'projects page {page_int}')
        response = self.transport(request)
        if response.status_code != 200:
            raise SaleApiError(f'Upstream API returned HTTP {response.status_code} on page {page_int}.')

        try:
            payload = json.loads(response.body.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SaleApiError(f'Upstream API returned invalid JSON on page {page_int}.') from exc

        if not payload.get('success') or payload.get('code') != 0:
            message = str(payload.get('message') or 'unknown upstream error')
            raise SaleApiError(f'Upstream API error on page {page_int}: {message}')

        result = payload.get('result')
        if result is None:
            return []
        if not isinstance(result, list):
            raise SaleApiError(f'Upstream API result is not a list on page {page_int}.')

        return result

    def fetch_presale_certificates(self, project_id: int | str) -> list[dict[str, Any]]:
        result = self._post(
            'GetLouPanPreSaleCertificates',
            {'id': project_id},
            context=f'presale certificates for project {project_id}',
        )
        if not isinstance(result, list):
            raise SaleApiError(f'Upstream presale certificate result is not a list for project {project_id}.')
        return result

    def fetch_room_types(self, project_id: int | str) -> list[dict[str, Any]]:
        result = self._post(
            'GetLouPanRoomType',
            {'houseid': project_id},
            context=f'room types for project {project_id}',
        )
        if not isinstance(result, list):
            raise SaleApiError(f'Upstream room type result is not a list for project {project_id}.')
        return result

    def fetch_room_items(self, project_id: int | str, evidence_id: int | str) -> list[dict[str, Any]]:
        rooms: list[dict[str, Any]] = []
        observed_pages: int | None = None

        for page_int in range(1, self.max_pages + 1):
            payload = {
                'id': project_id,
                'saleStatus': 0,
                'abnormalStatus': -1,
                'buildId': 0,
                'sortStatus': 0,
                'evidenceId': evidence_id,
                'pageint': page_int,
                'pagesize': self.room_page_size,
            }
            result = self._post(
                'GetLouPanRoomItems',
                payload,
                context=f'rooms for project {project_id}, certificate {evidence_id}, page {page_int}',
            )
            if not isinstance(result, dict) or not isinstance(result.get('list'), list):
                raise SaleApiError(
                    f'Upstream room result is invalid for project {project_id}, certificate {evidence_id}.'
                )

            rooms.extend(item for item in result['list'] if isinstance(item, dict))
            try:
                total_pages = int(result.get('totalPages') or 0)
                total = int(result.get('total') or 0)
            except (TypeError, ValueError) as exc:
                raise SaleApiError(
                    f'Upstream room pagination is invalid for project {project_id}, certificate {evidence_id}.'
                ) from exc

            if total_pages > 0:
                if observed_pages is None:
                    observed_pages = total_pages
                elif total_pages != observed_pages:
                    raise SaleApiError(
                        f'Upstream room total page count changed for project {project_id}, certificate {evidence_id}.'
                    )
                if page_int >= total_pages:
                    break
            elif len(result['list']) < self.room_page_size:
                break

        else:
            raise SaleApiError(
                f'Upstream room pagination did not stop before the configured page limit ({self.max_pages}).'
            )

        expected_total = total if total_pages > 0 else None
        if expected_total is not None and len(rooms) != expected_total:
            raise SaleApiError(
                f'Upstream returned {len(rooms)} rooms instead of {expected_total} '
                f'for project {project_id}, certificate {evidence_id}.'
            )
        return rooms

    def fetch_wangqian_data(self, date: str) -> dict[str, Any]:
        combined: dict[str, Any] = {'list': []}
        observed_pages: int | None = None

        for page_int in range(1, self.max_pages + 1):
            result = self._post(
                'GetWangQianHouseData',
                {'time': date, 'pageint': page_int, 'pagesize': self.page_size},
                context=f'wangqian changes for {date}, page {page_int}',
            )
            if not isinstance(result, dict) or not isinstance(result.get('list'), list):
                raise SaleApiError(f'Upstream wangqian result is invalid for {date}.')

            combined['time'] = result.get('time') or date
            combined['totalSoldNum'] = result.get('totalSoldNum')
            combined['list'].extend(item for item in result['list'] if isinstance(item, dict))
            try:
                total_pages = int(result.get('totalPages') or 0)
            except (TypeError, ValueError) as exc:
                raise SaleApiError(f'Upstream wangqian pagination is invalid for {date}.') from exc

            if total_pages > 0:
                if observed_pages is None:
                    observed_pages = total_pages
                elif total_pages != observed_pages:
                    raise SaleApiError(f'Upstream wangqian total page count changed for {date}.')
                if page_int >= total_pages:
                    break
            elif len(result['list']) < self.page_size:
                break
        else:
            raise SaleApiError(
                f'Upstream wangqian pagination did not stop before the configured page limit ({self.max_pages}).'
            )

        combined['totalPages'] = observed_pages or 1
        return combined
