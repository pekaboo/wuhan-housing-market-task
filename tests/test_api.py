import asyncio

import httpx

from sale_dashboard.api import create_app


def request(app, method: str, path: str):
    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
            return await getattr(client, method)(path)

    return asyncio.run(send())

class FakeService:
    def __init__(self):
        self.project_requests = 0
        self.detail_requests = 0
        self.warm_started = 0

    def projects(self, refresh=False):
        self.project_requests += 1
        return [
            {'id': 1, 'name': '实时楼盘', 'date': '2026-08-27', 'soldNum': 10, 'salePrice': 20000},
            {'id': 2, 'name': '下一个楼盘', 'date': '2026-08-27', 'soldNum': 20, 'salePrice': 21000},
        ]

    def project(self, project_id):
        self.detail_requests += 1
        return next((item for item in self.projects() if str(item.get('id')) == str(project_id)), None)

    def one_price(self, project_id, refresh=False):
        return {
            'status': 'complete',
            'projectId': project_id,
            'certificates': [
                {
                    'id': 900,
                    'name': '预售证',
                    'houseNum': 1,
                    'availableRoomNum': 1,
                    'soldNum': 0,
                    'rooms': [
                        {
                            'buildName': '1栋',
                            'unitName': '1单元',
                            'floorName': '1层',
                            'roomCode': '101',
                            'houseType': '三房',
                            'buildArea': '100',
                            'price': '20000',
                            'totalPrice': '2000000',
                            'saleStatus': 2,
                        }
                    ],
                }
            ],
        }

    def room_types(self, project_id, refresh=False):
        return {
            'status': 'complete',
            'projectId': project_id,
            'types': [
                {
                    'id': 800,
                    'houseType': '三房',
                    'buildingArea': '100',
                    'img': 'https://img.example.test/room.png',
                }
            ],
        }

    def start_warm(self):
        self.warm_started += 1
        return self.warm_status()

    def stop_warm(self):
        return self.warm_status()

    def warm_status(self):
        return {'state': 'running', 'total': 2, 'completed': 0, 'failed': 0, 'currentProject': None}


def test_api_serves_realtime_json_and_html():
    service = FakeService()
    app = create_app(service)

    assert request(app, 'get', '/health').json() == {'status': 'ok', 'upstreamConfigured': True, 'warm': service.warm_status()}
    assert request(app, 'get', '/api/projects').json()['projects'][0]['name'] == '实时楼盘'
    assert request(app, 'get', '/api/projects/1').json()['name'] == '实时楼盘'
    assert request(app, 'get', '/api/projects/1/one-price').json()['certificates'][0]['rooms'][0]['roomCode'] == '101'
    assert request(app, 'get', '/api/projects/1/room-types').json()['types'][0]['img'] == 'https://img.example.test/room.png'

    overview = request(app, 'get', '/').text
    detail = request(app, 'get', '/projects/1/').text
    assert '实时楼盘' in overview
    assert 'href="projects/2/"' in overview
    assert '实时楼盘' in detail
    assert 'https://img.example.test/room.png' in detail
    assert 'roomCode' not in detail


def test_api_can_start_and_inspect_background_warm():
    service = FakeService()
    app = create_app(service)

    response = request(app, 'post', '/api/warm')

    assert response.status_code == 202
    assert response.json()['state'] == 'running'
    assert service.warm_started == 1
    assert request(app, 'get', '/api/warm/status').json()['state'] == 'running'
