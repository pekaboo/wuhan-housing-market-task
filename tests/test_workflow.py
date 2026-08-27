from pathlib import Path


def test_workflow_publishes_the_complete_single_page_site_directory():
    workflow = Path('.github/workflows/daily-production-html.yml').read_text(encoding='utf-8')

    assert 'timeout-minutes: 30' in workflow
    assert '--site-output site' in workflow
    assert '--page-size 50' in workflow
    assert '--projects-per-page' not in workflow
    assert '--fetch-one-price' in workflow
    assert '--enrichment-batch-size 80' in workflow
    assert '--room-page-size 500' in workflow
    assert 'git add -A site' in workflow
    assert 'git add -A site index.html data' not in workflow
    assert 'path: site' in workflow
    assert 'path: .' not in workflow
    assert 'gzip.decompress' in workflow
