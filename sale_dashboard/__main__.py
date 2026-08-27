from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
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
from .enrichment import build_one_price_snapshot, build_room_type_snapshot, summarize_one_price
from .generate import write_site

DEFAULT_ENRICHMENT_BATCH_SIZE = 80
ENRICHMENT_STATE_VERSION = 1


def make_progress_logger(stream=None):
    output = stream or sys.stdout

    def log(message: str) -> None:
        print(f'[sale-dashboard] {message}', file=output, flush=True)

    return log


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError('must be positive')
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generate the Wuhan sale-control static dashboard')
    parser.add_argument('--site-output', default=os.getenv('WFT_SITE_OUTPUT', 'site'))
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
        help='fetch room types, presale certificates, room-level one-price data, and yesterday wangqian changes',
    )
    parser.add_argument(
        '--enrichment-batch-size',
        type=positive_int,
        default=int(os.getenv('WFT_ENRICHMENT_BATCH_SIZE', str(DEFAULT_ENRICHMENT_BATCH_SIZE))),
        help='number of projects to enrich per run; existing static JSON is reused for the rest',
    )
    return parser


def _wangqian_request_date(now: datetime | None = None) -> str:
    current = now or datetime.now(ZoneInfo('Asia/Shanghai'))
    date = current - timedelta(days=1)
    return f'{date.year}-{date.month}-{date.day}'



def load_enrichment_state(site_dir: Path | str) -> dict[str, int]:
    path = Path(site_dir) / 'data' / 'enrichment-state.json'
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'version': ENRICHMENT_STATE_VERSION, 'nextIndex': 0}
    next_index = value.get('nextIndex') if isinstance(value, dict) else None
    if value.get('version') != ENRICHMENT_STATE_VERSION or not isinstance(next_index, int) or next_index < 0:
        return {'version': ENRICHMENT_STATE_VERSION, 'nextIndex': 0}
    return {'version': ENRICHMENT_STATE_VERSION, 'nextIndex': next_index}


def load_existing_snapshots(
    site_dir: Path | str,
) -> tuple[dict[str, dict], dict[str, dict]]:
    root = Path(site_dir)
    one_price: dict[str, dict] = {}
    room_types: dict[str, dict] = {}
    for path in [*(root / 'data' / 'projects').glob('*/one-price.json'), *(root / 'data' / 'projects').glob('*/one-price.json.gz')]:
        try:
            content = path.read_bytes()
            if path.suffix == '.gz':
                content = gzip.decompress(content)
            snapshot = json.loads(content)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, gzip.BadGzipFile):
            continue
        project_id = snapshot.get('projectId') if isinstance(snapshot, dict) else None
        if project_id is not None:
            one_price[str(project_id)] = snapshot
    for path in (root / 'data' / 'projects').glob('*/room-types.json'):
        try:
            snapshot = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        project_id = snapshot.get('projectId') if isinstance(snapshot, dict) else None
        if project_id is not None:
            room_types[str(project_id)] = snapshot
    return one_price, room_types


def select_enrichment_batch(
    projects: list[dict],
    next_index: int,
    batch_size: int,
) -> tuple[list[dict], int]:
    if not projects:
        return [], 0
    if batch_size < 1:
        raise ValueError('batch size must be positive')
    count = len(projects)
    start = max(0, next_index) % count
    if batch_size >= count:
        return list(projects), 0
    remaining = count - start
    if batch_size <= remaining:
        return projects[start : start + batch_size], start + batch_size
    selected = projects[start:] + projects[: batch_size - remaining]
    return selected, (start + batch_size) % count


def enrich_project_batch(
    client: SaleApiClient,
    projects: list[dict],
    *,
    site_dir: Path | str,
    batch_size: int,
    progress,
) -> tuple[dict[str, dict], dict[str, dict], dict]:
    state = load_enrichment_state(site_dir)
    one_price_snapshots, room_type_snapshots = load_existing_snapshots(site_dir)
    batch, next_index = select_enrichment_batch(projects, state['nextIndex'], batch_size)
    progress(
        f'enriching batch of {len(batch)} projects from index {state["nextIndex"]}; '
        f'next batch starts at {next_index}'
    )
    positions = {str(project.get('id')): index for index, project in enumerate(projects, 1)}
    for project in batch:
        project_id = project.get('id')
        if project_id is None:
            progress('skipped a batch project without an id')
            continue
        project_name = project.get('name') or 'unnamed project'
        position = positions.get(str(project_id), 0)
        progress(f'[{position}/{len(projects)}] enriching {project_name} ({project_id})')

        new_one_price = build_one_price_snapshot(client, project_id)
        old_one_price = one_price_snapshots.get(str(project_id))
        if new_one_price.get('status') == 'error' and old_one_price and old_one_price.get('status') != 'error':
            progress(f'[{position}/{len(projects)}] preserved the previous one-price snapshot for {project_name}')
        else:
            one_price_snapshots[str(project_id)] = new_one_price

        new_room_types = build_room_type_snapshot(client, project_id)
        old_room_types = room_type_snapshots.get(str(project_id))
        if new_room_types.get('status') == 'error' and old_room_types and old_room_types.get('status') != 'error':
            progress(f'[{position}/{len(projects)}] preserved the previous room-type snapshot for {project_name}')
        else:
            room_type_snapshots[str(project_id)] = new_room_types

        one_price_summary = summarize_one_price(one_price_snapshots[str(project_id)])
        room_type_count = len(room_type_snapshots[str(project_id)].get('types') or [])
        progress(
            f'[{position}/{len(projects)}] completed {project_name}: '
            f'{one_price_summary["certificates"]} certificates, '
            f'{one_price_summary["rooms"]} rooms, {room_type_count} room types'
        )

    return one_price_snapshots, room_type_snapshots, {
        'version': ENRICHMENT_STATE_VERSION,
        'nextIndex': next_index,
        'batchSize': batch_size,
        'lastBatchProjectIds': [project.get('id') for project in batch if project.get('id') is not None],
    }

def main() -> int:
    args = build_parser().parse_args()
    token = os.getenv('WFT_TOKEN', '').strip()
    if not token:
        raise SystemExit('WFT_TOKEN is required')

    log = make_progress_logger()
    site_dir = Path(args.site_output)
    log('starting production snapshot generation')
    log(f'fetching project list with page size {args.page_size} and max pages {args.max_pages}')
    client = SaleApiClient(
        token=token,
        api_url=args.api_url,
        city_id=args.city_id,
        page_size=args.page_size,
        room_page_size=args.room_page_size,
        max_pages=args.max_pages,
        timeout_seconds=args.timeout,
        progress=log,
    )
    projects = client.fetch_all_projects()
    log(f'fetched {len(projects)} unique projects')
    one_price_snapshots: dict[str, dict] | None = None
    room_type_snapshots: dict[str, dict] | None = None
    wangqian_snapshot: dict | None = None
    enrichment_state: dict | None = None

    if args.fetch_one_price:
        one_price_snapshots, room_type_snapshots, enrichment_state = enrich_project_batch(
            client,
            projects,
            site_dir=site_dir,
            batch_size=args.enrichment_batch_size,
            progress=log,
        )
        request_date = _wangqian_request_date()
        log(f'fetching yesterday wangqian changes for {request_date}')
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
        site_dir=site_dir,
        one_price_snapshots=one_price_snapshots,
        room_type_snapshots=room_type_snapshots,
        wangqian_snapshot=wangqian_snapshot,
        enrichment_state=enrichment_state,
    )
    log(f'generated {len(projects)} projects and {len(output_paths)} files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
