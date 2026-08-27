import json
from pathlib import Path

from sale_dashboard.client import ApiRequest, ApiResponse, SaleApiClient, SaleApiError
from sale_dashboard.enrichment import build_one_price_snapshot, summarize_one_price
from sale_dashboard.generate import write_site

TOKEN = 'secret-token'
API_URL = 'https://api.example.test/api/v1/data/GetLouPanSaleImages'


class EndpointTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request: ApiRequest) -> ApiResponse:
        self.requests.append(request)
        payload = self.responses.pop(0)
        return ApiResponse(200, json.dumps(payload).encode('utf-8'), 'application/json')


def room(room_id, **overrides):
    data = {
        'id': room_id,
        'buildName': '3',
        'unitName': '1',
        'floor': '23',
        'roomName': '2303',
        'roomLayout': '三房',
        'saleStatus': 2,
        'abnormalStatus': 0,
        'price': 20000,
        'area': 100,
        'totalPrice': 2000000,
        'delivery': '全装修房',
    }
    data.update(overrides)
    return data


def certificate(certificate_id, **overrides):
    data = {
        'id': certificate_id,
        'name': '武房开预售[2026]001号',
        'houseNum': 3,
        'soldNum': 1,
        'availableRoomNum': 2,
        'abnormalNum': 0,
        'avgPrice': 20000,
        'time': '2026-01-01 00:00:00',
        'salePercentage': 0.3333,
    }
    data.update(overrides)
    return data


def successful_payload():
    return {
        'success': True,
        'code': 0,
        'result': [room(1), room(2, saleStatus=1, abnormalStatus=1), room(3)],
    }


def test_client_paginates_presale_certificates_and_rooms():
    transport = EndpointTransport(
        [
            {'success': True, 'code': 0, 'result': [certificate(900)]},
            {
                'success': True,
                'code': 0,
                'result': {'list': [room(1), room(2)], 'total': 3, 'totalPages': 2},
            },
            {
                'success': True,
                'code': 0,
                'result': {'list': [room(3)], 'total': 3, 'totalPages': 2},
            },
        ]
    )
    client = SaleApiClient(token=TOKEN, api_url=API_URL, room_page_size=2, transport=transport)

    certificates = client.fetch_presale_certificates(123)
    rooms = client.fetch_room_items(123, 900)

    assert [item['id'] for item in certificates] == [900]
    assert [item['id'] for item in rooms] == [1, 2, 3]
    assert transport.requests[0].url.endswith('/api/v1/data/GetLouPanPreSaleCertificates')
    assert transport.requests[1].payload == {
        'id': 123,
        'saleStatus': 0,
        'abnormalStatus': -1,
        'buildId': 0,
        'sortStatus': 0,
        'evidenceId': 900,
        'pageint': 1,
        'pagesize': 2,
    }
    assert [item.payload['pageint'] for item in transport.requests[1:]] == [1, 2]
    assert all(item.headers['wfTToken'] == TOKEN for item in transport.requests)


def test_client_paginates_wangqian_daily_changes():
    project_page = {'id': 123, 'name': '测试楼盘', 'soldNum': 4, 'roomList': [room(1)]}
    transport = EndpointTransport(
        [
            {
                'success': True,
                'code': 0,
                'result': {
                    'time': '2026-08-26 00:00:00',
                    'totalSoldNum': 7,
                    'totalPages': 2,
                    'list': [project_page],
                },
            },
            {
                'success': True,
                'code': 0,
                'result': {
                    'time': '2026-08-26 00:00:00',
                    'totalSoldNum': 7,
                    'totalPages': 2,
                    'list': [
                        {'id': 456, 'name': '第二个楼盘', 'soldNum': 3, 'roomList': [room(2)]}
                    ],
                },
            },
        ]
    )
    client = SaleApiClient(token=TOKEN, api_url=API_URL, transport=transport)

    result = client.fetch_wangqian_data('2026-8-26')

    assert result['totalSoldNum'] == 7
    assert [item['id'] for item in result['list']] == [123, 456]
    assert [request.payload['pageint'] for request in transport.requests] == [1, 2]
    assert transport.requests[0].url.endswith('/api/v1/data/GetWangQianHouseData')


