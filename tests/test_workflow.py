from pathlib import Path


def test_workflow_publishes_the_complete_single_page_site_directory():
    workflow = Path('.github/workflows/daily-production-html.yml').read_text(encoding='utf-8')

    assert 'timeout-minutes: 15' in workflow
    assert '--site-output site' in workflow
    assert '--page-size 50' in workflow
    assert '--projects-per-page' not in workflow
    assert '--fetch-one-price' not in workflow
    assert '--reuse-enrichment' in workflow
    assert '--room-page-size 500' in workflow
    assert 'git add -A site' in workflow
    assert 'git add -A site index.html data' not in workflow
    assert 'upload-pages-artifact' not in workflow
    assert 'deploy-pages' not in workflow
    assert 'path: .' not in workflow
    assert 'gzip.decompress' in workflow


def test_daily_workflow_only_refreshes_homepage_and_reuses_full_data():
    workflow = Path('.github/workflows/daily-production-html.yml').read_text(encoding='utf-8')

    assert 'schedule:' in workflow
    assert 'cron: "0 0 * * *"' in workflow
    assert '--fetch-one-price' not in workflow
    assert '--reuse-enrichment' in workflow
    assert '--page-size 50' in workflow
    assert 'timeout-minutes: 15' in workflow
    assert 'gzip.decompress' in workflow


def test_full_enrichment_workflow_is_manual_and_batched():
    workflow = Path('.github/workflows/manual-full-enrichment.yml').read_text(encoding='utf-8')

    assert 'workflow_dispatch:' in workflow
    assert 'schedule:' not in workflow
    assert 'batch_size:' in workflow
    assert 'default: 100' in workflow
    assert '--fetch-one-price' in workflow
    assert '--enrichment-batch-size ${{ inputs.batch_size }}' in workflow
    assert 'timeout-minutes: 30' in workflow
    assert 'concurrency:' in workflow
    assert 'group: production-site' in workflow
    assert 'gzip.decompress' in workflow


def test_featured_project_list_is_available_to_scheduled_and_manual_actions():
    daily = Path('.github/workflows/daily-production-html.yml').read_text(encoding='utf-8')
    manual = Path('.github/workflows/manual-full-enrichment.yml').read_text(encoding='utf-8')
    featured = Path('config/featured-projects.txt').read_text(encoding='utf-8')

    assert '--refresh-featured' in daily
    assert '--featured-projects config/featured-projects.txt' in daily
    assert '--featured-projects config/featured-projects.txt' in manual
    assert '一行一个' in featured
    assert 'ID 或名称' in featured
    assert '806507620348020' in featured
    assert '795364598689861' in featured


def test_artifact_target_config_exists_and_holds_a_single_valid_value():
    value = Path('config/artifact-target.txt').read_text(encoding='utf-8')
    tokens = [line.strip().lower() for line in value.splitlines() if line.strip() and not line.strip().startswith('#')]
    assert len(tokens) == 1
    assert tokens[0] in ('local', 'external')


def test_daily_workflow_switches_artifact_target_between_local_and_external():
    workflow = Path('.github/workflows/daily-production-html.yml').read_text(encoding='utf-8')

    assert 'DATA_REPO: pekaboo/wuhan-housing-market-dashboard' in workflow
    assert 'config/artifact-target.txt' in workflow
    assert 'DATA_REPO_TOKEN' in workflow
    assert "steps.target.outputs.target == 'local'" in workflow
    assert "steps.target.outputs.target == 'external'" in workflow
    assert 'rm -rf site' in workflow
    assert 'mv site/.git .artifact-git' in workflow
    assert 'GIT_DIR' in workflow
    assert 'GIT_WORK_TREE' in workflow
    assert "git add -A -- . ':(exclude).github'" in workflow


def test_daily_workflow_fails_fast_on_bad_switch_and_scans_token_before_commit():
    workflow = Path('.github/workflows/daily-production-html.yml').read_text(encoding='utf-8')

    assert workflow.index('config/artifact-target.txt') < workflow.index('pytest -q')
    assert '::error::' in workflow
    assert workflow.index('gzip.decompress') < workflow.index('Commit production snapshot')


def test_manual_workflow_switches_artifact_target_between_local_and_external():
    workflow = Path('.github/workflows/manual-full-enrichment.yml').read_text(encoding='utf-8')

    assert 'DATA_REPO: pekaboo/wuhan-housing-market-dashboard' in workflow
    assert 'config/artifact-target.txt' in workflow
    assert 'DATA_REPO_TOKEN' in workflow
    assert "steps.target.outputs.target == 'local'" in workflow
    assert "steps.target.outputs.target == 'external'" in workflow
    assert 'rm -rf site' in workflow
    assert 'mv site/.git .artifact-git' in workflow
    assert 'GIT_DIR' in workflow
    assert 'GIT_WORK_TREE' in workflow
    assert "git add -A -- . ':(exclude).github'" in workflow
    assert workflow.index('gzip.decompress') < workflow.index('Commit enriched production snapshot')


def test_bootstrap_dashboard_repo_script_seeds_from_committed_site_snapshot():
    script = Path('scripts/bootstrap-dashboard-repo.sh').read_text(encoding='utf-8')

    assert 'set -euo pipefail' in script
    assert 'pekaboo/wuhan-housing-market-dashboard' in script
    assert 'git archive HEAD:site' in script
    assert 'refusing to seed' in script
