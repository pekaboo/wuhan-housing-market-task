from __future__ import annotations

from typing import Any

from .render import esc, integer


def _safe_id(value: Any) -> str:
    rendered = ''.join(character if character.isalnum() else '-' for character in str(value or '')).strip('-')
    return rendered or 'unknown'


def _text(value: Any) -> str:
    return esc(value if value not in (None, '') else '—')


def _area(value: Any) -> str:
    try:
        return f'{float(value):,.2f} ㎡'
    except (TypeError, ValueError):
        return _text(value)


def _money(value: Any, unit: str) -> str:
    try:
        return f'{float(value):,.0f} {unit}'
    except (TypeError, ValueError):
        return _text(value)


def _room_rows(project: dict[str, Any]) -> str:
    rooms = project.get('roomList') or []
    if not isinstance(rooms, list) or not rooms:
        return '<tr><td colspan="10">暂无昨日网签房源</td></tr>'
    rows: list[str] = []
    for room in rooms:
        if not isinstance(room, dict):
            continue
        sale_status = '已售' if room.get('saleStatus') == 1 else '可售' if room.get('saleStatus') == 2 else '—'
        abnormal = '异常' if room.get('abnormalStatus') == 1 else '—'
        rows.append(
            f'''<tr>
              <td>{_text(room.get('buildName'))}</td>
              <td>{_text(room.get('shortBuildName') or room.get('buildName'))}</td>
              <td>{_text(room.get('unitName'))}</td>
              <td>{_text(room.get('floor'))}</td>
              <td>{_text(room.get('roomName'))}</td>
              <td>{_area(room.get('area'))}</td>
              <td>{_money(room.get('price'), '元/㎡')}</td>
              <td>{_money(room.get('totalPrice'), '元')}</td>
              <td><span class="status sold">{esc(sale_status)}</span></td>
              <td>{esc(abnormal)}</td>
            </tr>'''
        )
    return ''.join(rows) or '<tr><td colspan="10">暂无昨日网签房源</td></tr>'


