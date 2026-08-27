from __future__ import annotations

import html
import json
from datetime import datetime
from typing import Any


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


def collapsible_fields(project: dict[str, Any]) -> str:
    return (
        f'<details class="fields" open>'
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


def project_card(project: dict[str, Any], *, root_prefix: str = '') -> str:
    chart = latest_chart(project)
    detail_url = f'{root_prefix}projects/{project.get("id")}/'
    search = search_value(project)
    image = (
        f'''<a class="chart" href="{esc(chart['img'])}" target="_blank" rel="noopener noreferrer">
          <img src="{esc(chart['img'])}" alt="{esc(project.get('name'))} 标准销控图" loading="lazy" decoding="async">
          <span>数据日期 {esc(chart.get('time'))}</span>
        </a>'''
        if chart
        else '<div class="chart chart-empty"><span>暂无销控图</span></div>'
    )
    metrics = ''.join(
        [
            _metric('已售', integer(project.get('soldNum') or project.get('residenceSoldNum'))),
            _metric('均价', money(project.get('salePrice'))),
            _metric('总房源', integer(project.get('roomTotal'))),
        ]
    )
    return f'''<article class="project" role="listitem" data-name="{esc(project.get('name'))}" data-search="{esc(search)}" data-sold="{integer_value(project)}" data-price="{float_value(project)}" data-date="{esc(project.get('date') or '')}">
      <header>
        <h3><a class="detail-link" href="{esc(detail_url)}">{esc(project.get('name'))}</a></h3>
        <span class="date">{esc(project.get('date') or project.get('time'))}</span>
      </header>
      <div class="metrics">{metrics}</div>
      {collapsible_fields(project)}
      {image}
      <footer>
        <span>{esc(project.get('companyName'))}</span>
        <span>{esc(project.get('address'))}</span>
      </footer>
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


def page_link(current_page: int, target_page: int) -> str:
    if target_page == current_page:
        return '#'
    if current_page == 1:
        return './' if target_page == 1 else f'page/{target_page}/'
    if target_page == 1:
        return '../../'
    return './' if target_page == current_page else f'../{target_page}/'


def pagination(current_page: int, page_count: int) -> str:
    if page_count <= 1:
        return ''
    links = ''.join(
        f'<a href="{page_link(current_page, page)}"'
        f'{" aria-current=\"page\"" if page == current_page else ""}>'
        f'{page}</a>'
        for page in range(1, page_count + 1)
    )
    return (
        f'<nav class="pager" aria-label="楼盘分页">'
        f'<span>第 {current_page} / {page_count} 页</span><div>{links}</div></nav>'
    )


def render_html(
    projects: list[dict[str, Any]],
    *,
    generated_at: str,
    summary_projects: list[dict[str, Any]] | None = None,
    current_page: int = 1,
    page_count: int = 1,
    root_prefix: str = '',
) -> str:
    all_projects = projects if summary_projects is None else summary_projects
    summary = summarize(all_projects)
    cards = ''.join(project_card(project, root_prefix=root_prefix) for project in projects)
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
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="武汉楼盘销控数据每日快照，展示最新楼盘销售图、已售套数与均价。">
<meta name="color-scheme" content="light dark">
<title>武汉楼盘销控情报台</title>
<style>
:root{{--surface:#f4f7fb;--panel:#fff;--panel-soft:#eef3f9;--ink:#132233;--muted:#556879;--line:#d8e1ea;--brand:#0068a8;--brand-ink:#014d7d;--accent:#b98511;--focus:#2b7fd1;--shadow:0 12px 32px #17324d14}}
@media (prefers-color-scheme:dark){{:root{{--surface:#0a121b;--panel:#121d28;--panel-soft:#182633;--ink:#edf4fa;--muted:#a5b6c4;--line:#293b4a;--brand:#69b6e8;--brand-ink:#a9d8f6;--accent:#dfae4e;--focus:#8ccbf7;--shadow:0 12px 32px #00000059}}}}
*{{box-sizing:border-box}}html{{overflow-x:hidden}}body{{margin:0;background:var(--surface);color:var(--ink);font:15px/1.55 "Avenir Next","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;letter-spacing:.01em}}.shell{{max-width:1500px;margin:0 auto;padding:0 clamp(14px,3vw,38px) 72px}}.top{{display:flex;justify-content:space-between;gap:22px;align-items:flex-end;padding:clamp(28px,5vw,58px) 0 25px}}.eyebrow{{display:flex;gap:8px;color:var(--brand-ink);font-size:12px;font-weight:800;letter-spacing:.18em;text-transform:uppercase}}.eyebrow:before{{content:"";width:26px;height:2px;background:var(--accent)}}h1{{margin:8px 0 9px;font-size:clamp(29px,4.8vw,58px);line-height:1.02;letter-spacing:-.055em}}.subtitle{{max-width:640px;margin:0;color:var(--muted)}}.metadata{{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}}.pill{{display:inline-flex;align-items:center;height:30px;padding:0 11px;border:1px solid var(--line);border-radius:999px;background:var(--panel);color:var(--muted);font-size:12px;font-weight:650}}.kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:16px}}.kpi{{display:flex;min-height:103px;min-width:0;padding:17px;align-items:center;gap:13px;border:1px solid var(--line);border-radius:18px;background:var(--panel);box-shadow:var(--shadow)}}.kpi-icon{{width:27px;height:27px;flex:none;color:var(--brand)}}.kpi span{{display:block;color:var(--muted);font-size:12px}}.kpi strong{{display:block;margin-top:3px;font-size:clamp(20px,2vw,30px);line-height:1.12;letter-spacing:-.04em}}.controls{{position:sticky;top:0;z-index:10;padding:13px 0;background:color-mix(in srgb,var(--surface) 88%,transparent);backdrop-filter:blur(15px);border-bottom:1px solid transparent}}.control-inner{{display:grid;grid-template-columns:minmax(210px,1fr) auto;gap:9px;padding:11px;border:1px solid var(--line);border-radius:17px;background:var(--panel);box-shadow:var(--shadow)}}.search{{display:flex;align-items:center;gap:9px;min-width:0;padding:0 12px;border-radius:12px;background:var(--panel-soft)}}.search svg{{width:18px;height:18px;flex:none;color:var(--muted)}}input{{min-width:0;flex:1;height:43px;border:0;background:transparent;color:var(--ink);font:inherit;outline:none}}input::placeholder{{color:var(--muted)}}.sort{{display:flex;gap:6px;overflow:auto;scrollbar-width:none}}.sort::-webkit-scrollbar{{display:none}}button{{height:43px;border:0;border-radius:11px;background:var(--panel-soft);color:var(--muted);padding:0 11px;font:inherit;font-size:13px;font-weight:700;cursor:pointer;transition:color .2s ease,background .2s ease}}button[aria-pressed=true]{{background:var(--brand);color:#fff}}@media (prefers-color-scheme:dark){{button[aria-pressed=true]{{color:#07131d}}}}.pager{{display:flex;align-items:center;justify-content:space-between;gap:13px;margin:18px 0 0;padding:13px 15px;border:1px solid var(--line);border-radius:16px;background:var(--panel);box-shadow:var(--shadow)}}.pager>span{{color:var(--muted);font-size:13px;font-weight:700}}.pager div{{display:flex;gap:6px;flex-wrap:wrap}}.pager a{{display:grid;min-width:36px;height:36px;place-items:center;border:1px solid var(--line);border-radius:10px;background:var(--panel-soft);color:var(--ink);font-size:13px;font-weight:750;text-decoration:none;transition:color .2s ease,background .2s ease}}.pager a:hover{{color:var(--brand-ink);background:var(--panel)}}.pager a[aria-current=page]{{background:var(--brand);border-color:var(--brand);color:#fff}}@media (prefers-color-scheme:dark){{.pager a[aria-current=page]{{color:#07131d}}}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:15px;margin-top:17px}}.project{{min-width:0;overflow:hidden;border:1px solid var(--line);border-radius:19px;background:var(--panel);box-shadow:var(--shadow);transition:border-color .2s ease}}.project:hover{{border-color:var(--brand)}}.project header{{display:flex;justify-content:space-between;gap:12px;align-items:start;padding:17px 17px 13px}}h3{{margin:0;font-size:17px;line-height:1.38;letter-spacing:-.03em;overflow-wrap:anywhere}}.date{{flex:none;margin-top:2px;color:var(--brand-ink);font-size:12px;font-weight:750}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;padding:0 12px 13px;background:var(--panel-soft)}}.metric{{min-width:0;padding:10px;background:var(--panel)}}.metric span{{display:block;color:var(--muted);font-size:11px}}.metric strong{{display:block;margin-top:2px;font-size:14px;letter-spacing:-.02em}}.fields{{margin:0 12px 13px;border:1px solid var(--line);border-radius:13px;background:var(--panel-soft);color:var(--ink)}}.fields summary{{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:40px;padding:0 11px;color:var(--brand-ink);font-size:12px;font-weight:800;cursor:pointer;list-style:none}}.fields summary::-webkit-details-marker{{display:none}}.fields summary span{{min-width:24px;padding:2px 6px;border-radius:999px;background:var(--panel);color:var(--muted);text-align:center;font-size:11px}}.table-wrap{{max-height:290px;overflow:auto;border-top:1px solid var(--line)}}.field-table{{width:100%;min-width:430px;border-collapse:collapse;font-size:11px}}.field-table tr{{display:table-row}}.field-table th,.field-table td{{display:table-cell;padding:8px 10px;border-top:1px solid var(--line);text-align:left;vertical-align:top}}.field-table thead th{{position:sticky;top:0;background:var(--panel);color:var(--muted);font-size:10px;white-space:nowrap}}.field-table tbody th{{min-width:112px;background:var(--panel);color:var(--ink);font-weight:750}}.field-table tbody th span{{display:block}}.field-table tbody th code{{display:block;margin-top:2px;color:var(--muted);font-size:10px;overflow-wrap:anywhere}}.field-table td{{min-width:150px;max-width:300px;background:var(--panel)}}.field-table td span,.field-table td a{{display:block;color:var(--ink);overflow-wrap:anywhere}}.field-table td a{{color:var(--brand-ink)}}.chart{{position:relative;display:block;aspect-ratio:792/1000;background:var(--panel-soft);color:var(--brand-ink)}}.chart img{{display:block;width:100%;height:100%;object-fit:contain}}.chart span{{position:absolute;right:8px;bottom:8px;padding:4px 8px;border-radius:999px;background:color-mix(in srgb,var(--panel) 82%,transparent);font-size:11px;font-weight:700}}.chart-empty{{display:grid;place-items:center;color:var(--muted)}}.project footer{{display:flex;flex-direction:column;gap:3px;min-height:64px;padding:12px 17px 15px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}}.sr-only{{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}}.empty{{display:grid;min-height:250px;place-items:center;border:1px dashed var(--line);border-radius:20px;background:var(--panel);color:var(--muted)}}:is(a,button,input):focus-visible{{outline:3px solid var(--focus);outline-offset:3px}}@media (max-width:760px){{.top{{align-items:start;flex-direction:column}}.metadata{{justify-content:flex-start}}.kpis{{grid-template-columns:repeat(2,minmax(0,1fr))}}.control-inner{{grid-template-columns:1fr}}.sort{{width:100%}}}}@media (max-width:430px){{.kpis{{grid-template-columns:1fr}}.metrics{{grid-template-columns:1fr 1fr}}}}@media (prefers-reduced-motion:reduce){{*,*::before,*::after{{scroll-behavior:auto!important;transition-duration:.01ms!important}}}}
</style>
</head>
<body data-project-json="{embedded_projects}">
<div class="shell">
<header class="top">
  <div>
    <p class="eyebrow">Production Snapshot</p>
    <h1>武汉楼盘销控情报台</h1>
    <p class="subtitle">每日 08:00 自动获取生产销控数据，生成可检索、可排序的静态 HTML 快照。</p>
  </div>
  <div class="metadata"><span class="pill">城市 4201 · 武汉</span><span class="pill">生成 {esc(generated_at)}</span></div>
</header>
<section class="kpis" aria-label="市场概览">
  <div class="kpi">{_icon('building')}<div><span>监测楼盘</span><strong>{integer(summary['count'])}</strong></div></div>
  <div class="kpi">{_icon('sold')}<div><span>已售合计</span><strong>{integer(summary['sold'])}</strong></div></div>
  <div class="kpi">{_icon('price')}<div><span>样本均价</span><strong>{money(summary['averagePrice'])}</strong></div></div>
  <div class="kpi">{_icon('date')}<div><span>最新数据</span><strong>{esc(summary['latestDate'])}</strong></div></div>
</section>
<section class="controls" aria-label="本页筛选与排序">
  <div class="control-inner">
    <label class="search"><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-4.2-4.2"/></svg><span class="sr-only">搜索楼盘、开发商或地址</span><input data-role="project-search" type="search" placeholder="搜索本页楼盘、开发商或地址" autocomplete="off"></label>
    <div class="sort" role="group" aria-label="排序">
      <button type="button" data-role="sort-control" data-sort="default" aria-pressed="true">默认</button>
      <button type="button" data-role="sort-control" data-sort="sold" aria-pressed="false">已售优先</button>
      <button type="button" data-role="sort-control" data-sort="price-asc" aria-pressed="false">均价从低</button>
      <button type="button" data-role="sort-control" data-sort="price-desc" aria-pressed="false">均价从高</button>
    </div>
  </div>
</section>
<main class="grid" role="list" aria-live="polite">{cards or '<section class="empty">暂无楼盘数据</section>'}</main>
{pagination(current_page, page_count)}
</div>
<script>
(function(){{'use strict';const grid=document.querySelector('[role="list"]');const cards=[...grid.querySelectorAll('.project')];const search=document.querySelector('[data-role="project-search"]');let sortMode='default';function apply(){{const words=search.value.trim().toLowerCase().split(/\\s+/).filter(Boolean);cards.forEach(card=>{{const value=(card.dataset.search||'').toLowerCase();card.hidden=words.some(word=>!value.includes(word));}});if(sortMode==='sold')cards.sort((a,b)=>Number(b.dataset.sold)-Number(a.dataset.sold));else if(sortMode==='price-asc')cards.sort((a,b)=>Number(a.dataset.price)-Number(b.dataset.price));else if(sortMode==='price-desc')cards.sort((a,b)=>Number(b.dataset.price)-Number(a.dataset.price));else cards.sort((a,b)=>a.dataset.defaultIndex-b.dataset.defaultIndex);cards.forEach(card=>grid.append(card));}}cards.forEach((card,index)=>card.dataset.defaultIndex=index);search.addEventListener('input',apply);document.querySelectorAll('[data-role="sort-control"]').forEach(button=>button.addEventListener('click',()=>{{document.querySelectorAll('[data-role="sort-control"]').forEach(item=>item.setAttribute('aria-pressed','false'));button.setAttribute('aria-pressed','true');sortMode=button.dataset.sort;apply();}}));}})();
</script>
</body>
</html>'''
