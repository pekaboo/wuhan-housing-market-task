from pathlib import Path


def test_workflow_publishes_the_generated_multi_page_site_directory():
    workflow = Path('.github/workflows/daily-production-html.yml').read_text(encoding='utf-8')

    assert '--site-output site' in workflow
    assert '--projects-per-page 6' in workflow
    assert '--fetch-one-price' in workflow
    assert '--room-page-size 500' in workflow
    assert 'git add -A site' in workflow
    assert 'git add -A site index.html data' not in workflow
    assert 'path: site' in workflow
    assert 'path: .' not in workflow
