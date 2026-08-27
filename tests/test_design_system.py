import re

from sale_dashboard.render import render_html
from sale_dashboard.site import render_project_page
from sale_dashboard.wangqian import render_wangqian_page


def project_data():
    return {
        'id': 4,
        'name': '设计测试楼盘',
        'date': '2026-08-28',
        'soldNum': 36,
        'salePrice': 18500,
        'roomTotal': 300,
        'soldChartImg': 'https://img.example.test/standard.png',
        'douYinSoldChartImg': 'https://img.example.test/douyin.png',
    }


def test_all_pages_share_apple_commercial_design_tokens():
    overview = render_html([project_data()], generated_at='2026-08-28 08:00:00')
    detail = render_project_page(project_data(), generated_at='2026-08-28 08:00:00', all_count=1)
    wangqian = render_wangqian_page(
        {'date': '2026-08-27', 'totalSoldNum': 3, 'projects': []},
        generated_at='2026-08-28 08:00:00',
    )

    for page in (overview, detail, wangqian):
        assert '--design-system:apple-commercial' in page
        assert '--surface:#f5f5f7' in page
        assert '--ink:#1d1d1f' in page
        assert '--brand:#0071e3' in page
        assert '-apple-system,BlinkMacSystemFont' in page
        assert '--radius-lg:18px' in page
        assert '--radius-xl:24px' in page
        assert '--ease-out:cubic-bezier(.22,.61,.36,1)' in page
        assert 'prefers-reduced-motion:reduce' in page


def test_overview_uses_refined_bento_and_segmented_controls():
    page = render_html([project_data()], generated_at="2026-08-28 08:00:00")
    style = page.split("</style>", 1)[0]

    def rule(selector):
        match = re.search(re.escape(selector) + r"\s*\{([^}]+)\}", style)
        assert match
        return match.group(1).replace(" ", "")

    controls = rule(".controls")
    sort = rule(".sort")
    active_sort = rule('.sort button[aria-pressed="true"]')
    grid = rule(".grid")
    project = rule(".project")
    project_hover = rule(".project:hover")

    assert "position:sticky" in controls and "top:10px" in controls
    assert "backdrop-filter:saturate(180%)blur(20px)" in controls
    assert "border-radius:999px" in sort and "background:var(--panel-soft)" in sort
    assert "background:var(--panel)" in active_sort and "box-shadow:01px3px" in active_sort
    assert "minmax(380px,1fr)" in grid and "gap:14px" in grid
    assert "border-radius:22px" in project
    assert "border-color:var(--line-strong)" in project_hover
    assert "box-shadow:var(--shadow-hover)" in project_hover
    assert "transform:scale" not in style


def test_detail_images_open_in_apple_style_dialog_not_new_tab():
    page = render_project_page(project_data(), generated_at='2026-08-28 08:00:00', all_count=1)
    charts = page.split('<section class="charts"', 1)[1].split('</section>', 1)[0]

    assert 'data-role="chart-trigger"' in charts
    assert 'type="button"' in charts
    assert 'id="chart-dialog"' in page
    assert 'data-role="close-chart-dialog"' in page
    assert 'dialog.showModal()' in page
    assert 'target="_blank"' not in charts


def test_floor_map_supports_light_and_dark_apple_map_surfaces():
    page = render_project_page(project_data(), generated_at='2026-08-28 08:00:00', all_count=1)

    assert '--map-surface:#f0f2f5' in page
    assert '--map-panel:#ffffff' in page
    assert '@media (prefers-color-scheme:dark){.floor-results' in page
    assert '--map-surface:#0b141c' in page
    assert 'background:var(--map-surface)' in page