def test_one_price_snapshot_is_complete_and_summarized():
    class Client:
        def fetch_presale_certificates(self, project_id):
            assert project_id == 123
            return [certificate(900)]

        def fetch_room_items(self, project_id, evidence_id):
            assert (project_id, evidence_id) == (123, 900)
            return successful_payload()['result']

    snapshot = build_one_price_snapshot(Client(), 123)

    assert snapshot['status'] == 'complete'
    assert snapshot['certificates'][0]['rooms'][1]['id'] == 2
    assert summarize_one_price(snapshot) == {
        'certificates': 1,
        'rooms': 3,
        'sold': 1,
        'available': 2,
        'abnormal': 1,
    }


def test_one_price_project_failure_is_explicit_and_token_free():
    class Client:
        def fetch_presale_certificates(self, project_id):
            raise SaleApiError('Upstream API returned HTTP 503.')

    snapshot = build_one_price_snapshot(Client(), 123)

    assert snapshot['status'] == 'error'
    assert snapshot['message'] == 'Upstream API returned HTTP 503.'
    assert TOKEN not in json.dumps(snapshot)


def test_site_writes_one_price_json_detail_ui_and_wangqian_page(tmp_path):
    one_price = {
        'status': 'complete',
        'certificates': [
            {
                **certificate(900),
                'name': '<script>unsafe</script>',
                'rooms': [room(1, roomName='<script>room</script>')],
            }
        ],
    }
    wangqian = {
        'date': '2026-08-26',
        'totalSoldNum': 1,
        'projects': [
            {'id': 123, 'name': '<script>unsafe</script>', 'soldNum': 1, 'roomList': [room(1)]}
        ],
    }
    site_dir = tmp_path / 'site'

    write_site(
        [{'id': 123, 'name': '测试楼盘', 'date': '2026-08-26', 'soldNum': 1, 'salePrice': 20000}],
        site_dir=site_dir,
        generated_at='2026-08-27 08:00:00',
        one_price_snapshots={123: one_price},
        wangqian_snapshot=wangqian,
    )

    detail = (site_dir / 'projects' / '123' / 'index.html').read_text(encoding='utf-8')
    index = (site_dir / 'index.html').read_text(encoding='utf-8')
    wangqian_page = (site_dir / 'wangqian' / 'index.html').read_text(encoding='utf-8')
    data = json.loads((site_dir / 'data' / 'projects' / '123' / 'one-price.json').read_text(encoding='utf-8'))
    wangqian_data = json.loads((site_dir / 'data' / 'wangqian' / '2026-08-26.json').read_text(encoding='utf-8'))

    assert data['status'] == 'complete'
    assert '一房一价' in detail
    assert 'data-one-price-url="../../data/projects/123/one-price.json"' in detail
    assert 'data-role="room-filter"' in detail
    assert '可售' in detail
    assert '已售' in detail
    assert '异常' in detail
    assert '&lt;script&gt;unsafe&lt;/script&gt;' in detail
    assert '一房一价覆盖' in index
    assert 'href="wangqian/"' in index
    assert '昨日网签' in wangqian_page
    assert 'href="../projects/123/"' in wangqian_page
    assert wangqian_data['totalSoldNum'] == 1


def test_site_renders_one_price_error_and_room_types_without_crashing(tmp_path):
    site_dir = tmp_path / 'site'

    write_site(
        [{'id': 123, 'name': '测试楼盘', 'date': '2026-08-27'}],
        site_dir=site_dir,
        generated_at='2026-08-27 14:00:00',
        one_price_snapshots={123: {'status': 'error', 'message': 'Upstream unavailable', 'certificates': []}},
        room_type_snapshots={123: {'status': 'complete', 'types': []}},
    )

    detail = (site_dir / 'projects' / '123' / 'index.html').read_text(encoding='utf-8')
    assert '接口获取失败：Upstream unavailable' in detail
    assert '户型图' in detail
