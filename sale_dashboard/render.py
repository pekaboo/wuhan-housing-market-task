from __future__ import annotations

import html
import json
from datetime import datetime
from typing import Any

from .design import APPLE_DESIGN_CSS


def esc(value: Any) -> str:
    return html.escape('—' if value in (None, '') else str(value), quote=True)


def integer(value: Any) -> str:
    if value in (None, ''):
        return '—'
    try:
        return f'{int(value):,}'
    except (TypeError, ValueError):
        return esc(value)


def money(value: Any) -> str:
    if value in (None, ''):
        return '—'
    try:
        return f'{float(value):,.0f} 元/㎡'
    except (TypeError, ValueError):
        return esc(value)


FIELD_LABELS = {
    'id': '项目 ID',
    'name': '楼盘名称',
    'date': '数据日期',
    'salePrice': '均价',
    'soldNum': '已售套数',
    'soldChartImg': '标准销控图',
    'douYinSoldChartImg': '抖音版销控图',
    'greeningArea': '绿化面积',
    'roomTotal': '总房源',
    'residenceSoldNum': '住宅已售',
    'residenceRoomNum': '住宅可售',
    'otherSoldNum': '其他已售',
    'otherRoomNum': '其他可售',
    'companyName': '开发商',
    'address': '地址',
    'areaTotal': '占地面积',
    'bulidArea': '建筑面积',
    'greeningRate': '绿化率',
    'areaRate': '容积率',
    'completionTime': '竣工时间',
    'deliveryTime': '交付时间',
    'soldChartList': '历史销控图',
    'saleChartUpdateTime': '销控图更新时间',
}


def field_label(key: str) -> str:
    return FIELD_LABELS.get(key, key)


def display_value(value: Any) -> str:
    if value in (None, ''):
        return '—'
    if isinstance(value, bool):
        return '是' if value else '否'
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    return str(value)


def search_value(project: dict[str, Any]) -> str:
    pieces: list[str] = []
    for key, value in project.items():
        rendered = display_value(value)
        if rendered != '—':
            pieces.extend((key, rendered))
    return ' '.join(pieces)


def _field_value(value: Any) -> str:
    rendered = display_value(value)
    if isinstance(value, str) and value.startswith(('http://', 'https://')):
        return f'<a href="{esc(value)}" target="_blank" rel="noopener noreferrer">{esc(value)}</a>'
    return f'<span>{esc(rendered)}</span>'


def field_rows(project: dict[str, Any]) -> str:
    return ''.join(
        f'<tr data-field="{esc(key)}">'
        f'<th scope="row"><span>{esc(field_label(key))}</span><code>{esc(key)}</code></th>'
        f'<td>{_field_value(value)}</td></tr>'
        for key, value in project.items()
    )


def collapsible_fields(project: dict[str, Any], *, open: bool = True) -> str:
    return (
        f'<details class="fields"{" open" if open else ""}>'
        f'<summary>全部字段<span>{len(project)}</span></summary>'
        f'<div class="table-wrap"><table class="field-table"><caption class="sr-only">全部接口字段</caption>'
        f'<thead><tr><th scope="col">字段</th><th scope="col">值</th></tr></thead>'
        f'<tbody>{field_rows(project)}</tbody></table></div></details>'
    )


def latest_chart(project: dict[str, Any]) -> dict[str, Any] | None:
    if project.get('soldChartImg'):
        return {'img': project['soldChartImg'], 'time': project.get('date')}

    charts = project.get('soldChartList')
    if not isinstance(charts, list):
        return None

    def timestamp(chart: dict[str, Any]) -> tuple[int, str]:
        value = str(chart.get('staticDate') or chart.get('time') or '')
        try:
            return datetime.fromisoformat(value).timestamp(), value
        except ValueError:
            return 0, value

    candidates = [chart for chart in charts if isinstance(chart, dict) and chart.get('img')]
    return max(candidates, key=timestamp, default=None)


def summarize(projects: list[dict[str, Any]]) -> dict[str, Any]:
    prices = [float(item['salePrice']) for item in projects if isinstance(item.get('salePrice'), (int, float))]
    sold = [int(item['soldNum']) for item in projects if isinstance(item.get('soldNum'), (int, float))]
    return {
        'count': len(projects),
        'sold': sum(sold),
        'averagePrice': sum(prices) / len(prices) if prices else None,
        'latestDate': max((str(item.get('date') or '') for item in projects), default='—') or '—',
    }


