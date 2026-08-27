import gzip
import io
import json
import tempfile
from pathlib import Path

from sale_dashboard.__main__ import (
    DEFAULT_ENRICHMENT_BATCH_SIZE,
    build_parser,
    load_enrichment_state,
    load_existing_snapshots,
    make_progress_logger,
    select_enrichment_batch,
)


def test_progress_logger_flushes_action_visible_lines():
    output = io.StringIO()
    logger = make_progress_logger(output)

    logger('projects page 1')

    assert output.getvalue() == '[sale-dashboard] projects page 1\n'


def test_parser_supports_incremental_one_price_batches():
    args = build_parser().parse_args([])

    assert args.fetch_one_price is False
    assert args.enrichment_batch_size == DEFAULT_ENRICHMENT_BATCH_SIZE == 80


def test_enrichment_batch_rotates_and_wraps_without_losing_projects():
    projects = [{'id': index} for index in range(1, 6)]

    first, first_next = select_enrichment_batch(projects, 0, 2)
    second, second_next = select_enrichment_batch(projects, first_next, 2)
    wrapped, wrapped_next = select_enrichment_batch(projects, 4, 2)
    empty, empty_next = select_enrichment_batch([], 4, 2)

    assert [item['id'] for item in first] == [1, 2]
    assert first_next == 2
    assert [item['id'] for item in second] == [3, 4]
    assert second_next == 4
    assert [item['id'] for item in wrapped] == [5, 1]
    assert wrapped_next == 1
    assert empty == []
    assert empty_next == 0


def test_load_existing_snapshots_and_state_for_incremental_generation():
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        one_price_path = root / 'data' / 'projects' / '123' / 'one-price.json'
        room_type_path = root / 'data' / 'projects' / '123' / 'room-types.json'
        state_path = root / 'data' / 'enrichment-state.json'
        one_price_path.parent.mkdir(parents=True)
        room_type_path.parent.mkdir(parents=True, exist_ok=True)
        one_price_path.write_text(json.dumps({'projectId': 123, 'status': 'complete'}), encoding='utf-8')
        room_type_path.write_text(json.dumps({'projectId': 123, 'status': 'empty'}), encoding='utf-8')
        state_path.write_text(json.dumps({'version': 1, 'nextIndex': 240}), encoding='utf-8')

        one_price, room_types = load_existing_snapshots(root)
        state = load_enrichment_state(root)

        assert one_price == {'123': {'projectId': 123, 'status': 'complete'}}
        assert room_types == {'123': {'projectId': 123, 'status': 'empty'}}
        assert state == {'version': 1, 'nextIndex': 240}


def test_load_existing_snapshots_reads_compressed_one_price_json():
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        path = root / 'data' / 'projects' / '123' / 'one-price.json.gz'
        path.parent.mkdir(parents=True)
        payload = json.dumps({'projectId': 123, 'status': 'complete'}, separators=(',', ':')).encode('utf-8')
        path.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))

        one_price, room_types = load_existing_snapshots(root)

        assert one_price == {'123': {'projectId': 123, 'status': 'complete'}}
        assert room_types == {}


def test_invalid_or_missing_incremental_state_resets_safely():
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        state_path = root / 'data' / 'enrichment-state.json'
        state_path.parent.mkdir(parents=True)
        state_path.write_text(json.dumps({'version': 99, 'nextIndex': -3}), encoding='utf-8')

        assert load_enrichment_state(root) == {'version': 1, 'nextIndex': 0}
        assert load_enrichment_state(root / 'missing') == {'version': 1, 'nextIndex': 0}


def test_enrichment_batch_fetches_only_the_rotation_slice_and_keeps_old_data():
    from sale_dashboard.__main__ import enrich_project_batch
    from sale_dashboard.client import SaleApiError

    class RecordingClient:
        def __init__(self, fail_project_ids=frozenset()):
            self.project_ids = []
            self.fail_project_ids = fail_project_ids

        def fetch_presale_certificates(self, project_id):
            self.project_ids.append(project_id)
            if project_id in self.fail_project_ids:
                raise SaleApiError('upstream unavailable')
            return [{'id': f'cert-{project_id}'}]

        def fetch_room_items(self, project_id, evidence_id):
            return [{'roomName': f'room-{project_id}'}]

        def fetch_room_types(self, project_id):
            return [{'name': f'type-{project_id}'}]

    projects = [{'id': index, 'name': f'项目{index}'} for index in range(1, 5)]
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        data_dir = root / 'data' / 'projects'
        for project_id in (1, 2, 4):
            path = data_dir / str(project_id)
            path.mkdir(parents=True)
            (path / 'one-price.json').write_text(
                json.dumps({'projectId': project_id, 'status': 'complete', 'certificates': []}),
                encoding='utf-8',
            )
            (path / 'room-types.json').write_text(
                json.dumps({'projectId': project_id, 'status': 'complete', 'types': []}),
                encoding='utf-8',
            )
        (root / 'data' / 'enrichment-state.json').write_text(
            json.dumps({'version': 1, 'nextIndex': 2}),
            encoding='utf-8',
        )

        client = RecordingClient({4})
        logs = []
        one_price, room_types, state = enrich_project_batch(
            client,
            projects,
            site_dir=root,
            batch_size=2,
            progress=logs.append,
        )

        assert client.project_ids == [3, 4]
        assert one_price['1']['status'] == 'complete'
        assert one_price['3']['certificates'][0]['rooms'] == [{'roomName': 'room-3'}]
        assert one_price['4']['status'] == 'complete'
        assert room_types['2']['status'] == 'complete'
        assert room_types['4']['types'] == [{'name': 'type-4'}]
        assert state['nextIndex'] == 4
        assert state['lastBatchProjectIds'] == [3, 4]
        assert 'preserved the previous one-price snapshot' in '\n'.join(logs)
