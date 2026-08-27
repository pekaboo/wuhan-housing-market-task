import tempfile
from pathlib import Path

from sale_dashboard.cache import ResponseCache


def test_response_cache_round_trips_expires_and_persists():
    with tempfile.TemporaryDirectory() as temporary_directory:
        path = Path(temporary_directory) / 'responses.sqlite3'

        cache = ResponseCache(path)
        cache.set('projects', [{'id': 1}])
        assert cache.get('projects') == [{'id': 1}]
        assert cache.get('projects', ttl_seconds=0) is None
        cache.close()

        reopened = ResponseCache(path)
        assert reopened.get('projects') == [{'id': 1}]
        reopened.close()