def render_wangqian_page(snapshot: dict[str, Any], *, generated_at: str) -> str:
    date = snapshot.get('date') or snapshot.get('time') or '未知日期'
    total_sold = snapshot.get('totalSoldNum')
    projects = snapshot.get('projects') if isinstance(snapshot.get('projects'), list) else snapshot.get('list')
    projects = projects if isinstance(projects, list) else []
    status = snapshot.get('status')

    sections: list[str] = []
    for item in projects:
        if not isinstance(item, dict):
            continue
        project_id = _safe_id(item.get('id'))
        sections.append(
            f'''<article class="project">
              <header><h2><a href="../projects/{esc(project_id)}/">{_text(item.get('name'))}</a></h2><span>网签 {integer(item.get('soldNum'))} 套</span></header>
              <div class="table-wrap"><table>
                <caption class="sr-only">{_text(item.get('name'))} 昨日网签房源</caption>
                <thead><tr><th>楼栋</th><th>简称</th><th>单元</th><th>楼层</th><th>房号</th><th>面积</th><th>单价</th><th>总价</th><th>状态</th><th>标记</th></tr></thead>
                <tbody>{_room_rows(item)}</tbody>
              </table></div>
            </article>'''
        )

    projects_html = ''.join(sections) or '<section class="empty">昨日没有网签房源记录。</section>'
    status_html = (
        f'<section class="error" role="alert">网签接口获取失败：{esc(snapshot.get("message") or "未知错误")}</section>'
        if status == 'error'
        else ''
    )
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="description" content="武汉楼盘昨日网签变化，按楼盘与房号展示面积、单价和总价。">
<title>昨日网签 · 武汉楼盘销控情报台</title>
<style>
:root{{--surface:#f4f7fb;--panel:#fff;--panel-soft:#eef3f9;--ink:#132233;--muted:#556879;--line:#d8e1ea;--brand:#0068a8;--brand-ink:#014d7d;--accent:#b98511;--focus:#2b7fd1;--shadow:0 12px 32px #17324d14}}
@media (prefers-color-scheme:dark){{:root{{--surface:#0a121b;--panel:#121d28;--panel-soft:#182633;--ink:#edf4fa;--muted:#a5b6c4;--line:#293b4a;--brand:#69b6e8;--brand-ink:#a9d8f6;--accent:#dfae4e;--focus:#8ccbf7;--shadow:0 12px 32px #00000059}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--surface);color:var(--ink);font:15px/1.58 "Avenir Next","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}}.shell{{max-width:1180px;margin:0 auto;padding:0 clamp(15px,3vw,36px) 66px}}.breadcrumb{{display:flex;gap:8px;align-items:center;padding:25px 0 13px;color:var(--muted);font-size:13px}}.breadcrumb a{{color:var(--brand-ink);font-weight:780;text-decoration:none}}.hero{{display:flex;justify-content:space-between;gap:20px;align-items:end;padding:8px 0 23px;border-bottom:1px solid var(--line)}}.eyebrow{{display:flex;gap:8px;color:var(--brand-ink);font-size:11px;font-weight:850;letter-spacing:.18em;text-transform:uppercase}}.eyebrow:before{{content:"";width:24px;height:2px;background:var(--accent)}}h1{{margin:7px 0 8px;font-size:clamp(28px,4.5vw,48px);line-height:1.05;letter-spacing:-.055em}}.subtitle{{max-width:650px;margin:0;color:var(--muted)}}.kpi{{display:flex;align-items:center;gap:11px;min-width:180px;min-height:104px;padding:16px;border:1px solid var(--line);border-radius:17px;background:var(--panel);box-shadow:var(--shadow)}}.kpi span{{display:block;color:var(--muted);font-size:12px}}.kpi strong{{display:block;margin-top:2px;font-size:31px;letter-spacing:-.05em}}.error{{margin:15px 0;padding:13px 16px;border-radius:14px;background:color-mix(in srgb,#b42318 10%,var(--panel));color:#b42318;font-weight:750}}.project{{overflow:hidden;margin-top:15px;border:1px solid var(--line);border-radius:18px;background:var(--panel);box-shadow:var(--shadow)}}.project header{{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:15px 16px;background:var(--panel-soft)}}.project h2{{margin:0;font-size:16px;letter-spacing:-.035em}}.project a{{color:var(--brand-ink);text-decoration:none}}.project header span{{flex:none;color:var(--brand-ink);font-size:12px;font-weight:800}}.table-wrap{{overflow-x:auto}}table{{width:100%;min-width:940px;border-collapse:collapse;font-size:13px}}th,td{{padding:11px 13px;border-top:1px solid var(--line);text-align:left;white-space:nowrap}}thead th{{background:var(--panel);color:var(--muted);font-size:11px}}.status{{display:inline-flex;height:24px;align-items:center;padding:0 8px;border-radius:999px;background:var(--panel-soft);color:var(--muted);font-size:11px;font-weight:800}}.status.sold{{color:#a35613;background:color-mix(in srgb,#a35613 12%,var(--panel))}}.empty{{display:grid;min-height:230px;place-items:center;margin-top:15px;border:1px dashed var(--line);border-radius:18px;background:var(--panel);color:var(--muted)}}.sr-only{{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}}:is(a,button,input):focus-visible{{outline:3px solid var(--focus);outline-offset:3px}}@media (prefers-color-scheme:dark){{.error{{background:#43110c;color:#ffab94}}.status.sold{{color:#f0b76a}}}}@media (max-width:760px){{.hero{{align-items:start;flex-direction:column}}.kpi{{width:100%}}.project header{{align-items:start;flex-direction:column}}}}
</style>
</head>
<body>
<div class="shell">
<nav class="breadcrumb" aria-label="面包屑"><a href="../">全部楼盘</a><span>/</span><span>昨日网签</span></nav>
<header class="hero">
  <div><p class="eyebrow">Daily Wangqian</p><h1>昨日网签</h1><p class="subtitle">按楼盘和房号展示 {esc(date)} 的网签变化，可追溯到楼栋、单元、楼层与价格。</p></div>
  <section class="kpi" aria-label="昨日网签总量"><div><span>网签房源</span><strong>{integer(total_sold)}</strong></div></section>
</header>
{status_html}
{projects_html}
<p class="subtitle" style="margin-top:24px">生产快照生成时间：{esc(generated_at)}；<a href="../data/wangqian/">查看 JSON 数据目录</a>。</p>
</div>
</body>
</html>'''
