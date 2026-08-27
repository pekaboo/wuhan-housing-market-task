import gzip
import json
import re
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
    compressed = (site_dir / 'data' / 'projects' / '123' / 'one-price.json.gz').read_bytes()
    data = json.loads(gzip.decompress(compressed).decode(encoding='utf-8'))
    wangqian_data = json.loads((site_dir / 'data' / 'wangqian' / '2026-08-26.json').read_text(encoding='utf-8'))

    assert data['status'] == 'complete'
    assert '一房一价' in detail
    assert 'data-one-price-url="../../data/projects/123/one-price.json.gz"' in detail
    assert "DecompressionStream('gzip')" in detail
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


def test_one_price_ui_offers_table_and_floor_distribution_modes(tmp_path):
    one_price = {
        'status': 'complete',
        'certificates': [{**certificate(900), 'rooms': [room(1), room(2, saleStatus=1)]}],
    }
    site_dir = tmp_path / 'site'

    write_site(
        [{'id': 123, 'name': '测试楼盘', 'date': '2026-08-27'}],
        site_dir=site_dir,
        generated_at='2026-08-27 16:00:00',
        one_price_snapshots={123: one_price},
    )

    detail = (site_dir / 'projects' / '123' / 'index.html').read_text(encoding='utf-8')

    assert 'data-role="view-mode" data-mode="table" aria-pressed="true"' in detail
    assert 'data-role="view-mode" data-mode="floor" aria-pressed="false"' in detail
    assert '明细表' in detail
    assert '楼层分布' in detail
    assert 'data-role="floor-results" hidden' in detail
    assert 'data-role="building-filter"' in detail
    assert 'data-role="unit-filter"' in detail
    assert '相同价格同色；筛选外房源保留原位置并变成灰色方块' in detail

    for control in ('price-min', 'price-max', 'total-min', 'total-max'):
        assert f'data-role="{control}"' in detail

    script = detail.split('<script>', 1)[1]
    for behavior in (
        'function numericValue',
        'function priceKey',
        'function buildPricePalette',
        'function matrixKey',
        'function filterRooms',
        'function renderFloorView',
        'function roomCell',
        'priceGroups.get(priceKey',
        "style.setProperty('--price-color'",
        'data-price',
        'data-price-value',
        'data-total-price',
        'data-price-group',
        'floor-meta',
        "Number(room.abnormalStatus)===1",
        "hsl('+hue.toFixed(2)+',72%,'+light+'%)')",
        "data.status!=='complete'",
        "view!=='table'",
        'Number(room.saleStatus)',
    ):
        assert behavior in script

def test_one_price_floor_matrix_is_a_map_style_aligned_grid(tmp_path):
    one_price = {
        'status': 'complete',
        'certificates': [
            {
                **certificate(900),
                'rooms': [
                    room(1, buildName='2', unitName='1', floor='3', roomName='0301'),
                    room(2, buildName='10', unitName='1', floor='2', roomName='0201'),
                    room(3, buildName='2', unitName='2', floor='3', roomName='0302'),
                    room(4, floor='3', roomName='0303'),
                ],
            }
        ],
    }
    site_dir = tmp_path / 'site'

    write_site(
        [{'id': 123, 'name': '地图矩阵', 'date': '2026-08-27'}],
        site_dir=site_dir,
        generated_at='2026-08-27 23:00:00',
        one_price_snapshots={123: one_price},
    )

    detail = (site_dir / 'projects' / '123' / 'index.html').read_text(encoding='utf-8')

    assert '楼栋从左到右、楼层从上到下、同一楼层横向一排' in detail
    for marker in (
        'floor-stage floor-map',
        'floor-canvas',
        'floor-matrix',
        'floor-axis-y',
        'building-cell',
        'floor-row',
        'floor-column-head',
        'floor-missing',
        'matrixKey',
        'floorRooms.get(column.key)',
        'naturalCompare(left.building,right.building)',
        'unitName:text(room.unitName)',
    ):
        assert marker in detail

    matrix_rule = re.search(r'\.floor-matrix\{([^}]+)\}', detail)
    assert matrix_rule
    assert 'display:grid' in matrix_rule.group(1)
    assert 'grid-template-columns:var(--floor-axis) repeat(var(--floor-columns),var(--building-width))' in matrix_rule.group(1)
    assert 'grid-auto-rows:var(--floor-height)' in matrix_rule.group(1)
    assert 'grid-template-rows:58px repeat(var(--floor-count),var(--floor-height))' in matrix_rule.group(1)
    assert "style.setProperty('--floor-count'" in detail
    assert 'flex-wrap:wrap' not in matrix_rule.group(1)
    assert '.building-world{display:flex;flex-wrap:wrap' not in detail

    room_rule = re.search(r'\.room-cells\{([^}]+)\}', detail)
    assert room_rule
    assert 'grid-auto-flow:column' in room_rule.group(1)
    assert '--room-width:112px' in detail
    assert 'grid-auto-columns:var(--room-width)' in room_rule.group(1)
    assert 'grid-auto-rows:100%' in room_rule.group(1)
    assert 'height:calc(var(--floor-height) - 10px)' in room_rule.group(1)

    cell_rule = re.search(r'\.building-cell\{([^}]+)\}', detail)
    assert cell_rule
    assert 'height:var(--floor-height)' in cell_rule.group(1)
    assert 'overflow:hidden' in cell_rule.group(1)


