from __future__ import annotations

from typing import Any

from .render import esc, integer, summarize_public_one_price


def one_price_section(snapshot: dict[str, Any] | None, data_url: str | None) -> str:
    if not data_url:
        return '<section class="one-price empty" aria-label="一房一价">未获取一房一价数据</section>'

    certificates = snapshot.get('certificates') if isinstance(snapshot, dict) else None
    certificates = certificates if isinstance(certificates, list) else []
    summary = summarize_public_one_price(snapshot or {})
    if summary is None or summary.get('status') == 'error':
        values = ('—', '—', '—', '—', '—')
    else:
        values = (
            integer(summary['certificates']),
            integer(summary['rooms']),
            integer(summary['available']),
            integer(summary['sold']),
            integer(summary['abnormal']),
        )
    labels = ('预售证', '房源', '可售', '已售', '异常')
    classes = ('', '', 'available', 'sold', 'abnormal')
    summary_html = ''.join(
        f'<div class="one-price-metric {class_name}"><span>{label}</span><strong>{value}</strong></div>'
        for label, value, class_name in zip(labels, values, classes, strict=True)
    )

    certificate_cards: list[str] = []
    for certificate in certificates:
        if not isinstance(certificate, dict):
            continue
        name = certificate.get('name') or f"预售证 {certificate.get('id') or '未知编号'}"
        certificate_cards.append(
            f'''<article class="certificate-card">
              <h3>{esc(name)}</h3>
              <dl>
                <div><dt>房源</dt><dd>{integer(certificate.get('houseNum'))}</dd></div>
                <div><dt>可售</dt><dd>{integer(certificate.get('availableRoomNum'))}</dd></div>
                <div><dt>已售</dt><dd>{integer(certificate.get('soldNum'))}</dd></div>
                <div><dt>去化</dt><dd>{esc(certificate.get('salePercentage') or '—')}</dd></div>
              </dl>
            </article>'''
        )

    status_html = ''
    if isinstance(snapshot, dict) and snapshot.get('status') == 'error':
        status_html = (
            f'<p class="one-price-error" role="alert">'
            f'接口获取失败：{esc(snapshot.get("message") or "未知错误")}</p>'
        )
    elif not certificates:
        status_html = '<p class="one-price-note">该楼盘暂无可展示的预售证明细。</p>'

    return f'''<section id="one-price" class="one-price" data-one-price-url="{esc(data_url)}" aria-labelledby="one-price-title">
      <div class="one-price-head">
        <div><h2 id="one-price-title">一房一价</h2><p>按预售证聚合房号、面积、单价、总价、销售与异常状态；支持明细表与真实楼层分布两种视图。</p></div>
        <a href="{esc(data_url)}" download>JSON 明细</a>
      </div>
{status_html}
      <div class="one-price-summary" data-role="one-price-summary">{summary_html}</div>
      <div class="room-controls">
        <div class="view-switch" role="group" aria-label="一房一价视图">
          <button type="button" data-role="view-mode" data-mode="table" aria-pressed="true">明细表</button>
          <button type="button" data-role="view-mode" data-mode="floor" aria-pressed="false">楼层分布</button>
        </div>
        <label>预售证<select data-role="certificate-filter" aria-label="筛选预售证"><option value="all">全部预售证</option></select></label>
        <label>楼栋<select data-role="building-filter" aria-label="筛选楼栋"><option value="all">全部楼栋</option></select></label>
        <label>单元<select data-role="unit-filter" aria-label="筛选单元"><option value="all">全部单元</option></select></label>
        <label>搜索<input data-role="room-search" type="search" placeholder="楼栋 / 单元 / 楼层 / 房号 / 户型" autocomplete="off"></label>
        <div class="room-filters" role="group" aria-label="房源状态筛选">
          <button type="button" data-role="room-filter" data-filter="all" aria-pressed="true">全部</button>
          <button type="button" data-role="room-filter" data-filter="available" aria-pressed="false">可售</button>
          <button type="button" data-role="room-filter" data-filter="sold" aria-pressed="false">已售</button>
          <button type="button" data-role="room-filter" data-filter="abnormal" aria-pressed="false">异常</button>
        </div>
        <div class="floor-toolbar" aria-label="楼层分布缩放控制" hidden>
          <button type="button" data-role="zoom-in">放大</button>
          <button type="button" data-role="zoom-out">缩小</button>
          <button type="button" data-role="reset-zoom">复位</button><button type="button" data-role="floor-fullscreen" aria-pressed="false">全屏</button>
          <label class="zoom-control">缩放<input data-role="zoom-range" type="range" min="18" max="220" step="1" value="100" aria-label="楼层分布缩放比例"></label>
          <button type="button" data-role="all-buildings">全部楼栋</button>
          <span><output data-role="zoom-scale">100%</output></span>
        </div>
        <div class="numeric-filters" aria-label="价格筛选">
          <label>单价下限<input data-role="price-min" type="number" min="0" step="100" inputmode="numeric" placeholder="元/㎡"></label>
          <label>单价上限<input data-role="price-max" type="number" min="0" step="100" inputmode="numeric" placeholder="元/㎡"></label>
          <label>总价下限<input data-role="total-min" type="number" min="0" step="10000" inputmode="numeric" placeholder="万元"></label>
          <label>总价上限<input data-role="total-max" type="number" min="0" step="10000" inputmode="numeric" placeholder="万元"></label>
        </div>
      </div>
      <p class="floor-note">楼层分布按“楼栋 + 单元”排布：楼栋从左到右、楼层从上到下、同一楼层横向一排。地图式操作：拖拽 / 滚轮上下平移，双指捏合等比缩放；已售为红色，可售为绿色，右上角小方块表示单价且相同价格同色；筛选外房源保留原位置并变成灰色方块。</p>
      <div class="room-table-wrap">
        <table class="room-table">
          <caption class="sr-only">一房一价房源明细</caption>
          <thead><tr><th>楼栋</th><th>单元</th><th>楼层</th><th>房号</th><th>户型</th><th>面积</th><th>单价</th><th>总价</th><th>状态</th><th>标记</th><th>交付</th></tr></thead>
          <tbody data-role="room-results"><tr><td colspan="11" class="loading">正在载入房源明细…</td></tr></tbody>
        </table>
      </div>
      <div class="floor-results" data-role="floor-results" hidden aria-live="polite"><button type="button" class="back-overview" data-role="back-to-overview" hidden aria-label="返回单元总览"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6"/></svg><span>返回单元总览</span></button><p class="loading">正在载入楼层分布…</p></div>
      <div class="room-foot"><p data-role="room-count" role="status" aria-live="polite">等待载入</p><button type="button" data-role="room-more" hidden>显示更多房源</button></div>
      <div class="certificate-list">{''.join(certificate_cards) or '<p class="one-price-note">暂无预售证摘要。</p>'}</div>
    </section>'''



