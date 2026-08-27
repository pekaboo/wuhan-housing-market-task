from __future__ import annotations

from typing import Any

from .render import esc, integer, money, summarize


def all_charts(project: dict[str, Any]) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []
    if project.get('soldChartImg'):
        charts.append({'img': project['soldChartImg'], 'time': project.get('date')})

    history = project.get('soldChartList')
    if isinstance(history, list):
        charts.extend(
            {
                'img': item.get('img'),
                'time': item.get('staticDate') or item.get('time'),
            }
            for item in history
            if isinstance(item, dict) and item.get('img')
        )

    unique_by_url: dict[str, dict[str, Any]] = {}
    for chart in charts:
        url = str(chart['img'])
        if url not in unique_by_url:
            unique_by_url[url] = chart
    return list(unique_by_url.values())


DETAIL_CSS = '''
:root{--surface:#f4f7fb;--panel:#fff;--panel-soft:#eef3f9;--ink:#132233;--muted:#556879;--line:#d8e1ea;--brand:#0068a8;--brand-ink:#014d7d;--accent:#b98511;--focus:#2b7fd1;--shadow:0 12px 32px #17324d14}
@media (prefers-color-scheme:dark){:root{--surface:#0a121b;--panel:#121d28;--panel-soft:#182633;--ink:#edf4fa;--muted:#a5b6c4;--line:#293b4a;--brand:#69b6e8;--brand-ink:#a9d8f6;--accent:#dfae4e;--focus:#8ccbf7;--shadow:0 12px 32px #00000059}}
*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--ink);font:15px/1.58 "Avenir Next","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}.shell{max-width:1120px;margin:0 auto;padding:0 clamp(15px,3vw,36px) 72px}.breadcrumb{display:flex;gap:9px;align-items:center;padding:26px 0 12px;color:var(--muted);font-size:13px}.breadcrumb a{color:var(--brand-ink);font-weight:750;text-decoration:none}.hero{padding:12px 0 22px;border-bottom:1px solid var(--line)}.eyebrow{display:flex;gap:8px;color:var(--brand-ink);font-size:11px;font-weight:850;letter-spacing:.18em;text-transform:uppercase}.eyebrow:before{content:"";width:24px;height:2px;background:var(--accent)}h1{margin:8px 0 8px;font-size:clamp(28px,4.5vw,50px);line-height:1.05;letter-spacing:-.055em}.description{max-width:650px;margin:0;color:var(--muted)}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:22px 0}.metric{padding:15px;border:1px solid var(--line);border-radius:16px;background:var(--panel);box-shadow:var(--shadow)}.metric span{display:block;color:var(--muted);font-size:12px}.metric strong{display:block;margin-top:3px;font-size:20px;letter-spacing:-.04em}.facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;margin:0 0 22px;background:var(--panel-soft);border:1px solid var(--line);border-radius:18px;overflow:hidden}.fact{padding:14px 16px;background:var(--panel)}.fact span{display:block;color:var(--muted);font-size:11px}.fact strong{display:block;margin-top:3px;font-size:14px;overflow-wrap:anywhere}h2{margin:32px 0 13px;font-size:20px;letter-spacing:-.04em}.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:15px}.chart{overflow:hidden;border:1px solid var(--line);border-radius:18px;background:var(--panel);box-shadow:var(--shadow);text-decoration:none}.chart img{display:block;width:100%;height:auto;background:var(--panel-soft)}.chart span{display:block;padding:11px 13px;color:var(--brand-ink);font-size:12px;font-weight:750}.empty{display:grid;min-height:230px;place-items:center;border:1px dashed var(--line);border-radius:18px;background:var(--panel);color:var(--muted)}.footer-nav{display:flex;justify-content:space-between;gap:10px;margin-top:30px}.footer-nav a{display:flex;align-items:center;justify-content:space-between;gap:12px;min-width:190px;padding:14px 16px;border:1px solid var(--line);border-radius:15px;background:var(--panel);color:var(--ink);font-weight:750;text-decoration:none;box-shadow:var(--shadow)}.footer-nav span:first-child{color:var(--muted);font-size:11px}.footer-nav .next{margin-left:auto;text-align:right}.footer-nav a:hover{border-color:var(--brand)}:is(a,input,button):focus-visible{outline:3px solid var(--focus);outline-offset:3px}@media (max-width:760px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.facts{grid-template-columns:1fr}.footer-nav{align-items:stretch;flex-direction:column}.footer-nav a{width:100%}.footer-nav .next{text-align:left}}@media (max-width:430px){.metrics{grid-template-columns:1fr}}@media (prefers-reduced-motion:reduce){*,*::before,*::after{transition-duration:.01ms!important}}
'''