def summarize_public_one_price(snapshot: dict[str, Any]) -> dict[str, int] | None:
    if snapshot.get('status') == 'error':
        return {'status': 'error'}
    certificates = snapshot.get('certificates')
    rooms = [
        room
        for certificate in certificates if isinstance(certificate, dict)
        for room in certificate.get('rooms', []) if isinstance(room, dict)
    ]
    return {
        'certificates': len(certificates) if isinstance(certificates, list) else 0,
        'rooms': len(rooms),
        'sold': sum(room.get('saleStatus') == 1 for room in rooms),
        'available': sum(room.get('saleStatus') == 2 for room in rooms),
        'abnormal': sum(room.get('abnormalStatus') == 1 for room in rooms),
    }


def one_price_chip(summary: dict[str, int] | None) -> str:
    if summary is None:
        return '<span class="coverage-chip pending">一房一价未获取</span>'
    if summary.get('status') == 'error':
        return '<span class="coverage-chip pending">一房一价获取失败</span>'
    return (
        f'<span class="coverage-chip ready">一房一价 · {integer(summary.get("rooms"))} 房 / '
        f'可售 {integer(summary.get("available"))}</span>'
    )


def one_price_coverage(
    projects: list[dict[str, Any]],
    snapshots: dict[Any, dict[str, Any]] | None,
    *,
    root_prefix: str = '',
) -> str:
    if snapshots is None:
        return ''
    by_id = {str(key): value for key, value in snapshots.items()}
    covered = sum(
        by_id.get(str(project.get('id')), {}).get('status') == 'complete'
        for project in projects
    )
    total = len(projects)
    percentage = round(covered / total * 100) if total else 0
    detail = f'{covered}/{total} 个楼盘已取到预售证与房号明细'
    return f'''<section class="coverage" aria-label="一房一价覆盖">
  <div>
    <p>一房一价覆盖</p>
    <strong>{integer(covered)} <span>/ {integer(total)}</span></strong>
    <span>{esc(detail)}</span>
  </div>
  <div class="coverage-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{percentage}" aria-label="一房一价覆盖率 {percentage}%"><i style="width:{percentage}%"></i></div>
  <a class="wangqian-link" href="{esc(root_prefix) if root_prefix else ''}wangqian/">查看昨日网签</a>
</section>'''


def _icon(kind: str) -> str:
    paths = {
        'building': '<path d="M4 21h16M6 21V5a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v16M14 9h3a1 1 0 0 1 1 1v11M9 8h2M9 12h2M9 16h2"/>',
        'sold': '<path d="M4 18h4v-6H4v6Zm6 0h4V6h-4v12Zm6 0h4V9h-4v9Z"/><path d="M3 21h18"/>',
        'price': '<path d="M9 6h8m-8 5h8m-8 5h3"/><circle cx="6" cy="6" r="2"/><circle cx="6" cy="16" r="2"/>',
        'date': '<path d="M5 7h14v13H5zM8 4v4m8-4v4M5 12h14"/>',
    }
    return f'<svg class="kpi-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{paths[kind]}</svg>'


def _metric(label: str, value: str) -> str:
    return f'<div class="metric"><span>{label}</span><strong>{value}</strong></div>'


