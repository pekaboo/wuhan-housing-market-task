import html
import json
import re
import tempfile
import unittest
from pathlib import Path

from sale_dashboard.client import ApiRequest, ApiResponse, SaleApiClient, SaleApiError
from sale_dashboard.generate import write_outputs, write_site
from sale_dashboard.render import render_html
from sale_dashboard.site import render_project_page

TOKEN = 'secret-token'
API_URL = 'https://api.example.test/GetLouPanSaleImages'


def project(project_id: int, name: str, **overrides):
    data = {
        'id': project_id,
        'name': name,
        'date': '2026-08-27',
        'salePrice': 18500,
        'soldNum': 36,
        'soldChartImg': f'https://img.example.test/{project_id}.png',
    }
    data.update(overrides)
    return data


class SequenceTransport:
    def __init__(self, pages):
        self.pages = list(pages)
        self.requests = []

    def __call__(self, request: ApiRequest) -> ApiResponse:
        self.requests.append(request)
        payload = self.pages.pop(0)
        return ApiResponse(200, json.dumps(payload).encode('utf-8'), 'application/json')


class TestSaleApiClient(unittest.TestCase):
    def test_paginates_past_short_pages_until_the_upstream_ends_and_deduplicates_ids(self):
        transport = SequenceTransport(
            [
                {'result': [project(1, '壹号院'), project(2, '江岸府')], 'success': True, 'code': 0},
                {'result': [project(3, '光谷项目')], 'success': True, 'code': 0},
                {'result': [project(4, '最后项目'), project(1, '重复项目')], 'success': True, 'code': 0},
                {'result': None, 'success': True, 'code': 0},
            ]
        )
        progress: list[str] = []
        client = SaleApiClient(
            token=TOKEN,
            api_url=API_URL,
            page_size=2,
            transport=transport,
            progress=progress.append,
        )

        projects = client.fetch_all_projects()

        self.assertEqual([item['id'] for item in projects], [1, 2, 3, 4])
        self.assertEqual(progress, ['projects page 1', 'projects page 2', 'projects page 3', 'projects page 4'])
        self.assertEqual([request.payload['pageInt'] for request in transport.requests], [1, 2, 3, 4])
        self.assertEqual(transport.requests[0].headers['wfTToken'], TOKEN)
        self.assertEqual(transport.requests[0].headers['X-City-Id'], '4201')

    def test_rejects_upstream_error_without_exposing_token(self):
        transport = SequenceTransport([{'result': [], 'success': False, 'code': 401, 'message': 'token expired'}])
        client = SaleApiClient(token=TOKEN, api_url=API_URL, transport=transport)

        with self.assertRaisesRegex(SaleApiError, 'token expired') as raised:
            client.fetch_all_projects()

        self.assertNotIn(TOKEN, str(raised.exception))

    def test_stops_at_configured_page_limit(self):
        page = {'result': [project(1, '项目')], 'success': True, 'code': 0}
        transport = SequenceTransport([page, page])
        client = SaleApiClient(token=TOKEN, api_url=API_URL, page_size=1, max_pages=2, transport=transport)

        with self.assertRaisesRegex(SaleApiError, 'page limit'):
            client.fetch_all_projects()


