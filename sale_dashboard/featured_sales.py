from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .design import APPLE_DESIGN_CSS
from .featured import split_featured_projects
from .render import esc, integer


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _room(room: dict[str, Any]) -> dict[str, Any] | None:
    if room.get('saleStatus') != 1:
        return None
    return {
        'unitName': room.get('unitName'),
        'floor': room.get('floor'),
        'roomName': room.get('roomName'),
        'area': room.get('area'),
        'price': room.get('price'),
        'totalPrice': room.get('totalPrice'),
    }


def _building_snapshot(rooms: list[dict[str, Any]], build_name: Any, short_name: Any) -> dict[str, Any]:
    areas = [_number(room.get('area')) for room in rooms]
    total_prices = [_number(room.get('totalPrice')) for room in rooms]
    valid_areas = [value for value in areas if value is not None]
    valid_prices = [value for value in total_prices if value is not None]
    return {
        'buildName': build_name,
        'shortBuildName': short_name,
        'soldCount': len(rooms),
        'totalArea': sum(valid_areas),
        'totalPrice': sum(valid_prices),
        'averagePrice': sum(valid_prices) / sum(valid_areas) if valid_areas else None,
        'rooms': rooms,
    }


def build_featured_daily_sales(
    snapshot: dict[str, Any],
    featured_keys: list[str],
    *,
    generated_at: str,
    projects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_projects = snapshot.get('projects') if isinstance(snapshot.get('projects'), list) else snapshot.get('list')
    source_projects = source_projects if isinstance(source_projects, list) else []
    source_project_ids = {str(item.get('id')) for item in source_projects if isinstance(item, dict)}
    featured_projects, _ = split_featured_projects(
        [item for item in source_projects if isinstance(item, dict)] + (projects or []),
        featured_keys,
    )

    project_reports: list[dict[str, Any]] = []
    for project in featured_projects:
        rooms_by_building: dict[tuple[Any, Any], list[dict[str, Any]]] = defaultdict(list)
        for source_room in project.get('roomList') or []:
            if not isinstance(source_room, dict):
                continue
            room = _room(source_room)
            if room is None:
                continue
            key = (source_room.get('buildName'), source_room.get('shortBuildName') or source_room.get('buildName'))
            rooms_by_building[key].append(room)

        buildings = [
            _building_snapshot(rooms, build_name, short_name)
            for (build_name, short_name), rooms in rooms_by_building.items()
        ]
        has_source = str(project.get('id')) in source_project_ids
        source_count = _number(project.get('soldNum')) if has_source else None
        sold_count = sum(building['soldCount'] for building in buildings)
        project_reports.append(
            {
                'projectId': project.get('id'),
                'name': project.get('name'),
                'soldCount': sold_count,
                'sourceSoldCount': int(source_count) if source_count is not None else None,
                'countMatchesSource': source_count is None or int(source_count) == sold_count,
                'buildings': sorted(buildings, key=lambda item: str(item.get('buildName') or '')),
            }
        )

    return {
        'version': 1,
        'status': snapshot.get('status') or 'ok',
        'message': snapshot.get('message'),
        'date': snapshot.get('date') or snapshot.get('time'),
        'generatedAt': generated_at,
        'totalSold': sum(project['soldCount'] for project in project_reports),
        'projects': project_reports,
    }


def _room_row(room: dict[str, Any]) -> str:
    def area(value: Any) -> str:
        parsed = _number(value)
        return f'{parsed:,.2f} ㎡' if parsed is not None else esc(value or '—')

    def money(value: Any, unit: str) -> str:
        parsed = _number(value)
        return f'{parsed:,.0f} {unit}' if parsed is not None else esc(value or '—')

    return (
        f'<tr><td>{esc(room.get("unitName") or "—")}</td>'
        f'<td>{esc(room.get("floor") or "—")}</td>'
        f'<td>{esc(room.get("roomName") or "—")}</td>'
        f'<td>{area(room.get("area"))}</td>'
        f'<td>{money(room.get("totalPrice"), "元")}</td>'
        f'<td>{money(room.get("price"), "元/㎡")}</td></tr>'
    )


def _project_html(project: dict[str, Any]) -> str:
    count_note = (
        f'<span class="pill">接口汇总 {integer(project.get("sourceSoldCount"))}</span>'
        if not project.get('countMatchesSource')
        else ''
    )
    buildings = []
    for building in project.get('buildings') or []:
        rooms = ''.join(_room_row(room) for room in building.get('rooms') or [])
        buildings.append(
            f'''<article class="building">
              <header><h3>{esc(building.get('buildName') or '未知楼栋')}</h3><span>{integer(building.get('soldCount'))} 套</span></header>
              <p>{esc(building.get('shortBuildName') or '—')}</p>
              <div class="table-wrap"><table>
                <thead><tr><th>单元</th><th>楼层</th><th>房号</th><th>面积</th><th>总价</th><th>单价</th></tr></thead>
                <tbody>{rooms}</tbody>
              </table></div>
            </article>'''
        )
    body = ''.join(buildings) or '<section class="empty">昨日无成交</section>'
    return (
        f'<article class="project"><header><div><p>Featured Project</p>'
        f'<h2>{esc(project.get("name") or "未知楼盘")}</h2></div>'
        f'<div><strong>{integer(project.get("soldCount"))} 套</strong>{count_note}</div></header>{body}</article>'
    )


def render_featured_daily_sales_page(report: dict[str, Any], history: list[dict[str, Any]]) -> str:
    projects = report.get('projects') if isinstance(report.get('projects'), list) else []
    history_rows: list[str] = []
    project_by_id = {str(project.get('projectId')): project for project in projects}
    for item in sorted(history, key=lambda value: str(value.get('date') or ''), reverse=True)[:30]:
        row_projects = item.get('projects') if isinstance(item.get('projects'), list) else []
        counts = {
            str(value.get('projectId')): value.get('soldCount')
            for value in row_projects
            if isinstance(value, dict)
        }
        cells = ''.join(f'<td>{integer(counts.get(project_id, 0))}</td>' for project_id in project_by_id)
        history_rows.append(
            f'<tr><th scope="row">{esc(item.get("date") or "未知日期")}</th>{cells}'
            f'<td>{integer(item.get("totalSold") or 0)}</td></tr>'
        )
    history_html = ''.join(history_rows) or '<tr><td colspan="2">暂无历史记录</td></tr>'
    history_heads = ''.join(
        f'<th scope="col">{esc(project.get("name") or project.get("projectId"))}</th>'
        for project in projects
    )
    status_html = (
        f'<section class="error" role="alert">昨日网签接口获取失败：{esc(report.get("message") or "未知错误")}</section>'
        if report.get('status') == 'error'
        else ''
    )
    projects_html = ''.join(_project_html(project) for project in projects if isinstance(project, dict))
    return f'''<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark"><meta name="description" content="重点楼盘昨日成交，按楼盘、楼栋与房号追踪。">
<title>重点楼盘昨日成交 · 武汉楼盘销控情报台</title>
<style>
:root{{--featured-surface:#f5f5f7;--featured-panel:#fff;--featured-ink:#1d1d1f;--featured-muted:#6e6e73;--featured-line:#d2d2d7;--featured-brand:#0071e3;--featured-ink-strong:#004478;--featured-shadow:0 12px 34px #00000012}}
@media (prefers-color-scheme:dark){{:root{{--featured-surface:#090c10;--featured-panel:#151a21;--featured-ink:#f5f5f7;--featured-muted:#a1a6ad;--featured-line:#2a333d;--featured-brand:#6cb8f6;--featured-ink-strong:#a8d3f7;--featured-shadow:0 14px 38px #00000073}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--featured-surface);color:var(--featured-ink);font:15px/1.58 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}}.shell{{max-width:1180px;margin:0 auto;padding:0 clamp(15px,3vw,36px) 70px}}.breadcrumb{{padding:25px 0 13px;color:var(--featured-muted);font-size:13px}}.breadcrumb a{{color:var(--featured-ink-strong);font-weight:760;text-decoration:none}}.hero{{display:flex;justify-content:space-between;gap:20px;align-items:end;padding:8px 0 23px;border-bottom:1px solid var(--featured-line)}}.eyebrow{{margin:0;color:var(--featured-brand);font-size:11px;font-weight:850;letter-spacing:.16em;text-transform:uppercase}}h1{{margin:7px 0 8px;font-size:clamp(28px,4.5vw,46px);letter-spacing:-.05em}}.subtitle{{margin:0;max-width:680px;color:var(--featured-muted)}}.kpi{{display:grid;gap:3px;min-width:150px;min-height:96px;padding:16px 18px;border:1px solid var(--featured-line);border-radius:18px;background:var(--featured-panel);box-shadow:var(--featured-shadow)}}.kpi span{{color:var(--featured-muted);font-size:12px}}.kpi strong{{font-size:31px;letter-spacing:-.04em}}.error{{margin:15px 0;padding:13px 16px;border-radius:16px;background:#b4231812;color:#b42318;font-weight:720}}.project,.building,.history{{margin-top:15px;border:1px solid var(--featured-line);border-radius:20px;background:var(--featured-panel);box-shadow:var(--featured-shadow);overflow:hidden}}.project>header,.building>header{{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:15px 17px;background:color-mix(in srgb,var(--featured-panel) 88%,var(--featured-surface))}}.project h2,.building h3{{margin:0;letter-spacing:-.03em}}.project header p{{margin:0;color:var(--featured-brand);font-size:10px;font-weight:850;letter-spacing:.14em;text-transform:uppercase}}.project header strong,.building header span{{color:var(--featured-ink-strong);font-size:15px;font-weight:820}}.pill{{display:inline-flex;margin-left:7px;padding:3px 8px;border-radius:999px;background:color-mix(in srgb,#b42318 10%,var(--featured-panel));color:#b42318;font-size:11px;font-weight:780}}.building p{{margin:0;padding:8px 17px 0;color:var(--featured-muted);font-size:12px}}.table-wrap{{overflow-x:auto;padding-bottom:8px}}table{{width:100%;min-width:720px;border-collapse:collapse;font-size:13px}}th,td{{padding:10px 13px;border-top:1px solid var(--featured-line);text-align:left;white-space:nowrap}}thead th{{color:var(--featured-muted);font-size:11px}}.empty{{display:grid;min-height:160px;place-items:center;color:var(--featured-muted)}}.history h2{{margin:0;padding:16px 17px;font-size:17px}}:is(a):focus-visible{{outline:3px solid var(--featured-brand);outline-offset:3px}}@media (max-width:760px){{.hero{{align-items:start;flex-direction:column}}.kpi{{width:100%}}}}
{APPLE_DESIGN_CSS}</style></head>
<body><div class="shell">
<nav class="breadcrumb"><a href="../">全部楼盘</a><span>/</span><span>重点楼盘昨日成交</span></nav>
<header class="hero"><div><p class="eyebrow">Featured Daily Sales</p><h1>重点楼盘昨日成交</h1>
<p class="subtitle">按官方昨日网签明细统计，逐楼栋管理到单元、楼层与房号；数量同时与接口楼盘汇总值校验。</p></div>
<section class="kpi" aria-label="重点楼盘昨日总成交"><div><span>{esc(report.get('date') or '未知日期')} 成交</span><strong>{integer(report.get('totalSold'))}</strong></div></section></header>
{status_html}
{projects_html}
<section class="history"><h2>近 30 天汇总</h2><div class="table-wrap"><table>
<thead><tr><th scope="col">日期</th>{history_heads}<th scope="col">合计</th></tr></thead><tbody>{history_html}</tbody></table></div></section>
</div></body></html>'''


def load_featured_daily_sales_history(site_dir: Path | str) -> list[dict[str, Any]]:
    directory = Path(site_dir) / 'data' / 'featured-daily-sales'
    reports: list[dict[str, Any]] = []
    try:
        paths = list(directory.glob('*.json'))
    except OSError:
        return []
    for path in paths:
        if path.name == 'latest.json':
            continue
        try:
            report = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(report, dict) and report.get('date'):
            reports.append(report)
    return reports
