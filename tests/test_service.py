import tempfile
from pathlib import Path

from sale_dashboard.cache import ResponseCache
from sale_dashboard.service import DashboardService


class CountingClient:
    def __init__(self):
        self.project_calls = 0
        self.certificate_calls = 0
        self.room_type_calls = 0

    def fetch_all_projects(self):
        self.project_calls += 1
        return [{'id': 1, 'name': '可恢复楼盘'}]

    def fetch_presale_certificates(self, project_id):
        self.certificate_calls += 1
        return [{'id': 9, 'rooms': []}]

    def fetch_room_items(self, project_id, evidence_id):
        return []

    def fetch_room_types(self, project_id):
        self.room_type_calls += 1
        return [{'id': 8, 'img': 'https://img.example.test/room.png'}]


def test_dashboard_service_persists_responses_for_resume():
    with tempfile.TemporaryDirectory() as temporary_directory:
        cache_path = Path(temporary_directory) / 'cache.sqlite3'
        client = CountingClient()
        service = DashboardService(client, ResponseCache(cache_path), ttl_seconds=3600)

        assert service.projects() == [{'id': 1, 'name': '可恢复楼盘'}]
        assert service.room_types(1)['types'][0]['id'] == 8
        assert service.one_price(1)['certificates'][0]['id'] == 9
        assert (client.project_calls, client.room_type_calls, client.certificate_calls) == (1, 1, 1)

        assert service.projects() == [{'id': 1, 'name': '可恢复楼盘'}]
        assert service.room_types(1)['types'][0]['id'] == 8
        assert service.one_price(1)['certificates'][0]['id'] == 9
        assert (client.project_calls, client.room_type_calls, client.certificate_calls) == (1, 1, 1)

        resumed = DashboardService(CountingClient(), ResponseCache(cache_path), ttl_seconds=3600)
        assert resumed.one_price(1)['certificates'][0]['id'] == 9
        assert resumed.room_types(1)['types'][0]['id'] == 8


def test_dashboard_service_keeps_raw_enrichment_responses_for_mid_project_resume():
    with tempfile.TemporaryDirectory() as temporary_directory:
        client = CountingClient()
        cache = ResponseCache(Path(temporary_directory) / 'cache.sqlite3')
        service = DashboardService(client, cache, ttl_seconds=3600)

        service.one_price(1)
        cache.set(f'{service.namespace}:one-price:1', None)

        assert service.one_price(1)['certificates'][0]['id'] == 9
        assert client.certificate_calls == 1
