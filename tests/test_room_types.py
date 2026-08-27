import json
from pathlib import Path

from sale_dashboard.client import ApiRequest, ApiResponse, SaleApiClient
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


def room_type(type_id, **overrides):
    data = {
        'id': type_id,
        'name': '<script>unsafe type</script>',
        'sectionNum': 4,
        'roomLayout': '4室2厅3卫',
        'area': 139,
        'img': 'https://img.example.test/plan.png',
        'effectImage': None,
        'availableRoomNum': 39,
        'buildList': [
            {
                'buildShortName': '3#',
                'unitName': '1',
                'roomTotal': 48,
                'soldNum': 26,
                'availableRoomNum': 22,
                'abnormalRoomNum': 0,
                'evidenceName': '武房开预售[2026]202号',
                'floorTotal': 25,
                'buildType': '高层',
            }
        ],
    }
    data.update(overrides)
    return data


def test_client_fetches_room_types_with_house_id():
    transport = EndpointTransport(
        [{'success': True, 'code': 0, 'result': [room_type(900)]}]
    )
    client = SaleApiClient(token=TOKEN, api_url=API_URL, transport=transport)

    result = client.fetch_room_types(123)

    assert [item['id'] for item in result] == [900]
    assert transport.requests[0].url.endswith('/api/v1/data/GetLouPanRoomType')
    assert transport.requests[0].payload == {'houseid': 123}
    assert transport.requests[0].headers['wfTToken'] == TOKEN


def test_site_writes_room_type_json_and_expanding_detail_dialogs(tmp_path):
    snapshot = {'status': 'complete', 'types': [room_type(900)]}
    site_dir = tmp_path / 'site'

    write_site(
        [{'id': 123, 'name': '测试楼盘', 'date': '2026-08-27'}],
        site_dir=site_dir,
        generated_at='2026-08-27 14:00:00',
        room_type_snapshots={123: snapshot},
    )

    detail = (site_dir / 'projects' / '123' / 'index.html').read_text(encoding='utf-8')
    data = json.loads((site_dir / 'data' / 'projects' / '123' / 'room-types.json').read_text(encoding='utf-8'))

    assert data['status'] == 'complete'
    assert '户型图' in detail
    assert 'data-room-type-url="../../data/projects/123/room-types.json"' in detail
    assert 'data-role="room-type-trigger"' in detail
    assert '<dialog' in detail
    assert 'https://img.example.test/plan.png' in detail
    assert '&lt;script&gt;unsafe type&lt;/script&gt;' in detail