def project_card(
    project: dict[str, Any],
    *,
    root_prefix: str = '',
    one_price_summary: dict[str, int] | None = None,
) -> str:
    chart = latest_chart(project)
    detail_url = f'{root_prefix}projects/{project.get("id")}/'
    search = search_value(project)
    image = (
        f'''<button type="button" class="chart-thumb" data-role="chart-trigger" data-chart-url="{esc(chart['img'])}" data-chart-title="{esc(project.get('name'))} 标准销控图" data-chart-date="{esc(chart.get('time'))}" aria-haspopup="dialog">
          <img src="{esc(chart['img'])}" alt="{esc(project.get('name'))} 标准销控图" loading="lazy" decoding="async">
          <span>{esc(chart.get('time'))}</span>
        </button>'''
        if chart
        else '<div class="chart-thumb chart-empty"><span>暂无销控图</span></div>'
    )
    metrics = ''.join(
        [
            _metric('已售', integer(project.get('soldNum') or project.get('residenceSoldNum'))),
            _metric('均价', money(project.get('salePrice'))),
            _metric('总房源', integer(project.get('roomTotal'))),
        ]
    )
    facts = ''.join(
        f'<div><dt>{esc(label)}</dt><dd>{esc(project.get(key))}</dd></div>'
        for key, label in (
            ('companyName', '开发商'),
            ('address', '地址'),
            ('residenceRoomNum', '住宅可售'),
            ('completionTime', '竣工'),
        )
    )
    return f'''<article class="project" role="listitem" data-name="{esc(project.get('name'))}" data-search="{esc(search)}" data-sold="{integer_value(project)}" data-price="{float_value(project)}" data-date="{esc(project.get('date') or '')}">
      <div class="project-main">
        {image}
        <div class="project-primary">
          <header>
            <div>
              <h3><a class="detail-link" href="{esc(detail_url)}">{esc(project.get('name'))}</a></h3>
              <span class="date">{esc(project.get('date') or project.get('time'))}</span>
            </div>
            {one_price_chip(one_price_summary)}
          </header>
          <div class="metrics">{metrics}</div>
          <dl class="project-facts">{facts}</dl>
          <nav class="project-actions" aria-label="{esc(project.get('name'))}快捷入口">
            <a class="quick-link" href="{esc(detail_url)}">详情</a>
            <a class="quick-link" href="{esc(detail_url)}#one-price">一房一价</a>
            <a class="quick-link" href="{esc(detail_url)}#room-types">户型</a>
          </nav>
        </div>
      </div>
      {collapsible_fields(project, open=False)}
    </article>'''


def integer_value(project: dict[str, Any]) -> str:
    try:
        return str(int(project.get('soldNum') or project.get('residenceSoldNum') or 0))
    except (TypeError, ValueError):
        return '0'


def float_value(project: dict[str, Any]) -> str:
    try:
        return str(float(project.get('salePrice') or 0))
    except (TypeError, ValueError):
        return '0'