class TestRenderHtml(unittest.TestCase):
    def setUp(self):
        self.projects = [
            project(1, '<script>unsafe</script>', salePrice=20000, soldNum=20),
            {
                **project(2, '光谷壹号院', salePrice=18000, soldNum=40),
                'soldChartImg': None,
                'soldChartList': [
                    {'img': 'https://img.example.test/old.png', 'time': '2026-08-01'},
                    {'img': 'https://img.example.test/new.png', 'time': '2026-08-27'},
                ],
            },
            project(3, '无图项目', soldChartImg=None),
        ]

    def test_renders_secure_accessible_dashboard(self):
        page = render_html(self.projects, generated_at='2026-08-27 08:00:00')

        self.assertIn('武汉楼盘销控情报台', page)
        self.assertIn('楼盘', page)
        self.assertIn('光谷壹号院', page)
        self.assertIn('https://img.example.test/1.png', page)
        self.assertIn('https://img.example.test/new.png', page)
        # 完整字段表会保留历史 URL；概览缩略图仍只使用最新一张。
        self.assertIn('https://img.example.test/old.png', page)
        self.assertNotIn('<img src="https://img.example.test/old.png"', page)
        self.assertNotIn('<script>unsafe</script>', page)
        self.assertIn('&lt;script&gt;unsafe&lt;/script&gt;', page)
        self.assertIn('暂无销控图', page)
        self.assertIn('20,000 元/㎡', page)
        self.assertIn('prefers-reduced-motion', page)
        self.assertIn('role="list"', page)
        self.assertNotIn(TOKEN, page)

    def test_generated_page_has_working_dashboard_script(self):
        page = render_html(self.projects, generated_at='2026-08-27 08:00:00')

        self.assertIn('data-role="project-search"', page)
        self.assertIn('data-role="sort-control"', page)
        self.assertIn('data-project-json=', page)

    def test_overview_card_displays_and_searches_every_available_field(self):
        rich_project = {
            **project(4, '完整数据楼盘'),
            'douYinSoldChartImg': 'https://img.example.test/4-douyin.png',
            'companyName': '测试开发商',
            'address': '武汉市测试区完整路 1 号',
            'greeningArea': '3000㎡',
            'roomTotal': 500,
            'residenceSoldNum': 100,
            'residenceRoomNum': 400,
            'otherSoldNum': 8,
            'otherRoomNum': 12,
            'areaTotal': '10000㎡',
            'bulidArea': '90000㎡',
            'greeningRate': '35%',
            'areaRate': '2.5',
            'completionTime': '2027-06-30',
            'deliveryTime': '2027-09-30',
            'futureMetric': '测试字段',
        }

        page = render_html([rich_project], generated_at='2026-08-27 08:00:00')

        self.assertIn('全部字段', page)
        self.assertIn('data-field="futureMetric"', page)
        self.assertIn('测试字段', page)
        self.assertIn('data-field="deliveryTime"', page)
        self.assertIn('2027-09-30', page)
        search_value = html.unescape(re.search(r'data-search="([^"]+)"', page).group(1))
        for expected in ('完整数据楼盘', '测试开发商', '武汉市测试区完整路 1 号', '测试字段', '4-douyin.png'):
            self.assertIn(expected, search_value)

    def test_detail_page_displays_both_chart_types_all_fields_and_raw_json(self):
        rich_project = {
            **project(4, '完整数据楼盘'),
            'soldChartImg': 'https://img.example.test/4-standard.png',
            'douYinSoldChartImg': 'https://img.example.test/4-douyin.png',
            'companyName': '<开发商>测试</开发商>',
            'address': '武汉市测试区完整路 1 号',
            'greeningArea': '3000㎡',
            'roomTotal': 500,
            'residenceSoldNum': 100,
            'residenceRoomNum': 400,
            'otherSoldNum': 8,
            'otherRoomNum': 12,
            'areaTotal': '10000㎡',
            'bulidArea': '90000㎡',
            'greeningRate': '35%',
            'areaRate': '2.5',
            'completionTime': '2027-06-30',
            'deliveryTime': '2027-09-30',
            'soldChartList': [
                {'img': 'https://img.example.test/4-old.png', 'time': '2026-08-01'},
                {'img': 'https://img.example.test/4-new.png', 'time': '2026-08-27'},
            ],
            'futureMetric': '测试字段',
        }

        page = render_project_page(
            rich_project,
            generated_at='2026-08-27 08:00:00',
            all_count=1,
        )

        self.assertIn('alt="完整数据楼盘 抖音版销控图"', page)
        self.assertIn('https://img.example.test/4-standard.png', page)
        self.assertIn('https://img.example.test/4-douyin.png', page)
        self.assertIn('https://img.example.test/4-old.png', page)
        self.assertIn('https://img.example.test/4-new.png', page)
        self.assertIn('全部字段', page)
        self.assertIn('data-field="futureMetric"', page)
        self.assertIn('data-field="bulidArea"', page)
        self.assertIn('建筑面积', page)
        self.assertIn('完整原始 JSON', page)
        self.assertIn('&lt;开发商&gt;测试&lt;/开发商&gt;', page)
        self.assertNotIn('<开发商>测试</开发商>', page)

    def test_overview_prioritizes_dense_data_and_opens_charts_in_a_dialog(self):
        rich_project = {
            **project(4, '高密度楼盘'),
            'companyName': '测试开发商',
            'address': '武汉市测试区密集路 1 号',
            'roomTotal': 500,
            'residenceRoomNum': 120,
            'completionTime': '2027-06-30',
        }

        page = render_html([rich_project], generated_at='2026-08-27 08:00:00')

        self.assertIn('class="project-primary"', page)
        self.assertIn('class="chart-thumb"', page)
        self.assertIn('data-role="chart-trigger"', page)
        self.assertIn('type="button"', page)
        self.assertIn('id="chart-dialog"', page)
        self.assertIn('data-role="chart-dialog-image"', page)
        self.assertIn('data-role="close-chart-dialog"', page)
        self.assertNotIn('class="chart" href="', page)
        self.assertIn('<details class="fields">', page)
        self.assertNotIn('<details class="fields" open>', page)
        self.assertIn('href="projects/4/"', page)
        self.assertIn('href="projects/4/#one-price"', page)
        self.assertIn('href="projects/4/#room-types"', page)
        self.assertIn('class="quick-link"', page)
        self.assertIn('class="project-facts"', page)
        self.assertIn('测试开发商', page)
        self.assertIn('武汉市测试区密集路 1 号', page)