ONE_PRICE_CSS = r'''.one-price{overflow:hidden;margin:0 0 24px;border:1px solid var(--line);border-radius:18px;background:var(--panel);box-shadow:var(--shadow)}.one-price.empty{display:grid;min-height:170px;place-items:center;color:var(--muted)}.one-price-head{display:flex;justify-content:space-between;gap:16px;align-items:start;padding:18px 18px 14px}.one-price-head h2{margin:0}.one-price-head p{margin:4px 0 0;color:var(--muted);font-size:13px}.one-price-head a{display:inline-flex;min-height:36px;align-items:center;padding:0 12px;border-radius:10px;background:var(--panel-soft);color:var(--brand-ink);font-size:12px;font-weight:800;text-decoration:none;white-space:nowrap}.one-price-error{margin:0;padding:13px 18px;background:color-mix(in srgb,#b42318 10%,var(--panel));color:#b42318;font-weight:750}.one-price-note{margin:0;padding:14px 18px;color:var(--muted)}.one-price-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:1px;background:var(--panel-soft)}.one-price-metric{min-width:0;padding:13px;background:var(--panel)}.one-price-metric span{display:block;color:var(--muted);font-size:11px}.one-price-metric strong{display:block;margin-top:2px;font-size:21px;letter-spacing:-.045em}.one-price-metric.available strong{color:#137a4b}.one-price-metric.sold strong{color:#a35613}.one-price-metric.abnormal strong{color:#a33815}@media (prefers-color-scheme:dark){.one-price-metric.available strong{color:#75d9a5}.one-price-metric.sold strong{color:#f0b76a}.one-price-metric.abnormal strong{color:#ff9d7a}.one-price-error{background:#43110c;color:#ffab94}}.room-controls{display:grid;grid-template-columns:auto minmax(170px,220px) minmax(140px,180px) minmax(130px,170px) minmax(220px,1fr);gap:9px;padding:13px 14px;border-top:1px solid var(--line);background:var(--panel-soft)}.room-controls label,.room-filters,.numeric-filters{display:flex;min-width:0;align-items:center;gap:7px;color:var(--muted);font-size:12px;font-weight:750}.room-controls select,.room-controls input{min-width:0;flex:1;height:38px;padding:0 10px;border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--ink);font:inherit;font-size:13px;outline:none}.room-controls input:focus-visible,.room-controls select:focus-visible{border-color:var(--focus)}.view-switch{display:flex;gap:5px}.view-switch button,.room-filters button{height:38px;padding:0 11px;border:0;border-radius:10px;background:var(--panel);color:var(--muted);font:inherit;font-size:12px;font-weight:800;cursor:pointer}.view-switch button[aria-pressed=true],.room-filters button[aria-pressed=true]{background:var(--brand);color:#fff}.room-filters,.numeric-filters{grid-column:1/-1;flex-wrap:wrap}.room-filters{justify-content:flex-start;overflow:visible}.numeric-filters{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:7px}.numeric-filters label{flex-direction:column;align-items:stretch;gap:4px}.numeric-filters input{width:100%}.floor-note{margin:0;padding:9px 15px;border-top:1px solid var(--line);background:var(--panel);color:var(--muted);font-size:12px}.room-table-wrap{overflow-x:auto;border-top:1px solid var(--line)}.room-table{width:100%;min-width:1030px;border-collapse:collapse;font-size:13px}.room-table th,.room-table td{padding:11px 13px;border-top:1px solid var(--line);text-align:left;vertical-align:top;white-space:nowrap}.room-table thead th{position:sticky;top:0;background:var(--panel);color:var(--muted);font-size:11px}.room-table td.loading{color:var(--muted)}.status{display:inline-flex;height:24px;align-items:center;padding:0 8px;border-radius:999px;background:var(--panel-soft);color:var(--muted);font-size:11px;font-weight:800}.status.available{color:#137a4b;background:color-mix(in srgb,#137a4b 12%,var(--panel))}.status.sold{color:#a35613;background:color-mix(in srgb,#a35613 12%,var(--panel))}.status.abnormal{margin-left:5px;color:#a33815;background:color-mix(in srgb,#a33815 12%,var(--panel))}@media (prefers-color-scheme:dark){.status.available{color:#75d9a5}.status.sold{color:#f0b76a}.status.abnormal{color:#ff9d7a}}.floor-results{--floor-scale:1;--pan-x:0px;--pan-y:0px;--map-surface:#f0f2f5;--map-panel:#ffffff;--map-panel-soft:#f7f8fa;--map-ink:#1d1d1f;--map-muted:#6e6e73;--map-line:#d2d2d7;--map-line-strong:#a1a1a6;--map-brand:#0071e3;--map-brand-ink:#0066cc;--map-focus:#0071e3;--map-available:#34c759;--map-sold:#ff3b30;--map-ghost:#8e8e93;--floor-axis:52px;--floor-height:96px;--room-width:112px;position:relative;padding:0;border-top:1px solid var(--map-line);background:var(--map-surface);color:var(--map-ink)}
.one-price.floor-fullscreen{position:fixed;inset:0;z-index:80;display:flex;flex-direction:column;border:0;border-radius:0;background:#f0f2f5;overflow:hidden}.one-price.floor-fullscreen>*:not(.room-controls):not(.floor-results){display:none}.one-price.floor-fullscreen .room-controls{display:block;padding:0;border-top:0;background:color-mix(in srgb,#ffffff 82%,transparent);backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px)}.one-price.floor-fullscreen .room-controls>*:not(.floor-toolbar){display:none}.one-price.floor-fullscreen .floor-toolbar{border-radius:0}.one-price.floor-fullscreen .floor-results{display:flex;flex:1;min-height:0;flex-direction:column;border-top:0}.one-price.floor-fullscreen .floor-stage.floor-map{flex:1;height:auto;min-height:0}.floor-results>.loading{margin:0;padding:16px;color:var(--map-muted)}.floor-render-status{position:absolute;left:50%;bottom:12px;z-index:11;margin:0;padding:5px 10px;border:1px solid var(--map-line);border-radius:999px;background:color-mix(in srgb,var(--map-panel) 88%,transparent);color:var(--map-muted);font-size:10px;font-weight:750;box-shadow:0 8px 24px #00000014;transform:translateX(-50%);pointer-events:none}
.floor-toolbar{position:relative;z-index:5;display:flex;flex-wrap:wrap;align-items:center;gap:6px;min-height:56px;padding:9px 14px;border-bottom:1px solid color-mix(in srgb,var(--map-ink) 10%,transparent);background:color-mix(in srgb,var(--map-panel) 82%,transparent);backdrop-filter:saturate(180%) blur(20px);-webkit-backdrop-filter:saturate(180%) blur(20px)}
.floor-toolbar button{height:34px;padding:0 12px;border:1px solid var(--map-line);border-radius:999px;background:color-mix(in srgb,var(--map-panel) 88%,transparent);color:var(--map-ink);font:inherit;font-size:12px;font-weight:650;letter-spacing:-.01em;cursor:pointer;transition:background .18s var(--ease-out),border-color .18s var(--ease-out),color .18s var(--ease-out),box-shadow .18s var(--ease-out)}
.floor-toolbar button:hover,.floor-toolbar button[aria-pressed=true]{border-color:color-mix(in srgb,var(--map-brand) 34%,var(--map-line));background:var(--map-panel);color:var(--map-brand-ink);box-shadow:0 1px 2px #0000000a,0 8px 20px #00000012}
.floor-toolbar button:focus-visible{outline:3px solid color-mix(in srgb,var(--map-focus) 58%,transparent);outline-offset:2px}.back-overview{position:absolute;top:12px;left:12px;z-index:12;display:inline-flex;min-height:38px;align-items:center;gap:4px;padding:0 13px;border:1px solid color-mix(in srgb,var(--map-ink) 14%,transparent);border-radius:999px;background:color-mix(in srgb,var(--map-panel) 88%,transparent);color:var(--map-brand-ink);font:inherit;font-size:12px;font-weight:750;letter-spacing:-.01em;cursor:pointer;backdrop-filter:saturate(180%) blur(18px);-webkit-backdrop-filter:saturate(180%) blur(18px);box-shadow:0 1px 2px #0000000a,0 10px 28px #00000016;transition:transform .18s var(--ease-out),border-color .18s var(--ease-out),background .18s var(--ease-out)}.back-overview:hover{border-color:color-mix(in srgb,var(--map-brand) 36%,var(--map-line));background:var(--map-panel)}.back-overview:active{transform:scale(.97)}.back-overview svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}.back-overview[hidden]{display:none}
.floor-toolbar span{display:inline-flex;align-items:center;justify-content:center;min-width:58px;min-height:34px;padding:0 10px;border:1px solid var(--map-line);border-radius:999px;background:color-mix(in srgb,var(--map-panel) 88%,transparent);color:var(--map-muted);font-size:12px;font-weight:650;font-variant-numeric:tabular-nums}
.zoom-control{display:flex;align-items:center;gap:9px;min-height:34px;padding:0 12px;border:1px solid var(--map-line);border-radius:999px;background:color-mix(in srgb,var(--map-panel) 88%,transparent);color:var(--map-muted);font-size:12px;font-weight:650}
.zoom-control input{width:132px;accent-color:var(--map-brand)}
.floor-stage.floor-map{position:relative;z-index:1;height:min(78vh,860px);overflow:hidden;cursor:grab;touch-action:none;overscroll-behavior:contain;user-select:none;-webkit-user-select:none;background:var(--map-surface);background-image:radial-gradient(circle at 50% 0,color-mix(in srgb,var(--map-panel) 90%,transparent) 0,transparent 62%),repeating-linear-gradient(90deg,color-mix(in srgb,var(--map-ink) 5%,transparent) 0 1px,transparent 1px 32px),repeating-linear-gradient(180deg,color-mix(in srgb,var(--map-ink) 5%,transparent) 0 1px,transparent 1px 32px)}
.floor-stage.floor-map:active,.floor-stage.floor-map.dragging{cursor:grabbing}
.floor-stage.floor-map:focus-visible{outline:3px solid color-mix(in srgb,var(--map-focus) 58%,transparent);outline-offset:-3px}
.floor-canvas{position:relative;display:block;width:max-content;padding:18px;transform-origin:0 0;transform:translate3d(var(--pan-x),var(--pan-y),0) scale(var(--floor-scale));will-change:transform}
.floor-matrix{display:grid;width:max-content;grid-template-columns:var(--floor-axis) repeat(var(--floor-columns),var(--building-width));grid-template-rows:58px repeat(var(--floor-count),var(--floor-height));grid-auto-rows:var(--floor-height);gap:0 12px}
.floor-row{display:grid;grid-column:1/-1;grid-template-columns:var(--floor-axis) repeat(var(--floor-columns),var(--building-width));align-items:stretch}
.floor-row.header-row{grid-auto-rows:58px;min-height:58px}
.floor-corner{display:flex;align-items:end;padding:0 0 9px;color:var(--map-muted);font-size:10px;font-weight:650;letter-spacing:.08em;text-transform:uppercase}
.floor-column-head{display:grid;align-content:center;gap:2px;min-height:52px;padding:7px 9px;border:1px solid var(--map-line);border-radius:12px;background:color-mix(in srgb,var(--map-panel) 92%,transparent);box-shadow:0 1px 2px #00000008;text-align:center;backdrop-filter:blur(12px)}
.floor-column-head strong{color:var(--map-ink);font-size:13px;letter-spacing:-.01em}
.floor-column-head span{color:var(--map-muted);font-size:10px;font-weight:500}
.floor-axis-y{display:flex;align-items:center;justify-content:center;border-right:1px solid color-mix(in srgb,var(--map-line) 82%,transparent);color:var(--map-muted);font-size:11px;font-weight:650;font-variant-numeric:tabular-nums}
.building-cell{position:relative;height:var(--floor-height);min-width:0;overflow:hidden;padding:4px;border:1px solid color-mix(in srgb,var(--map-line) 82%,transparent);border-radius:10px;background:color-mix(in srgb,var(--map-panel) 72%,transparent);box-shadow:0 1px 2px #00000006;backdrop-filter:blur(10px)}
.room-cells{display:grid;height:calc(var(--floor-height) - 10px);grid-template-rows:100%;grid-auto-rows:100%;grid-auto-flow:column;grid-auto-columns:var(--room-width);gap:6px;align-content:stretch}
.floor-room{position:relative;box-sizing:border-box;width:100%;height:100%;min-width:0;min-height:0;padding:7px 9px 6px 10px;overflow:hidden;border:1px solid color-mix(in srgb,var(--map-ink) 10%,transparent);border-left:4px solid var(--price-color,var(--map-brand));border-radius:7px;background:var(--map-panel);color:var(--map-ink);box-shadow:0 1px 2px #00000006;transition:background .18s var(--ease-out),border-color .18s var(--ease-out),box-shadow .18s var(--ease-out);content-visibility:auto;contain:layout paint style;contain-intrinsic-size:auto 86px}
.floor-room.available{--status-color:var(--map-available);background:color-mix(in srgb,var(--map-available) 7%,var(--map-panel))}
.floor-room.sold{--status-color:var(--map-sold);background:color-mix(in srgb,var(--map-sold) 7%,var(--map-panel))}
.floor-room:hover,.floor-room:focus-visible{border-color:color-mix(in srgb,var(--map-brand) 42%,var(--map-line));box-shadow:0 0 0 3px color-mix(in srgb,var(--map-brand) 14%,transparent),0 8px 20px #00000012}
.floor-room:focus-visible{outline:3px solid color-mix(in srgb,var(--map-focus) 58%,transparent);outline-offset:2px}
.floor-room.filtered-out,.floor-missing{--price-color:var(--map-ghost);--status-color:var(--map-ghost);padding:0;border:1px solid color-mix(in srgb,var(--map-ghost) 24%,transparent);border-left-width:1px;border-radius:7px;background:color-mix(in srgb,var(--map-ghost) 12%,transparent);color:var(--map-ghost);font-size:11px;font-weight:650;text-align:center;box-shadow:none}
.floor-room.filtered-out{width:100%;height:100%;min-height:100%}
.floor-room.filtered-out>*{display:none}
.floor-missing{display:flex;box-sizing:border-box;width:100%;height:100%;min-height:100%;align-items:center;justify-content:center}
.floor-price{display:block;color:var(--map-muted);font-size:9px;font-weight:650;line-height:1.2;font-variant-numeric:tabular-nums}
.floor-room strong{display:block;margin-top:1px;font-size:12px;line-height:1.2;letter-spacing:-.01em;overflow-wrap:anywhere}
.floor-meta{display:block;margin-top:2px;color:var(--map-muted);font-size:9px;font-weight:500;line-height:1.2;overflow-wrap:anywhere}
.floor-total{display:block;margin-top:2px;color:var(--map-muted);font-size:9px;font-weight:500;font-variant-numeric:tabular-nums}
.floor-room .status{margin-top:3px;height:17px;padding:0 5px;font-size:8px}
.floor-room .status+.status{margin-left:3px}
.price-chip{position:absolute;top:5px;right:5px;width:10px;height:10px;border:2px solid color-mix(in srgb,var(--map-panel) 90%,transparent);border-radius:3px;background:var(--price-color,var(--map-brand));box-shadow:0 1px 2px #00000012}
@media (prefers-color-scheme:dark){.floor-results{--map-surface:#0b141c;--map-panel:#1d1d20;--map-panel-soft:#2c2c2e;--map-ink:#f5f5f7;--map-muted:#a1a1a6;--map-line:#38383a;--map-line-strong:#5a5a5e;--map-brand:#2997ff;--map-brand-ink:#64a8ff;--map-focus:#64a8ff;--map-available:#30d158;--map-sold:#ff453a;--map-ghost:#98989d}.one-price.floor-fullscreen{background:#0b141c}.floor-toolbar,.zoom-control,.floor-toolbar span{background:color-mix(in srgb,#1d1d20 82%,transparent)}.floor-toolbar button,.floor-toolbar span,.zoom-control{border-color:#48484a}.floor-stage.floor-map{background-image:radial-gradient(circle at 50% 0,color-mix(in srgb,#2c2c2e 58%,transparent) 0,transparent 62%),repeating-linear-gradient(90deg,color-mix(in srgb,#f5f5f7 5%,transparent) 0 1px,transparent 1px 32px),repeating-linear-gradient(180deg,color-mix(in srgb,#f5f5f7 5%,transparent) 0 1px,transparent 1px 32px)}.floor-room{box-shadow:0 1px 2px #00000040}.floor-room.filtered-out,.floor-missing{background:color-mix(in srgb,#98989d 15%,transparent)}}.overview-grid{display:grid;width:100%;max-width:1440px;grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:18px;margin:0 auto}.building-overview{position:relative;min-width:0;padding:0;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink);font:inherit;cursor:pointer}.building-overview:hover,.building-overview:active{border-color:color-mix(in srgb,var(--brand) 48%,var(--line));transform:translateY(-1px)}.building-overview .floor-column-head{min-height:46px;border:0;background:transparent}.overview-body{position:relative;display:block;margin:0 8px 10px;height:calc(var(--floors,1)*10px + 18px)}.overview-face{position:absolute;inset:0;border:1px solid color-mix(in srgb,var(--ink) 28%,var(--line));border-radius:4px;background:linear-gradient(to top,color-mix(in srgb,#17935d calc(var(--match-ratio,1)*60%),transparent) 0,transparent calc(var(--match-ratio,1)*100%)),repeating-linear-gradient(to top,color-mix(in srgb,var(--ink) 18%,transparent) 0 1px,transparent 1px 10px)}.overview-scale{position:absolute;bottom:-19px;left:50%;white-space:nowrap;color:var(--muted);font-size:9px;font-weight:850;transform:translateX(-50%)}.building-overview:focus-visible{outline:3px solid var(--focus);outline-offset:3px}.room-foot{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 15px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}.room-foot p{margin:0}.room-foot button{height:36px;padding:0 13px;border:0;border-radius:10px;background:var(--brand);color:#fff;font:inherit;font-size:12px;font-weight:800;cursor:pointer}@media (prefers-color-scheme:dark){.room-foot button{color:#07131d}.view-switch button[aria-pressed=true],.room-filters button[aria-pressed=true]{color:#07131d}}.certificate-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1px;padding:1px;background:var(--panel-soft);border-top:1px solid var(--line)}.certificate-card{min-width:0;padding:14px;background:var(--panel)}.certificate-card h3{margin:0 0 8px;font-size:13px;line-height:1.45;overflow-wrap:anywhere}.certificate-card dl{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:0}.certificate-card div{min-width:0}.certificate-card dt{color:var(--muted);font-size:10px}.certificate-card dd{margin:2px 0 0;font-size:14px;font-weight:800}@media (max-width:760px){.floor-toolbar button{height:44px}.floor-toolbar span,.zoom-control{min-height:44px}.one-price-head{align-items:start;flex-direction:column}.one-price-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.one-price-metric:last-child{grid-column:1/-1}.room-controls{grid-template-columns:1fr}.floor-toolbar{padding:9px 12px} .zoom-control{flex:1 1 100%;justify-content:space-between}.zoom-control input{width:100%}.view-switch{display:grid;grid-template-columns:1fr 1fr}.view-switch button,.room-filters button{min-height:44px}.room-controls select,.room-controls input{min-height:44px}.numeric-filters{grid-template-columns:1fr 1fr}.room-filters{justify-content:flex-start}.room-foot{align-items:stretch;flex-direction:column}.room-foot button{width:100%}.certificate-card dl{grid-template-columns:repeat(2,1fr)}}@media (max-width:430px){.numeric-filters{grid-template-columns:1fr}}@media (prefers-reduced-motion:reduce){.one-price *,.one-price *::before,.one-price *::after{transition-duration:.01ms!important;animation-duration:.01ms!important}}'''