DASHBOARD_CSS = """
:root {
  color-scheme: light dark;
  --surface: #eef3f8;
  --panel: #fff;
  --panel-soft: #f3f7fb;
  --ink: #12212f;
  --muted: #536677;
  --line: #d6e0ea;
  --brand: #0068a8;
  --brand-ink: #014d7d;
  --accent: #b98511;
  --ok: #12805c;
  --focus: #2b7fd1;
  --shadow: 0 10px 28px #17324d12;
}
@media (prefers-color-scheme: dark) {
  :root {
    --surface: #08111a;
    --panel: #111d28;
    --panel-soft: #182634;
    --ink: #edf4fa;
    --muted: #a3b5c4;
    --line: #293b4a;
    --brand: #69b6e8;
    --brand-ink: #a9d8f6;
    --accent: #dfae4e;
    --ok: #67c79c;
    --focus: #8ccbf7;
    --shadow: 0 12px 34px #00000066;
  }
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background:
    radial-gradient(circle at 100% 0, color-mix(in srgb, var(--brand) 11%, transparent), transparent 32%),
    var(--surface);
  color: var(--ink);
  font: 13px/1.42 ui-sans-serif, system-ui, -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
body:has(dialog[open]) { overflow: hidden; }
.shell { width: min(1520px, 100%); margin: 0 auto; padding: 18px clamp(14px, 2.4vw, 34px) 44px; }
.top { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 10px 0 16px; }
.eyebrow { margin: 0 0 2px; color: var(--brand); font-size: 10px; font-weight: 800; letter-spacing: .11em; text-transform: uppercase; }
h1 { margin: 0; font-size: clamp(19px, 2.4vw, 27px); line-height: 1.1; letter-spacing: -.035em; }
.subtitle { display: none; margin: 3px 0 0; color: var(--muted); }
.metadata { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 5px; }
.pill { padding: 5px 10px; border: 1px solid var(--line); border-radius: 999px; background: color-mix(in srgb,var(--panel) 84%,transparent); color: var(--muted); font-size: 10px; font-weight: 650; white-space: nowrap; backdrop-filter:saturate(180%) blur(10px); }
.kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.kpi { display: flex; align-items: center; gap: 11px; min-height: 68px; padding: 12px 14px; border: 1px solid var(--line); border-radius: var(--radius-lg); background: var(--panel); box-shadow: var(--shadow); }
.kpi-icon { width: 20px; height: 20px; flex: 0 0 auto; color: var(--brand); }
.kpi span { display: block; color: var(--muted); font-size: 10px; font-weight:550; }
.kpi strong { display: block; font-size: 16px; line-height: 1.15; letter-spacing: -.02em; }
.coverage { display: grid; grid-template-columns: minmax(210px, 1fr) minmax(160px, 2fr) auto; align-items: center; gap: 10px; margin: 6px 0; padding: 7px 9px; border: 1px solid color-mix(in srgb, var(--brand) 24%, var(--line)); border-radius: 11px; background: color-mix(in srgb, var(--brand) 7%, var(--panel)); }
.coverage p { margin: 0; color: var(--muted); font-size: 10px; font-weight: 700; }
.coverage strong { font-size: 15px; }
.coverage strong span { color: var(--muted); font-size: 11px; }
.coverage > div:first-child > span { display: block; color: var(--muted); font-size: 10px; }
.coverage-bar { height: 7px; overflow: hidden; border-radius: 999px; background: color-mix(in srgb, var(--ink) 10%, transparent); }
.coverage-bar i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--brand), var(--ok)); }
.wangqian-link { color: var(--brand-ink); font-size: 11px; font-weight: 800; text-decoration: none; white-space: nowrap; }
.wangqian-link:hover { text-decoration: underline; }
.controls { position: sticky; top: 10px; z-index: 8; margin: 12px 0 14px; border: 1px solid color-mix(in srgb,var(--ink) 7%,transparent); border-radius: var(--radius-xl); background: color-mix(in srgb,var(--panel) 74%,transparent); backdrop-filter:saturate(180%) blur(20px); box-shadow: var(--shadow-hover); }
.control-inner { display: grid; grid-template-columns: minmax(260px, 1fr) auto; gap: 6px; padding: 7px; }
.search { position: relative; display: flex; align-items: center; }
.search svg { position: absolute; left: 11px; width: 14px; height: 14px; color: var(--muted); pointer-events: none; }
.search input { width: 100%; min-height: 38px; padding: 5px 10px 5px 31px; border: 1px solid transparent; border-radius: 999px; background: var(--panel-soft); color: var(--ink); font: inherit; }
.search input:focus { outline: 2px solid var(--focus); outline-offset: 1px; }
.sort { display:flex;align-items:center;gap:2px;padding:3px;border-radius:999px;background:var(--panel-soft); }
.sort button { min-height:32px;padding:4px 11px;border:0;border-radius:999px;background:transparent;color:var(--muted);font:inherit;font-size:11px;font-weight:650;cursor:pointer;transition:color .2s var(--ease-out),background .2s var(--ease-out),box-shadow .2s var(--ease-out);white-space:nowrap; }
.sort button[aria-pressed="true"] { background:var(--panel);color:var(--ink);box-shadow:0 1px 3px #0000001f; }
.grid { display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:14px;align-items:start; }
.project { min-width:0;overflow:clip;border:1px solid var(--line);border-radius:22px;background:var(--panel);box-shadow:var(--shadow);transition:border-color .22s var(--ease-out),box-shadow .22s var(--ease-out); }
.project:hover { border-color:var(--line-strong);box-shadow:var(--shadow-hover); }
.project-main { display: grid; grid-template-columns: 96px minmax(0, 1fr); gap: 12px; padding: 12px; }
.chart-thumb { position: relative; display: block; width: 96px; height: 128px; padding: 0; overflow: hidden; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--panel-soft); color: var(--brand-ink); cursor: zoom-in; }
.chart-thumb img { width: 100%; height: 100%; object-fit: contain; }
.chart-thumb span { position: absolute; right: 3px; bottom: 3px; max-width: calc(100% - 6px); padding: 2px 4px; overflow: hidden; border-radius: 5px; background: color-mix(in srgb, var(--panel) 86%, transparent); color: var(--ink); font-size: 8px; font-weight: 800; text-overflow: ellipsis; white-space: nowrap; }
.chart-empty { display: grid; place-items: center; color: var(--muted); font-size: 10px; cursor: default; }
.project-primary { min-width: 0; }
.project header { display: flex; align-items: start; justify-content: space-between; gap: 6px; }
.project h3 { margin: 0; font-size: 15px; line-height: 1.2; letter-spacing: -.025em; }
.detail-link { color: inherit; text-decoration: none; }
.detail-link::after { content: ""; position: absolute; inset: 0; }
.detail-link:hover { color: var(--brand-ink); }
.project header > div:first-child { position: relative; min-width: 0; }
.date { display: block; margin-top: 1px; color: var(--muted); font-size: 10px; }
.coverage-chip { flex: 0 0 auto; max-width: 135px; overflow: hidden; padding: 3px 5px; border-radius: 999px; color: var(--muted); background: var(--panel-soft); font-size: 9px; font-weight: 800; text-overflow: ellipsis; white-space: nowrap; }
.coverage-chip.ready { color: var(--ok); background: color-mix(in srgb, var(--ok) 12%, transparent); }
.metrics { position: relative; z-index: 1; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; margin: 6px 0; }
.metric { min-width: 0; padding: 6px 7px; border-radius: var(--radius-sm); background: var(--panel-soft); }
.metric span { display: block; color: var(--muted); font-size: 9px; }
.metric strong { display: block; overflow: hidden; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.project-facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 2px 8px; margin: 0; color: var(--muted); font-size: 10px; }
.project-facts > div { min-width: 0; }
.project-facts > div:last-child:nth-child(odd) { grid-column: 1 / -1; }
.project-facts dt { float: left; margin-right: 4px; color: color-mix(in srgb, var(--muted) 78%, transparent); }
.project-facts dt::after { content: "·"; margin-left: 2px; color: var(--line); }
.project-facts dd { display: inline; margin: 0; overflow-wrap: anywhere; }
.project-actions { position: relative; z-index: 2; display: flex; gap: 4px; margin-top: 6px; }
.quick-link { padding:4px 8px;border:1px solid color-mix(in srgb,var(--brand) 18%,transparent);border-radius:999px;background:color-mix(in srgb,var(--brand) 7%,transparent);color:var(--brand-ink);font-size:10px;font-weight:650;text-decoration:none;transition:background .2s var(--ease-out),border-color .2s var(--ease-out); }
.quick-link:hover { background: var(--brand); border-color:var(--brand); color:#fff; }
.fields { position: relative; z-index: 2; border-top: 1px solid var(--line); background: var(--panel-soft); }
.fields summary { padding: 5px 9px; color: var(--muted); font-size: 10px; font-weight: 800; cursor: pointer; list-style: none; }
.fields summary::-webkit-details-marker { display: none; }
.fields summary::after { content: "＋"; float: right; }
.fields[open] summary::after { content: "－"; }
.fields summary span { margin-left: 4px; color: var(--brand-ink); }
.table-wrap { max-height: 260px; overflow: auto; border-top: 1px solid var(--line); }
.field-table { width: 100%; border-collapse: collapse; background: var(--panel); font-size: 10px; }
.field-table th, .field-table td { padding: 4px 6px; border-top: 1px solid var(--line); text-align: left; vertical-align: top; }
.field-table th span { display: block; }
.field-table code { color: var(--muted); font-size: 9px; }
.field-table a { color: var(--brand-ink); overflow-wrap: anywhere; }
.chart-dialog { width: min(94vw, 1000px); max-height: 92vh; padding: 0; border: 1px solid color-mix(in srgb,var(--ink) 10%,transparent); border-radius: var(--radius-xl); background: var(--panel); color: var(--ink); box-shadow: 0 30px 90px #00000052; }
.chart-dialog::backdrop { background: #00000073; backdrop-filter:saturate(120%) blur(14px); }
.chart-dialog article { display: grid; grid-template-rows: auto minmax(0, 1fr); max-height: 92vh; }
.chart-dialog header { display: flex; align-items: start; justify-content: space-between; gap: 12px; padding: 10px 12px; border-bottom: 1px solid var(--line); }
.chart-dialog p { margin: 0; color: var(--brand); font-size: 10px; font-weight: 850; }
.chart-dialog h2 { margin: 1px 0 0; font-size: 16px; }
.chart-dialog [data-role="close-chart-dialog"] { min-height:34px;padding:4px 12px;border:0;border-radius:999px;background:var(--panel-soft);color:var(--ink);font:inherit;font-size:11px;font-weight:650;cursor:pointer; }
.chart-dialog img { display: block; width: 100%; max-height: calc(92vh - 54px); object-fit: contain; background: var(--panel-soft); }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
.empty { display: grid; min-height: 220px; place-items: center; border: 1px dashed var(--line); border-radius: 12px; background: var(--panel); color: var(--muted); }
a:hover, button:hover { transition: background-color .16s ease-out, color .16s ease-out, border-color .16s ease-out; }
:is(a, button, input, summary):focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
@media (max-width: 1000px) { .grid { grid-template-columns: minmax(0, 1fr); } .subtitle { display: block; } }
@media (max-width: 760px) {
  .top { align-items: start; flex-direction: column; }
  .metadata { justify-content: flex-start; }
  .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .coverage { grid-template-columns: minmax(0, 1fr) 58px auto; }
  .coverage > div:first-child > span { display: none; }
  .control-inner { grid-template-columns: minmax(0, 1fr); }
  .sort { width: 100%; overflow-x: auto; padding-bottom: 1px; }
  .chart-thumb { width: 78px; height: 106px; }
  .project-main { grid-template-columns: 78px minmax(0, 1fr); gap: 7px; padding: 7px; }
}
@media (max-width: 430px) {
  .shell { padding-inline: 8px; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; } }
"""