class TestWriteOutputs(unittest.TestCase):
    def test_writes_html_and_atomic_json_snapshot(self):
        projects = [project(1, '测试项目')]

        with tempfile.TemporaryDirectory() as temporary_directory:
            html_path = Path(temporary_directory) / 'index.html'
            data_path = Path(temporary_directory) / 'data' / 'sale-data.json'
            generated_at = write_outputs(projects, html_path=html_path, data_path=data_path)

            self.assertTrue(html_path.exists())
            self.assertTrue(data_path.exists())
            self.assertIn('测试项目', html_path.read_text(encoding='utf-8'))
            snapshot = json.loads(data_path.read_text(encoding='utf-8'))
            self.assertEqual(snapshot['count'], 1)
            self.assertEqual(snapshot['projects'][0]['name'], '测试项目')
            self.assertEqual(snapshot['generatedAt'], generated_at)


class TestSinglePageSite(unittest.TestCase):
    def test_generates_one_overview_with_every_project_and_no_pager(self):
        projects = [
            project(1, '第一楼盘', soldNum=10, salePrice=10000),
            project(2, '第二楼盘', soldNum=20, salePrice=12000),
            project(3, '第三楼盘', soldNum=30, salePrice=13000),
            project(4, '第四楼盘', soldNum=40, salePrice=14000),
            {
                **project(5, '第五楼盘', soldNum=50, salePrice=15000, soldChartImg=None),
                'soldChartList': [
                    {'img': 'https://img.example.test/5-old.png', 'time': '2026-08-01'},
                    {'img': 'https://img.example.test/5-new.png', 'time': '2026-08-27'},
                ],
            },
            project(6, '第六楼盘', soldNum=60, salePrice=16000),
            project(7, '第七楼盘', soldNum=70, salePrice=17000),
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            site_dir = Path(temporary_directory) / 'site'
            (site_dir / 'stale').mkdir(parents=True)
            (site_dir / 'stale' / 'index.html').write_text('old', encoding='utf-8')

            paths = write_site(
                projects,
                site_dir=site_dir,
                generated_at='2026-08-27 08:00:00',
            )

            self.assertEqual(
                paths,
                [
                    Path('index.html'),
                    Path('projects/1/index.html'),
                    Path('projects/2/index.html'),
                    Path('projects/3/index.html'),
                    Path('projects/4/index.html'),
                    Path('projects/5/index.html'),
                    Path('projects/6/index.html'),
                    Path('projects/7/index.html'),
                ],
            )
            self.assertFalse((site_dir / 'stale').exists())
            self.assertFalse((site_dir / 'page').exists())

            overview = (site_dir / 'index.html').read_text(encoding='utf-8')
            fifth_detail = (site_dir / 'projects' / '5' / 'index.html').read_text(encoding='utf-8')

            for name in ('第一楼盘', '第二楼盘', '第三楼盘', '第四楼盘', '第五楼盘', '第六楼盘', '第七楼盘'):
                self.assertIn(name, overview)
            self.assertNotIn('class="pager"', overview)
            self.assertNotIn('楼盘分页', overview)
            self.assertNotIn('aria-current="page"', overview)
            self.assertIn('href="projects/5/"', overview)

            self.assertIn('第五楼盘', fifth_detail)
            self.assertIn('https://img.example.test/5-old.png', fifth_detail)
            self.assertIn('https://img.example.test/5-new.png', fifth_detail)
            self.assertIn('href="../../"', fifth_detail)
            self.assertIn('全部销控图', fifth_detail)

            snapshot = json.loads((site_dir / 'data' / 'sale-data.json').read_text(encoding='utf-8'))
            self.assertEqual(snapshot['count'], 7)
            self.assertEqual(snapshot['generatedAt'], '2026-08-27 08:00:00')


    def test_writes_incremental_enrichment_progress_for_the_next_action_run(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            site_dir = Path(temporary_directory)
            state = {
                'version': 1,
                'nextIndex': 4,
                'batchSize': 2,
                'lastBatchProjectIds': [3, 4],
            }

            write_site(
                [project(1, '壹号院'), project(2, '江岸府')],
                site_dir=site_dir,
                generated_at='2026-08-27 08:00:00',
                enrichment_state=state,
            )

            saved = json.loads((site_dir / 'data' / 'enrichment-state.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['version'], 1)
            self.assertEqual(saved['nextIndex'], 4)
            self.assertEqual(saved['batchSize'], 2)
            self.assertEqual(saved['lastBatchProjectIds'], [3, 4])
            self.assertEqual(saved['lastRunAt'], '2026-08-27 08:00:00')


if __name__ == '__main__':
    unittest.main()
