import json
import tempfile
import unittest
from pathlib import Path

from sale_dashboard.client import ApiRequest, ApiResponse, SaleApiClient, SaleApiError
from sale_dashboard.generate import write_outputs
from sale_dashboard.render import render_html

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
    def test_paginates_until_short_page_and_deduplicates_ids(self):
        transport = SequenceTransport(
            [
                {'result': [project(1, '壹号院'), project(2, '江岸府')], 'success': True, 'code': 0},
                {'result': [project(3, '光谷项目'), project(1, '重复项目')], 'success': True, 'code': 0},
                {'result': [project(4, '最后项目')], 'success': True, 'code': 0},
            ]
        )
        client = SaleApiClient(token=TOKEN, api_url=API_URL, page_size=2, transport=transport)

        projects = client.fetch_all_projects()

        self.assertEqual([item['id'] for item in projects], [1, 2, 3, 4])
        self.assertEqual([request.payload['pageInt'] for request in transport.requests], [1, 2, 3])
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
        self.assertNotIn('https://img.example.test/old.png', page)
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


if __name__ == '__main__':
    unittest.main()