def test_one_price_floor_map_preserves_grey_placeholders_and_large_project_overview(tmp_path):
    one_price = {
        'status': 'complete',
        'certificates': [
            {
                **certificate(900),
                'rooms': [
                    room(1, floor='8', roomName='0801', price=18000),
                    room(2, floor='8', roomName='0802', saleStatus=1, price=18000),
                    room(3, floor='7', roomName='0701', price=21000),
                ],
            }
        ],
    }
    site_dir = tmp_path / 'site'

    write_site(
        [{'id': 456, 'name': '筛选占位', 'date': '2026-08-27'}],
        site_dir=site_dir,
        generated_at='2026-08-28 08:00:00',
        one_price_snapshots={456: one_price},
    )

    detail = (site_dir / 'projects' / '456' / 'index.html').read_text(encoding='utf-8')

    assert 'data-role="zoom-in"' in detail
    assert '楼层从上到下、同一楼层横向一排' in detail
    assert 'function roomMatches(room)' in detail
    assert 'function scopedRooms()' in detail
    assert 'renderFloorView(visibleRooms)' in detail
    assert "article.classList.toggle('filtered-out',!roomMatches(room))" in detail
    assert '.floor-room.filtered-out>*{display:none}' in detail
    assert '.floor-room.filtered-out{width:100%;height:100%;min-height:100%' in detail
    assert 'priceGroups.get(priceKey(room))' in detail
    assert "swatch.className='price-chip'" in detail
    assert 'DETAIL_BUILDING_LIMIT=16' in detail
    assert 'building-overview' in detail
    assert 'focusBuilding(column)' in detail
    assert 'var columnFloors=floorRooms.get(column.key).size' in detail
    assert "block.style.setProperty('--floors',String(columnFloors))" in detail
    assert "columnFloors+' 层，'" in detail
    assert "block.className='building-column building-overview'" in detail


def test_one_price_floor_map_has_apple_maps_style_proportional_gestures(tmp_path):
    one_price = {
        'status': 'complete',
        'certificates': [
            {
                **certificate(901),
                'rooms': [
                    room(11, buildName='1', floor='9', roomName='0901', price=18000),
                    room(12, buildName='1', floor='9', roomName='0902', saleStatus=1, price=18000),
                    room(13, buildName='1', floor='8', roomName='0801', price=21000),
                ],
            }
        ],
    }
    site_dir = tmp_path / 'site'

    write_site(
        [{'id': 789, 'name': '地图手势', 'date': '2026-08-27'}],
        site_dir=site_dir,
        generated_at='2026-08-28 09:00:00',
        one_price_snapshots={789: one_price},
    )

    detail = (site_dir / 'projects' / '789' / 'index.html').read_text(encoding='utf-8')

    assert 'aria-label="楼层分布缩放控制"' in detail
    for control in ('zoom-in', 'zoom-out', 'reset-zoom', 'zoom-range', 'zoom-scale'):
        assert f'data-role="{control}"' in detail

    for marker in (
        'var viewState={scale:1,x:0,y:0}',
        'function applyViewState(canvas)',
        'function setZoom(value,anchorX,anchorY)',
        'function zoomAt(anchorX,anchorY,nextScale)',
        'var worldX=(anchorX-viewState.x)/viewState.scale',
        'viewState.x=anchorX-worldX*viewState.scale',
        "canvas.style.transform='translate3d('",
        "floorResults.style.setProperty('--floor-scale'",
        "floorResults.style.setProperty('--pan-x'",
        "floorResults.style.setProperty('--pan-y'",
        'Math.min(2.2,Math.max(.18',
        'function fitView(canvas)',
        'function resetView(canvas){fitView(canvas)}',
        'fitView(canvas)',
        '.floor-canvas{position:relative;',
        'transform-origin:0 0',
        'transform:translate3d(var(--pan-x),var(--pan-y),0) scale(var(--floor-scale))',
        '.floor-stage.floor-map{position:relative;',
        'overflow:hidden;',
        'touch-action:none',
        'activePointers',
        'pointerdown',
        'pointermove',
        'pointercancel',
        'wheel',
        'pinchState',
        'panBy(deltaX,deltaY)',
        "floorToolbar.hidden=view!=='floor'",
        '加号放大，减号缩小，0 复位',
    ):
        assert marker in detail

    assert not re.search(r'(?:^|[;{])zoom:', detail)
    assert 'camera-preset' not in detail
    assert 'camera-zoom' not in detail
    assert 'setCameraPreset' not in detail
    assert 'moveCamera' not in detail
    assert 'rotateX(' not in detail
    assert 'rotateY(' not in detail
    assert 'transform-style:preserve-3d' not in detail
    assert 'translateZ(' not in detail
    assert 'perspective:' not in detail
    assert 'matrix3d' not in detail
    assert 'room-3d' not in detail
    assert 'building-3d' not in detail