def _fact(label: str, value: Any) -> str:
    return f'<div class="fact"><span>{label}</span><strong>{esc(value)}</strong></div>'


def render_project_page(
    project: dict[str, Any],
    *,
    generated_at: str,
    all_count: int,
    previous_project: dict[str, Any] | None = None,
    next_project: dict[str, Any] | None = None,
) -> str:
    charts = all_charts(project)
    charts_html = ''.join(
        f'''<a class="chart" href="{esc(chart['img'])}" target="_blank" rel="noopener noreferrer">
          <img src="{esc(chart['img'])}" alt="{esc(project.get('name'))} {esc(chart.get('time'))} 销控图" loading="lazy" decoding="async">
          <span>{esc(chart.get('time') or '数据日期未知')}</span>
        </a>'''
        for chart in charts
    ) or '<section class="empty">暂无销控图</section>'
    previous_html = (
        f'<a class="previous" href="../../projects/{esc(previous_project.get("id"))}/">'
        f'<span>上一个楼盘</span><span>{esc(previous_project.get("name"))}</span></a>'
        if previous_project
        else '<span></span>'
    )
    next_html = (
        f'<a class="next" href="../../projects/{esc(next_project.get("id"))}/">'
        f'<span>下一个楼盘</span><span>{esc(next_project.get("name"))}</span></a>'
        if next_project
        else '<span></span>'
    )
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="description" content="{esc(project.get('name'))} 楼盘销控详情，包含最新销控图、已售套数与均价。">
<title>{esc(project.get('name'))} · 楼盘销控详情</title>
<style>{DETAIL_CSS}</style>
</head>
<body>
<div class="shell">
<nav class="breadcrumb" aria-label="面包屑"><a href="../../">全部楼盘</a><span>/</span><span>{esc(project.get('name'))}</span></nav>
<header class="hero">
  <p class="eyebrow">Project Detail</p>
  <h1>{esc(project.get('name'))}</h1>
  <p class="description">共 {all_count} 个楼盘中的当前项目详情页；包含接口返回的全部历史销控图。</p>
</header>
<section class="metrics" aria-label="核心指标">
  <div class="metric"><span>数据日期</span><strong>{esc(project.get('date') or project.get('time'))}</strong></div>
  <div class="metric"><span>已售</span><strong>{integer(project.get('soldNum') or project.get('residenceSoldNum'))}</strong></div>
  <div class="metric"><span>均价</span><strong>{money(project.get('salePrice'))}</strong></div>
  <div class="metric"><span>总房源</span><strong>{integer(project.get('roomTotal'))}</strong></div>
</section>
<section class="facts" aria-label="项目信息">
  {_fact('开发商', project.get('companyName'))}
  {_fact('地址', project.get('address'))}
  {_fact('绿化率', project.get('greeningRate'))}
  {_fact('容积率', project.get('areaRate'))}
  {_fact('竣工时间', project.get('completionTime'))}
  {_fact('交付时间', project.get('deliveryTime'))}
</section>
<h2>全部历史销控图</h2>
<section class="charts">{charts_html}</section>
<nav class="footer-nav" aria-label="项目导航">{previous_html}{next_html}</nav>
<p class="description" style="margin-top:24px">生产快照生成时间：{esc(generated_at)}；<a href="../../data/sale-data.json">查看 JSON 数据</a>。</p>
</div>
</body>
</html>'''