DASHBOARD_SCRIPT = """
(function() {
  'use strict';
  const grid = document.querySelector('[role="list"]');
  const cards = Array.from(grid.querySelectorAll('.project'));
  const search = document.querySelector('[data-role="project-search"]');
  const dialog = document.getElementById('chart-dialog');
  const dialogImage = dialog.querySelector('[data-role="chart-dialog-image"]');
  const dialogTitle = dialog.querySelector('[data-role="chart-dialog-title"]');
  const closeButton = dialog.querySelector('[data-role="close-chart-dialog"]');
  let sortMode = 'default';
  let opener = null;
  function apply() {
    const words = search.value.trim().toLowerCase().split(/\\s+/).filter(Boolean);
    cards.forEach(card => {
      const value = (card.dataset.search || '').toLowerCase();
      card.hidden = words.some(word => !value.includes(word));
    });
    if (sortMode === 'sold') cards.sort((a, b) => Number(b.dataset.sold) - Number(a.dataset.sold));
    else if (sortMode === 'price-asc') cards.sort((a, b) => Number(a.dataset.price) - Number(b.dataset.price));
    else if (sortMode === 'price-desc') cards.sort((a, b) => Number(b.dataset.price) - Number(a.dataset.price));
    else cards.sort((a, b) => Number(a.dataset.defaultIndex) - Number(b.dataset.defaultIndex));
    cards.forEach(card => grid.append(card));
  }
  cards.forEach((card, index) => { card.dataset.defaultIndex = String(index); });
  search.addEventListener('input', apply);
  document.querySelectorAll('[data-role="sort-control"]').forEach(button => {
    button.addEventListener('click', () => {
      document.querySelectorAll('[data-role="sort-control"]').forEach(item => item.setAttribute('aria-pressed', 'false'));
      button.setAttribute('aria-pressed', 'true');
      sortMode = button.dataset.sort;
      apply();
    });
  });
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('close', () => {
    dialogImage.removeAttribute('src');
    if (opener) { opener.focus(); opener = null; }
  });
  closeButton.addEventListener('click', () => dialog.close());
  document.addEventListener('click', event => {
    const trigger = event.target.closest('[data-role="chart-trigger"]');
    if (!trigger) return;
    event.preventDefault();
    opener = trigger;
    dialogImage.src = trigger.dataset.chartUrl || '';
    dialogImage.alt = trigger.dataset.chartTitle || '标准销控图';
    dialogTitle.textContent = trigger.dataset.chartTitle || '标准销控图';
    dialog.showModal();
  });
})();
"""