ONE_PRICE_JS = r'''(function(){
  'use strict';
  var root=document.querySelector('[data-one-price-url]');
  if(!root)return;
  var url=root.getAttribute('data-one-price-url');
  var view='table',filter='all',certificate='all',building='all',unit='all',query='',limit=100;
  var bounds={priceMin:null,priceMax:null,totalMin:null,totalMax:null};
  var tbody=root.querySelector('[data-role="room-results"]');
  var tableWrap=root.querySelector('.room-table-wrap');
  var floorResults=root.querySelector('[data-role="floor-results"]');
  var floorToolbar=root.querySelector('.floor-toolbar');
  var backToOverview=root.querySelector('[data-role="back-to-overview"]');
  var count=root.querySelector('[data-role="room-count"]');
  var more=root.querySelector('[data-role="room-more"]');
  var certificateSelect=root.querySelector('[data-role="certificate-filter"]');
  var buildingSelect=root.querySelector('[data-role="building-filter"]');
  var unitSelect=root.querySelector('[data-role="unit-filter"]');
  var search=root.querySelector('[data-role="room-search"]');
  var rooms=[];
  var priceGroups=new Map();
  function text(value){return value===null||value===undefined||value===''?'—':String(value);}
  function pickRoom(room){return Object.assign({},room,{
    buildName:room.buildName!==undefined?room.buildName:room.buildingName,
    unitName:room.unitName!==undefined?room.unitName:room.unit,
    floor:room.floor!==undefined?room.floor:room.floorName,
    roomName:room.roomName,
    roomLayout:room.roomLayout!==undefined?room.roomLayout:room.houseType,
    area:room.area!==undefined?room.area:room.buildArea
  });}
  function numericValue(value){if(value===null||value===undefined||value==='')return null;var parsed=Number(value);return isFinite(parsed)?parsed:null;}
  function totalYuan(value){return numericValue(value);}
  function number(value){var parsed=Number(value);return isFinite(parsed)?parsed.toLocaleString('zh-CN'):text(value);}
  function area(value){var parsed=Number(value);return isFinite(parsed)?parsed.toLocaleString('zh-CN',{maximumFractionDigits:2})+' ㎡':text(value);}
  function money(value){var parsed=Number(value);return isFinite(parsed)?parsed.toLocaleString('zh-CN',{maximumFractionDigits:0})+' 元/㎡':text(value);}
  function total(value){var parsed=Number(value);return isFinite(parsed)?parsed.toLocaleString('zh-CN',{maximumFractionDigits:0})+' 元':text(value);}
  function setSummary(values){
    var sold=values.filter(function(room){return Number(room.saleStatus)===1}).length;
    var available=values.filter(function(room){return Number(room.saleStatus)===2}).length;
    var abnormal=values.filter(function(room){return Number(room.abnormalStatus)===1}).length;
    var summary=[certificateSelect.options.length-1,values.length,available,sold,abnormal];
    root.querySelectorAll('.one-price-metric strong').forEach(function(item,index){item.textContent=number(summary[index])});
  }
  function priceKey(room){
    var value=numericValue(room.price);
    return value===null?'unknown':'price-'+String(value);
  }
  function buildPricePalette(values){
    var unique=[];var seen=new Set();
    values.forEach(function(room){
      var value=numericValue(room.price);var key=priceKey(room);
      if(value===null||seen.has(key))return;seen.add(key);unique.push({key:key,value:value});
    });
    unique.sort(function(left,right){return left.value-right.value});
    var result=new Map();
    unique.forEach(function(item,index){
      var hue=(index*137.508)%360;var light=40+(index%4)*7;
      result.set(item.key,'hsl('+hue.toFixed(2)+',72%,'+light+'%)');
    });
    return result;
  }
  function matrixKey(room){return [text(room.buildName),text(room.unitName)].join('\\u0001');}
  function floorNumber(value){var match=String(value).match(/-?\d+(?:\.\d+)?/);return match?Number(match[0]):Number.NaN;}
  function naturalCompare(left,right){return String(left).localeCompare(String(right),'zh-Hans-CN',{numeric:true,sensitivity:'base'});}
  function scopedRooms(){
    return rooms.filter(function(room){
      if(certificate!=='all'&&room.certificateId!==certificate)return false;
      if(building!=='all'&&text(room.buildName)!==building)return false;
      if(unit!=='all'&&text(room.unitName)!==unit)return false;
      return true;
    });
  }
  function roomMatches(room){
    if(certificate!=='all'&&room.certificateId!==certificate)return false;
    if(building!=='all'&&text(room.buildName)!==building)return false;
    if(unit!=='all'&&text(room.unitName)!==unit)return false;
    if(filter==='available'&&Number(room.saleStatus)!==2)return false;
    if(filter==='sold'&&Number(room.saleStatus)!==1)return false;
    if(filter==='abnormal'&&Number(room.abnormalStatus)!==1)return false;
    var price=numericValue(room.price);var totalPrice=totalYuan(room.totalPrice);
    if(bounds.priceMin!==null&&(price===null||price<bounds.priceMin))return false;
    if(bounds.priceMax!==null&&(price===null||price>bounds.priceMax))return false;
    if(bounds.totalMin!==null&&(totalPrice===null||totalPrice<bounds.totalMin*10000))return false;
    if(bounds.totalMax!==null&&(totalPrice===null||totalPrice>bounds.totalMax*10000))return false;
    var haystack=[room.certificateName,room.buildName,room.unitName,room.floor,room.roomName,room.roomLayout,room.price,room.totalPrice].join(' ').toLowerCase();
    return query.trim().toLowerCase().split(/\s+/).filter(Boolean).every(function(word){return haystack.indexOf(word)>=0});
  }
  function filterRooms(){
    return scopedRooms().filter(roomMatches);
  }
  function row(room){
    var tr=document.createElement('tr');
    [room.buildName,room.unitName,room.floor,room.roomName,room.roomLayout].forEach(function(value){
      var cell=document.createElement('td');cell.textContent=text(value);tr.appendChild(cell);
    });
    [area(room.area),money(room.price),total(room.totalPrice)].forEach(function(value){
      var cell=document.createElement('td');cell.textContent=value;tr.appendChild(cell);
    });
    var statusCell=document.createElement('td');var badge=document.createElement('span');
    var available=Number(room.saleStatus)===2;
    badge.className='status '+(available?'available':'sold');badge.textContent=available?'可售':'已售';
    statusCell.appendChild(badge);tr.appendChild(statusCell);
    var flagCell=document.createElement('td');
    if(Number(room.abnormalStatus)===1){var flag=document.createElement('span');flag.className='status abnormal';flag.textContent='异常';flagCell.appendChild(flag);}else{flagCell.textContent='—';}
    tr.appendChild(flagCell);
    var delivery=document.createElement('td');delivery.textContent=text(room.delivery);tr.appendChild(delivery);
    return tr;
  }
  function setOptions(select,allLabel,values,current){
    var selected=current;var unique=values.filter(function(value,index){return values.indexOf(value)===index}).sort(naturalCompare);
    if(selected!=='all'&&unique.indexOf(selected)<0)selected='all';
    select.replaceChildren();
    var all=document.createElement('option');all.value='all';all.textContent=allLabel;select.appendChild(all);
    unique.forEach(function(value){var option=document.createElement('option');option.value=value;option.textContent=value;select.appendChild(option)});
    select.value=selected;
  }
  function refreshBuildingOptions(){
    var values=rooms.filter(function(room){return certificate==='all'||room.certificateId===certificate}).map(function(room){return text(room.buildName)});
    setOptions(buildingSelect,'全部楼栋',values,building);building=buildingSelect.value;
  }
  function refreshUnitOptions(){
    var values=rooms.filter(function(room){return (certificate==='all'||room.certificateId===certificate)&&(building==='all'||text(room.buildName)===building)}).map(function(room){return text(room.unitName)});
    setOptions(unitSelect,'全部单元',values,unit);unit=unitSelect.value;
  }
  function roomCell(room,matched){
    var available=Number(room.saleStatus)===2;var price=numericValue(room.price);var group=priceGroups.get(priceKey(room));
    var article=document.createElement('article');article.className='floor-room '+(available?'available':'sold')+(matched?'':' filtered-out');article.tabIndex=0;
    article.setAttribute('aria-disabled',matched?'false':'true');
    article.setAttribute('data-price',text(room.price));article.setAttribute('data-price-value',price===null?'':String(price));article.setAttribute('data-total-price',text(room.totalPrice));
    article.setAttribute('data-price-group',priceKey(room));article.setAttribute('data-room-status',available?'available':'sold');
    article.setAttribute('aria-label',text(room.buildName)+text(room.unitName)+text(room.floor)+' '+text(room.roomName)+(available?'，可售':'，已售')+'，单价 '+money(room.price)+'，总价 '+total(room.totalPrice)+(matched?'':'，筛选外'));
    if(!matched){article.textContent='—';return article}
    if(group)article.style.setProperty('--price-color',group);
    var priceLabel=document.createElement('span');priceLabel.className='floor-price';priceLabel.textContent=money(room.price);article.appendChild(priceLabel);
    var name=document.createElement('strong');name.textContent=text(room.roomName);article.appendChild(name);
    var meta=document.createElement('span');meta.className='floor-meta';meta.textContent=text(room.roomLayout)+' · '+area(room.area);article.appendChild(meta);
    var totalPrice=document.createElement('span');totalPrice.className='floor-total';totalPrice.textContent=total(room.totalPrice);article.appendChild(totalPrice);
    var badge=document.createElement('span');badge.className='status '+(available?'available':'sold');badge.textContent=available?'可售':'已售';article.appendChild(badge);
    if(Number(room.abnormalStatus)===1){var abnormal=document.createElement('span');abnormal.className='status abnormal';abnormal.textContent='异常';article.appendChild(abnormal);}
    if(group){var swatch=document.createElement('span');swatch.className='price-chip';swatch.setAttribute('aria-hidden','true');article.appendChild(swatch);}
    return article;
  }

  function floorHeader(column){
    var head=document.createElement('header');head.className='building-head floor-column-head';
    var building=document.createElement('strong');building.textContent=text(column.building);head.appendChild(building);
    var unit=document.createElement('span');unit.textContent='单元 '+text(column.unitName);head.appendChild(unit);
    return head;
  }
  var DETAIL_BUILDING_LIMIT=16;var floorSignature='';var floorRenderToken=0;
  function focusBuilding(column){building=text(column.building);unit=text(column.unitName);limit=100;render()}
  function renderFloorView(allRooms){
    var renderToken=++floorRenderToken;
    var backButton=backToOverview;
    floorResults.replaceChildren();
    if(!allRooms.length){var empty=document.createElement('p');empty.className='loading';empty.textContent='没有可展示的楼栋数据';floorResults.appendChild(empty);if(backButton)floorResults.appendChild(backButton);return;}
    var columns=[];var columnSeen=new Set();var floors=[];var floorSeen=new Set();var floorRooms=new Map();var maxRoomsPerColumn=1;
    allRooms.forEach(function(room){
      var key=matrixKey(room);var floor=text(room.floor);
      if(!columnSeen.has(key)){columnSeen.add(key);columns.push({key:key,building:text(room.buildName),unitName:text(room.unitName)});floorRooms.set(key,new Map())}
      if(!floorSeen.has(floor)){floorSeen.add(floor);floors.push(floor)}
      var rooms=floorRooms.get(key);if(!rooms.has(floor))rooms.set(floor,[]);
      var values=rooms.get(floor);values.push(room);maxRoomsPerColumn=Math.max(maxRoomsPerColumn,values.length);
    });
    columns.sort(function(left,right){return naturalCompare(left.building,right.building)||naturalCompare(left.unitName,right.unitName)});
    floors.sort(function(left,right){var ln=floorNumber(left);var rn=floorNumber(right);if(isFinite(ln)&&isFinite(rn)&&ln!==rn)return rn-ln;if(isFinite(ln))return -1;if(isFinite(rn))return 1;return naturalCompare(left,right)});
    var signature=columns.map(function(column){return column.key}).join('|')+'::'+floors.join('|');
    var stage=document.createElement('div');stage.className='floor-stage floor-map';stage.tabIndex=0;stage.setAttribute('role','application');stage.setAttribute('aria-label','楼层分布地图，可拖拽、缩放和键盘操作');stage.setAttribute('aria-keyshortcuts','方向键平移，加号放大，减号缩小，0 复位');stage.setAttribute('aria-busy','true');stage.dataset.renderState='loading';
    var status=document.createElement('p');status.className='floor-render-status';status.textContent='楼层分布渲染中 0%';
    var canvas=document.createElement('div');canvas.className='floor-canvas';
    var jobs=[];var overview=columns.length>DETAIL_BUILDING_LIMIT;
    if(overview){
      var overviewGrid=document.createElement('div');overviewGrid.className='overview-grid';overviewGrid.setAttribute('aria-label','楼栋总览，选择楼栋单元后查看真实楼层分布');
      canvas.appendChild(overviewGrid);stage.appendChild(canvas);stage.appendChild(status);
      columns.forEach(function(column){
        var values=[];floorRooms.get(column.key).forEach(function(floorRoomsForColumn){values.push.apply(values,floorRoomsForColumn)});
        var matched=values.filter(roomMatches).length;var ratio=values.length?matched/values.length:0;var columnFloors=floorRooms.get(column.key).size;
        jobs.push(function(){
          var block=document.createElement('button');block.type='button';block.className='building-column building-overview';block.style.setProperty('--floors',String(columnFloors));block.style.setProperty('--match-ratio',ratio.toFixed(3));
          block.setAttribute('aria-label','聚焦 '+text(column.building)+' 单元 '+text(column.unitName)+'，'+columnFloors+' 层，'+values.length+' 套房源');
          block.appendChild(floorHeader(column));
          var body=document.createElement('span');body.className='overview-body';
          var face=document.createElement('span');face.className='overview-face';face.setAttribute('aria-hidden','true');body.appendChild(face);
          var scale=document.createElement('span');scale.className='overview-scale';scale.textContent=columnFloors+'F · '+values.length+'套';body.appendChild(scale);
          block.appendChild(body);block.addEventListener('pointerup',function(event){if(event.pointerType==='touch'&&!gestureMoved)focusBuilding(column)});block.addEventListener('click',function(event){if(gestureMoved)return;focusBuilding(column)});
          return block;
        });
      });
    }else{
      var matrix=document.createElement('div');matrix.className='floor-matrix';matrix.style.setProperty('--floor-columns',String(columns.length));matrix.style.setProperty('--floor-count',String(floors.length));matrix.style.setProperty('--building-width',(maxRoomsPerColumn*119+8)+'px');
      matrix.setAttribute('aria-label','楼栋从左到右、楼层从上到下、同一楼层横向一排');
      var headerRow=document.createElement('div');headerRow.className='floor-row header-row';
      var corner=document.createElement('div');corner.className='floor-corner';corner.textContent='楼层';headerRow.appendChild(corner);
      columns.forEach(function(column){headerRow.appendChild(floorHeader(column))});
      matrix.appendChild(headerRow);
      floors.forEach(function(floor){
        var row=document.createElement('div');row.className='floor-row';
        var axis=document.createElement('div');axis.className='floor-axis-y';axis.textContent=floor;row.appendChild(axis);
        columns.forEach(function(column){
          var cell=document.createElement('div');cell.className='building-cell';
          var cells=document.createElement('div');cells.className='room-cells';cell.appendChild(cells);row.appendChild(cell);
          jobs.push(function(){
            var fragment=document.createDocumentFragment();var values=floorRooms.get(column.key)&&floorRooms.get(column.key).get(floor);
            if(values&&values.length){values.sort(function(left,right){return naturalCompare(left.roomName,right.roomName)}).forEach(function(room){var matched=roomMatches(room);fragment.appendChild(roomCell(room,matched))})}
            else{var missing=document.createElement('div');missing.className='floor-missing';missing.textContent='—';missing.setAttribute('aria-label',text(column.building)+' '+text(column.unitName)+' '+floor+' 无房源');fragment.appendChild(missing)}
            cells.appendChild(fragment);
          });
        });
        matrix.appendChild(row);
      });
      canvas.appendChild(matrix);stage.appendChild(canvas);stage.appendChild(status);
    }
    floorResults.appendChild(stage);if(backButton)floorResults.appendChild(backButton);
    if(!overview){
      if(signature!==floorSignature){floorSignature=signature;fitView(canvas)}else{applyViewState(canvas);queueClamp(canvas)}
    }
    var cursor=0;
    function finishRender(){
      if(renderToken!==floorRenderToken)return;
      if(overview){
        if(signature!==floorSignature){floorSignature=signature;fitView(canvas)}else{applyViewState(canvas);queueClamp(canvas)}
      }
      stage.dataset.renderState='complete';stage.removeAttribute('aria-busy');status.textContent='楼层分布渲染完成';
      requestAnimationFrame(function(){if(renderToken===floorRenderToken&&status.parentNode)status.parentNode.removeChild(status)});
    }
    function renderFloorBatch(){
      if(renderToken!==floorRenderToken)return;
      var frameStart=performance.now();var fragment=overview?document.createDocumentFragment():null;
      while(cursor<jobs.length&&performance.now()-frameStart<10){var result=jobs[cursor++]();if(fragment)fragment.appendChild(result)}
      if(fragment)canvas.firstChild.appendChild(fragment);
      var percent=jobs.length?Math.round(cursor/jobs.length*100):100;status.textContent='楼层分布渲染中 '+percent+'%';
      if(cursor<jobs.length)requestAnimationFrame(renderFloorBatch);else finishRender();
    }
    if(jobs.length)requestAnimationFrame(renderFloorBatch);else finishRender();
  }
  var viewState={scale:1,x:0,y:0};
  function clampScale(value){return Math.min(2.2,Math.max(.18,value))}
  function fitView(canvas){
    if(!canvas)return;var stage=canvas.closest('.floor-stage');if(!stage)return;
    var width=Math.max(1,canvas.offsetWidth);var height=Math.max(1,canvas.offsetHeight);
    var fitAll=Math.min((stage.clientWidth-32)/width,(stage.clientHeight-32)/height,1);
    var fitHeight=Math.min((stage.clientHeight-32)/height,1);
    viewState.scale=clampScale(fitAll>=.55?fitAll:fitHeight);
    viewState.x=(stage.clientWidth-width*viewState.scale)/2;viewState.y=(stage.clientHeight-height*viewState.scale)/2;
    applyViewState(canvas);queueClamp(canvas);var percent=Math.round(viewState.scale*100);
    if(zoomScale)zoomScale.textContent=percent+'%';if(zoomRange)zoomRange.value=String(percent);
  }
  function applyViewState(canvas){
    floorResults.style.setProperty('--floor-scale',viewState.scale.toFixed(3));
    floorResults.style.setProperty('--pan-x',viewState.x.toFixed(2)+'px');
    floorResults.style.setProperty('--pan-y',viewState.y.toFixed(2)+'px');
    if(canvas)canvas.style.transform='translate3d('+viewState.x.toFixed(2)+'px,'+viewState.y.toFixed(2)+'px,0) scale('+viewState.scale.toFixed(4)+')';
  }
  function clampPan(canvas){
    if(!canvas)return;var stage=canvas.closest('.floor-stage');if(!stage)return;
    var width=canvas.offsetWidth*viewState.scale;var height=canvas.offsetHeight*viewState.scale;
    viewState.x=stage.clientWidth>=width?(stage.clientWidth-width)/2:Math.min(0,Math.max(stage.clientWidth-width,viewState.x));
    viewState.y=stage.clientHeight>=height?(stage.clientHeight-height)/2:Math.min(0,Math.max(stage.clientHeight-height,viewState.y));
    applyViewState(canvas);
  }
  function queueClamp(canvas){requestAnimationFrame(function(){clampPan(canvas)})}
  function setZoom(value,anchorX,anchorY){
    var next=Number(value);if(!isFinite(next))return;
    var stage=floorResults.querySelector('.floor-stage');
    if((anchorX===undefined||anchorY===undefined)&&stage){var rect=stage.getBoundingClientRect();anchorX=rect.width/2;anchorY=rect.height/2}
    zoomAt(anchorX||0,anchorY||0,next/100);
  }
  function zoomAt(anchorX,anchorY,nextScale){
    var canvas=floorResults.querySelector('.floor-canvas');if(!canvas)return;
    var oldScale=viewState.scale;var worldX=(anchorX-viewState.x)/viewState.scale;var worldY=(anchorY-viewState.y)/viewState.scale;
    viewState.scale=clampScale(nextScale);
    viewState.x=anchorX-worldX*viewState.scale;viewState.y=anchorY-worldY*viewState.scale;
    applyViewState(canvas);queueClamp(canvas);
    var percent=Math.round(viewState.scale*100);if(zoomScale)zoomScale.textContent=percent+'%';if(zoomRange)zoomRange.value=String(percent);
  }
  function panBy(deltaX,deltaY){var canvas=floorResults.querySelector('.floor-canvas');if(!canvas)return;viewState.x+=deltaX;viewState.y+=deltaY;clampPan(canvas)}
  function resetView(canvas){fitView(canvas)}
  function render(){
    floorRenderToken++;
    refreshBuildingOptions();refreshUnitOptions();
    var visibleRooms=scopedRooms();var filtered=visibleRooms.filter(roomMatches);
    tableWrap.hidden=view!=='table';floorResults.hidden=view==='table';if(floorToolbar)floorToolbar.hidden=view!=='floor';
    if(view==='table'&&floorFullscreen)setFloorFullscreen(false,true);
    syncBackButton();
    if(view==='table'){
      var fragment=document.createDocumentFragment();
      filtered.slice(0,limit).forEach(function(room){fragment.appendChild(row(room))});
      if(!filtered.length){var empty=document.createElement('tr');var cell=document.createElement('td');cell.colSpan=11;cell.className='loading';cell.textContent='没有符合筛选条件的房源';empty.appendChild(cell);fragment.appendChild(empty);}
      tbody.replaceChildren(fragment);floorResults.replaceChildren();
    }else{renderFloorView(visibleRooms)}
    count.textContent=view==='table'?'显示 '+Math.min(limit,filtered.length)+' / '+filtered.length+' 套房源':'楼层分布显示 '+filtered.length+' / '+visibleRooms.length+' 套匹配房源';
    more.hidden=view!=='table'||limit>=filtered.length;setSummary(visibleRooms);
  }
  function syncBackButton(){if(backToOverview)backToOverview.hidden=!(view==='floor'&&(building!=='all'||unit!=='all'))}
  var zoomScale=root.querySelector('[data-role="zoom-scale"]');var zoomRange=root.querySelector('[data-role="zoom-range"]');var zoomIn=root.querySelector('[data-role="zoom-in"]');var zoomOut=root.querySelector('[data-role="zoom-out"]');var resetZoom=root.querySelector('[data-role="reset-zoom"]');var floorFullscreenButton=root.querySelector('[data-role="floor-fullscreen"]');var floorFullscreen=false;var floorFullscreenScroll={x:0,y:0};
  function syncFloorFullscreen(){if(!floorFullscreenButton)return;floorFullscreenButton.setAttribute('aria-pressed',floorFullscreen?'true':'false');floorFullscreenButton.textContent=floorFullscreen?'退出全屏':'全屏'}
  function refitFloorView(){requestAnimationFrame(function(){requestAnimationFrame(function(){if(view!=='floor')return;var canvas=floorResults.querySelector('.floor-canvas');if(canvas)fitView(canvas)})})}
  function restoreFloorScroll(){requestAnimationFrame(function(){window.scrollTo(floorFullscreenScroll.x,floorFullscreenScroll.y);refitFloorView()})}
  function setFloorFullscreen(enabled,useNative){
    if(enabled===floorFullscreen)return;
    if(enabled)floorFullscreenScroll={x:window.scrollX,y:window.scrollY};
    floorFullscreen=enabled;root.classList.toggle('floor-fullscreen',enabled);syncFloorFullscreen();
    if(enabled&&useNative&&root.requestFullscreen){try{var request=root.requestFullscreen();if(request&&request.catch)request.catch(function(){})}catch(error){}}
    if(!enabled&&document.fullscreenElement===root&&document.exitFullscreen){try{var exit=document.exitFullscreen();if(exit&&exit.catch)exit.catch(function(){})}catch(error){}}
    if(enabled)refitFloorView();else restoreFloorScroll();
  }
  function zoomFromControl(next){var stage=floorResults.querySelector('.floor-stage');if(!stage){setZoom(next);return}var rect=stage.getBoundingClientRect();setZoom(next,rect.width/2,rect.height/2)}
  if(zoomIn)zoomIn.addEventListener('click',function(){zoomFromControl((viewState.scale+.18)*100)});
  if(zoomOut)zoomOut.addEventListener('click',function(){zoomFromControl((viewState.scale-.18)*100)});
  if(resetZoom)resetZoom.addEventListener('click',function(){resetView(floorResults.querySelector('.floor-canvas'))});
  if(floorFullscreenButton)floorFullscreenButton.addEventListener('click',function(){setFloorFullscreen(!floorFullscreen,true)});
  document.addEventListener('fullscreenchange',function(){if(floorFullscreen&&document.fullscreenElement!==root){floorFullscreen=false;root.classList.remove('floor-fullscreen');syncFloorFullscreen();restoreFloorScroll()}if(!document.fullscreenElement&&!floorFullscreen)setTimeout(function(){restoreFloorScroll()},50)});
  document.addEventListener('keydown',function(event){if(event.key==='Escape'&&floorFullscreen){event.preventDefault();setFloorFullscreen(false,true)}});
  window.addEventListener('resize',function(){if(view==='floor')refitFloorView()});
  if(zoomRange)zoomRange.addEventListener('input',function(){zoomFromControl(zoomRange.value)});
  var allBuildings=root.querySelector('[data-role="all-buildings"]');
  if(allBuildings)allBuildings.addEventListener('click',function(){building='all';unit='all';limit=100;render()});
  if(backToOverview)backToOverview.addEventListener('click',function(){building='all';unit='all';limit=100;render()});
  var activePointers=new Map();var pinchState=null;var gestureMoved=false;
  function stagePoint(stage,event){var rect=stage.getBoundingClientRect();return{x:event.clientX-rect.left,y:event.clientY-rect.top}}
  function currentPoints(stage){var values=[];activePointers.forEach(function(point){values.push(point)});return values}
  function startPinch(stage){var points=currentPoints(stage);if(points.length<2)return;var ax=(points[0].x+points[1].x)/2;var ay=(points[0].y+points[1].y)/2;var dx=points[0].x-points[1].x;var dy=points[0].y-points[1].y;pinchState={distance:Math.max(1,Math.hypot(dx,dy)),baseScale:viewState.scale,worldX:(ax-viewState.x)/viewState.scale,worldY:(ay-viewState.y)/viewState.scale,midX:ax,midY:ay}}
  function wheelFactor(event){return event.deltaMode===1?16:event.deltaMode===2?100:1}
  floorResults.addEventListener('wheel',function(event){
    if(view==='table')return;var stage=event.target.closest('.floor-stage');if(!stage)return;
    event.preventDefault();var factor=wheelFactor(event);var point=stagePoint(stage,event);
    if(event.ctrlKey){zoomAt(point.x,point.y,viewState.scale*Math.exp(-event.deltaY*factor*.0022));return}
    panBy(-event.deltaX*factor,-event.deltaY*factor);
  },{passive:false});
  floorResults.addEventListener('pointerdown',function(event){
    if(view==='table'||event.button!==0)return;var stage=event.target.closest('.floor-stage');if(!stage)return;
    var selectableUnit=event.target.closest('.building-overview');var point=stagePoint(stage,event);activePointers.set(event.pointerId,point);gestureMoved=false;
    if(!selectableUnit){event.preventDefault();try{stage.setPointerCapture(event.pointerId)}catch(error){}}
    if(activePointers.size===2)startPinch(stage);
  });
  floorResults.addEventListener('pointermove',function(event){
    if(view==='table'||!activePointers.has(event.pointerId))return;var stage=event.target.closest('.floor-stage');if(!stage)return;
    var previous=activePointers.get(event.pointerId);var point=stagePoint(stage,event);activePointers.set(event.pointerId,point);
    if(Math.hypot(point.x-previous.x,point.y-previous.y)>4)gestureMoved=true;
    if(gestureMoved)stage.classList.add('dragging');
    if(activePointers.size>=2&&pinchState){
      var points=currentPoints(stage);var ax=(points[0].x+points[1].x)/2;var ay=(points[0].y+points[1].y)/2;
      var dx=points[0].x-points[1].x;var dy=points[0].y-points[1].y;var distance=Math.max(1,Math.hypot(dx,dy));
      viewState.scale=clampScale(pinchState.baseScale*distance/pinchState.distance);
      viewState.x=ax-pinchState.worldX*viewState.scale;viewState.y=ay-pinchState.worldY*viewState.scale;applyViewState(floorResults.querySelector('.floor-canvas'));
      var percent=Math.round(viewState.scale*100);if(zoomScale)zoomScale.textContent=percent+'%';if(zoomRange)zoomRange.value=String(percent);
    }else if(activePointers.size===1){panBy(point.x-previous.x,point.y-previous.y)}
  });
  function endPointer(event){
    if(!activePointers.has(event.pointerId))return;
    var stage=event.target.closest('.floor-stage');
    activePointers.delete(event.pointerId);
    if(stage){try{stage.releasePointerCapture(event.pointerId)}catch(error){}}
    if(activePointers.size<2)pinchState=null;
    if(!activePointers.size){if(stage)stage.classList.remove('dragging');queueClamp(floorResults.querySelector('.floor-canvas'))}
  }
  floorResults.addEventListener('pointerup',endPointer);
  floorResults.addEventListener('pointercancel',endPointer);
  floorResults.addEventListener('click',function(event){if(view==='floor'&&gestureMoved){event.stopPropagation();event.preventDefault()}},true);
  floorResults.addEventListener('keydown',function(event){
    if(view==='table')return;var stage=event.target.closest('.floor-stage');if(!stage)return;
    var step=event.shiftKey?100:40;var key=event.key;
    if(key==='ArrowLeft'){event.preventDefault();panBy(-step,0)}
    else if(key==='ArrowRight'){event.preventDefault();panBy(step,0)}
    else if(key==='ArrowUp'){event.preventDefault();panBy(0,-step)}
    else if(key==='ArrowDown'){event.preventDefault();panBy(0,step)}
    else if(key==='+'||key==='='){event.preventDefault();zoomFromControl((viewState.scale+.08)*100)}
    else if(key==='-'||key==='_'){event.preventDefault();zoomFromControl((viewState.scale-.08)*100)}
    else if(key==='0'){event.preventDefault();resetView(floorResults.querySelector('.floor-canvas'))}
  });
  root.querySelectorAll('[data-role="view-mode"]').forEach(function(button){
    button.addEventListener('click',function(){
      root.querySelectorAll('[data-role="view-mode"]').forEach(function(item){item.setAttribute('aria-pressed','false')});
      button.setAttribute('aria-pressed','true');view=button.getAttribute('data-mode');render();
    });
  });
  root.querySelectorAll('[data-role="room-filter"]').forEach(function(button){
    button.addEventListener('click',function(){
      root.querySelectorAll('[data-role="room-filter"]').forEach(function(item){item.setAttribute('aria-pressed','false')});
      button.setAttribute('aria-pressed','true');filter=button.getAttribute('data-filter');limit=100;render();
    });
  });
  search.addEventListener('input',function(){query=search.value;limit=100;render()});
  certificateSelect.addEventListener('change',function(){certificate=certificateSelect.value;building='all';unit='all';limit=100;render()});
  buildingSelect.addEventListener('change',function(){building=buildingSelect.value;unit='all';limit=100;render()});
  unitSelect.addEventListener('change',function(){unit=unitSelect.value;limit=100;render()});
  [['price-min','priceMin'],['price-max','priceMax'],['total-min','totalMin'],['total-max','totalMax']].forEach(function(pair){
    var input=root.querySelector('[data-role="'+pair[0]+'"]');if(!input)return;
    input.addEventListener('input',function(){bounds[pair[1]]=input.value===''?null:Number(input.value);if(input.value!==''&&!isFinite(bounds[pair[1]]))bounds[pair[1]]=null;limit=100;render()});
  });
  more.addEventListener('click',function(){limit+=200;render()});
  function loadJSON(url){
    if(!/\.json\.gz$/.test(url))return fetch(url).then(function(response){if(!response.ok)throw new Error('HTTP '+response.status);return response.json()});
    if(typeof DecompressionStream==='undefined')return Promise.reject(new Error('当前浏览器不支持解压静态 JSON'));
    return fetch(url).then(function(response){if(!response.ok)throw new Error('HTTP '+response.status);return response.arrayBuffer()}).then(function(buffer){
      var stream=new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'));return new Response(stream).json();
    });
  }
  loadJSON(url).then(function(data){
    if(data&&data.status&&data.status!=='complete')throw new Error(data.message||'接口返回错误');
    rooms=[];
    (data.certificates||[]).forEach(function(certificate){
      var id=String(certificate.id||'unknown');var name=certificate.name||('预售证 '+id);
      var option=document.createElement('option');option.value=id;option.textContent=name;certificateSelect.appendChild(option);
      (certificate.rooms||[]).forEach(function(room){rooms.push(Object.assign({},pickRoom(room),{certificateId:id,certificateName:name}))});
    });
    priceGroups=buildPricePalette(rooms);render();
  }).catch(function(error){
    tbody.replaceChildren(document.createElement('tr'));
    var cell=document.createElement('td');cell.colSpan=11;cell.className='loading';
    cell.textContent='一房一价明细载入失败：'+error.message;tbody.firstChild.appendChild(cell);
    floorRenderToken++;floorResults.replaceChildren();var floorError=document.createElement('p');floorError.className='loading';floorError.textContent='楼层分布载入失败：'+error.message;floorResults.appendChild(floorError);if(backToOverview)floorResults.appendChild(backToOverview);
    count.textContent='载入失败';more.hidden=true;
  });
})();
'''
