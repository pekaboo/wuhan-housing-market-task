import json
import tempfile
from pathlib import Path

from sale_dashboard.featured_sales import (
    build_featured_daily_sales,
    render_featured_daily_sales_page,
)
from sale_dashboard.generate import write_site


def test_builds_featured_daily_sales_by_building_and_keeps_zero_sale_projects():
    snapshot = {
        'date': '2026-10-31',
        'list': [
            {
                'id': 123,
                'name': '重点盘一',
                'soldNum': 3,
                'roomList': [
                    {'buildName': '1栋', 'shortBuildName': '1', 'unitName': '1', 'roomName': '101', 'area': 100, 'price': 10000, 'totalPrice': 1000000, 'saleStatus': 1},
                    {'buildName': '1栋', 'shortBuildName': '1', 'unitName': '2', 'roomName': '201', 'area': 100, 'price': 20000, 'totalPrice': 2000000, 'saleStatus': 1},
                    {'buildName': '2栋', 'shortBuildName': '2', 'unitName': '1', 'roomName': '301', 'area': 100, 'price': 30000, 'totalPrice': 3000000, 'saleStatus': 1},
                ],
            }
        ],
    }
    projects = [
        {'id': 123, 'name': '重点盘一'},
        {'id': 456, 'name': '重点盘二'},
    ]

    report = build_featured_daily_sales(
        snapshot,
        ['123', '重点盘二'],
        generated_at='2026-11-01 09:00:00',
        projects=projects,
    )

    assert report['date'] == '2026-10-31'
    assert report['totalSold'] == 3
    assert [project['name'] for project in report['projects']] == ['重点盘一', '重点盘二']
    assert report['projects'][0]['buildings'][0]['soldCount'] == 2
    assert report['projects'][1]['soldCount'] == 0
    assert report['projects'][1]['sourceSoldCount'] is None
    assert report['projects'][1]['countMatchesSource'] is True
    assert report['projects'][1]['buildings'] == []
    page = render_featured_daily_sales_page(report, [report])
    assert '重点楼盘昨日成交' in page
    assert '1栋' in page
    assert '昨日无成交' in page


def test_write_site_preserves_featured_daily_sales_history_and_writes_latest_page():
    with tempfile.TemporaryDirectory() as temporary_directory:
        site_dir = Path(temporary_directory)
        history_dir = site_dir / 'data' / 'featured-daily-sales'
        history_dir.mkdir(parents=True)
        old_report = {
            'version': 1,
            'status': 'ok',
            'date': '2026-10-30',
            'generatedAt': '2026-10-31 09:00:00',
            'totalSold': 2,
            'projects': [{'projectId': 123, 'name': '重点盘一', 'soldCount': 2, 'buildings': []}],
        }
        (history_dir / '2026-10-30.json').write_text(
            json.dumps(old_report, ensure_ascii=False),
            encoding='utf-8',
        )
        snapshot = {
            'date': '2026-10-31',
            'list': [
                {
                    'id': 123,
                    'name': '重点盘一',
                    'soldNum': 1,
                    'roomList': [
                        {'buildName': '1栋', 'unitName': '1', 'roomName': '101', 'area': 100, 'price': 10000, 'totalPrice': 1000000, 'saleStatus': 1}
                    ],
                }
            ],
        }

        write_site(
            [{'id': 123, 'name': '重点盘一'}],
            site_dir=site_dir,
            generated_at='2026-11-01 09:00:00',
            wangqian_snapshot=snapshot,
            featured_keys=['123'],
        )

        assert (history_dir / '2026-10-30.json').exists()
        assert (history_dir / '2026-10-31.json').exists()
        latest = json.loads((history_dir / 'latest.json').read_text(encoding='utf-8'))
        page = (site_dir / 'featured-daily-sales' / 'index.html').read_text(encoding='utf-8')
        assert latest['totalSold'] == 1
        assert '2026-10-30' in page
        assert '2026-10-31' in page