def render_html(
    projects: list[dict[str, Any]],
    *,
    generated_at: str,
    root_prefix: str = '',
    one_price_snapshots: dict[Any, dict[str, Any]] | None = None,
) -> str:
    summary = summarize(projects)
    snapshots_by_id = {str(key): value for key, value in (one_price_snapshots or {}).items()}
    cards = ''.join(
        project_card(
            project,
            root_prefix=root_prefix,
            one_price_summary=(
                summarize_public_one_price(snapshots_by_id[str(project.get('id'))])
                if str(project.get('id')) in snapshots_by_id
                else None
            ),
        )
        for project in projects
    )
    public_projects = [
        {
            'id': item.get('id'),
            'name': item.get('name'),
            'date': item.get('date') or item.get('time'),
            'soldNum': item.get('soldNum') or item.get('residenceSoldNum'),
            'salePrice': item.get('salePrice'),
            'chart': latest_chart(item),
        }
        for item in projects
    ]
    embedded_projects = esc(json.dumps(public_projects, ensure_ascii=False, separators=(',', ':')))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="武汉楼盘销控数据每日快照，展示最新楼盘销售图、已售套数与均价。">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="data:,">
<title>武汉楼盘销控情报台</title>
<style>{DASHBOARD_CSS}{APPLE_DESIGN_CSS}</style>
</head>
<body data-project-json="{embedded_projects}">
<div class="shell">
<header class="top">
  <div>
    <p class="eyebrow">Production Snapshot</p>
    <h1>武汉楼盘销控情报台</h1>
    <p class="subtitle">每日 08:00 自动获取生产数据；一房一价增量由手动全量任务维护。</p>
  </div>
  <div class="metadata"><span class="pill">城市 4201 · 武汉</span><span class="pill">生成 {esc(generated_at)}</span></div>
