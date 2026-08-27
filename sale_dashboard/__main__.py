from __future__ import annotations

import argparse
import os
from pathlib import Path

from .client import (
    DEFAULT_API_URL,
    DEFAULT_CITY_ID,
    DEFAULT_MAX_PAGES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_TIMEOUT_SECONDS,
    SaleApiClient,
)
from .generate import write_outputs


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError('must be positive')
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Generate the Wuhan sale-control static dashboard')
    parser.add_argument('--output', default='index.html')
    parser.add_argument('--data-output', default='data/sale-data.json')
    parser.add_argument('--api-url', default=os.getenv('WFT_API_URL', DEFAULT_API_URL))
    parser.add_argument('--city-id', default=os.getenv('WFT_CITY_ID', DEFAULT_CITY_ID))
    parser.add_argument('--page-size', type=positive_int, default=int(os.getenv('WFT_PAGE_SIZE', DEFAULT_PAGE_SIZE)))
    parser.add_argument('--max-pages', type=positive_int, default=int(os.getenv('WFT_MAX_PAGES', DEFAULT_MAX_PAGES)))
    parser.add_argument('--timeout', type=float, default=float(os.getenv('WFT_REQUEST_TIMEOUT_SECONDS', DEFAULT_TIMEOUT_SECONDS)))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    token = os.getenv('WFT_TOKEN', '').strip()
    if not token:
        raise SystemExit('WFT_TOKEN is required')

    projects = SaleApiClient(
        token=token,
        api_url=args.api_url,
        city_id=args.city_id,
        page_size=args.page_size,
        max_pages=args.max_pages,
        timeout_seconds=args.timeout,
    ).fetch_all_projects()
    generated_at = write_outputs(projects, html_path=Path(args.output), data_path=Path(args.data_output))
    print(f'Generated {len(projects)} projects at {generated_at}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
