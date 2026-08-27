from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .client import (
    DEFAULT_API_URL,
    DEFAULT_CITY_ID,
    DEFAULT_MAX_PAGES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_ROOM_PAGE_SIZE,
    DEFAULT_TIMEOUT_SECONDS,
    SaleApiClient,
    SaleApiError,
)
from .enrichment import build_one_price_snapshot
from .generate import write_site


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError('must be positive')
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generate the Wuhan sale-control static dashboard')
    parser.add_argument('--site-output', default=os.getenv('WFT_SITE_OUTPUT', 'site'))
    parser.add_argument(
        '--projects-per-page',
        type=positive_int,
        default=int(os.getenv('WFT_PROJECTS_PER_PAGE', '6')),
    )
    parser.add_argument('--api-url', default=os.getenv('WFT_API_URL', DEFAULT_API_URL))
    parser.add_argument('--city-id', default=os.getenv('WFT_CITY_ID', DEFAULT_CITY_ID))
    parser.add_argument('--page-size', type=positive_int, default=int(os.getenv('WFT_PAGE_SIZE', DEFAULT_PAGE_SIZE)))
    parser.add_argument(
        '--room-page-size',
        type=positive_int,
        default=int(os.getenv('WFT_ROOM_PAGE_SIZE', str(DEFAULT_ROOM_PAGE_SIZE))),
    )
    parser.add_argument('--max-pages', type=positive_int, default=int(os.getenv('WFT_MAX_PAGES', DEFAULT_MAX_PAGES)))
    parser.add_argument(
        '--timeout',
        type=float,
        default=float(os.getenv('WFT_REQUEST_TIMEOUT_SECONDS', DEFAULT_TIMEOUT_SECONDS)),
    )
    parser.add_argument(
        '--fetch-one-price',
        action='store_true',
        help='fetch presale certificates, room-level one-price data, and yesterday wangqian changes',
    )
    return parser


def _wangqian_request_date(now: datetime | None = None) -> str:
    current = now or datetime.now(ZoneInfo('Asia/Shanghai'))
    date = current - timedelta(days=1)
    return f'{date.year}-{date.month}-{date.day}'


def main() -> int:
    args = build_parser().parse_args()
    token = os.getenv('WFT_TOKEN', '').strip()
    if not token:
        raise SystemExit('WFT_TOKEN is required')

    client = SaleApiClient(
        token=token,
        api_url=args.api_url,
        city_id=args.city_id,
        page_size=args.page_size,
        room_page_size=args.room_page_size,
        max_pages=args.max_pages,
        timeout_seconds=args.timeout,
    )
    projects = client.fetch_all_projects()
    one_price_snapshots: dict[str, dict] | None = None
    wangqian_snapshot: dict | None = None

    if args.fetch_one_price:
        one_price_snapshots = {}
        for project in projects:
            project_id = project.get('id')
            if project_id is None:
                continue
            one_price_snapshots[str(project_id)] = build_one_price_snapshot(client, project_id)

        request_date = _wangqian_request_date()
        try:
            wangqian_snapshot = client.fetch_wangqian_data(request_date)
            wangqian_snapshot.setdefault('date', request_date)
        except SaleApiError as exc:
            # Keep the daily dashboard available when only the secondary wangqian API fails.
            wangqian_snapshot = {
                'status': 'error',
                'date': request_date,
                'message': str(exc),
                'totalSoldNum': None,
                'projects': [],
            }

    output_paths = write_site(
        projects,
        site_dir=Path(args.site_output),
        per_page=args.projects_per_page,
        one_price_snapshots=one_price_snapshots,
        wangqian_snapshot=wangqian_snapshot,
    )
    print(f'Generated {len(projects)} projects and {len(output_paths)} pages')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