</header>
<section class="kpis" aria-label="市场概览">
  <div class="kpi">{_icon('building')}<div><span>监测楼盘</span><strong>{integer(summary['count'])}</strong></div></div>
  <div class="kpi">{_icon('sold')}<div><span>已售合计</span><strong>{integer(summary['sold'])}</strong></div></div>
  <div class="kpi">{_icon('price')}<div><span>样本均价</span><strong>{money(summary['averagePrice'])}</strong></div></div>
  <div class="kpi">{_icon('date')}<div><span>最新数据</span><strong>{esc(summary['latestDate'])}</strong></div></div>
</section>
{one_price_coverage(projects, one_price_snapshots, root_prefix=root_prefix)}
<section class="controls" aria-label="全部楼盘筛选与排序">
  <div class="control-inner">
    <label class="search"><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-4.2-4.2"/></svg><span class="sr-only">搜索楼盘、开发商或地址</span><input data-role="project-search" type="search" placeholder="搜索楼盘、开发商、地址、全部接口字段" autocomplete="off"></label>
    <div class="sort" role="group" aria-label="排序">
      <button type="button" data-role="sort-control" data-sort="default" aria-pressed="true">默认</button>
      <button type="button" data-role="sort-control" data-sort="sold" aria-pressed="false">已售优先</button>
      <button type="button" data-role="sort-control" data-sort="price-asc" aria-pressed="false">均价从低</button>
      <button type="button" data-role="sort-control" data-sort="price-desc" aria-pressed="false">均价从高</button>
    </div>
  </div>
</section>
<main class="grid" role="list" aria-live="polite">{cards or '<section class="empty">暂无楼盘数据</section>'}</main>
</div>
<dialog id="chart-dialog" class="chart-dialog" aria-labelledby="chart-dialog-title">
  <article>
    <header>
      <div><p>销控图查看</p><h2 id="chart-dialog-title" data-role="chart-dialog-title"></h2></div>
      <button type="button" data-role="close-chart-dialog">关闭</button>
    </header>
    <img data-role="chart-dialog-image" alt="">
  </article>
</dialog>
<script>{DASHBOARD_SCRIPT}</script>
</body>
</html>"""
