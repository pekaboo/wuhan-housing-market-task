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

    generated_at = snapshot.get('generatedAt') if isinstance(snapshot, dict) else None
    generated_label = generated_at or '载入中'

    return f'''<section id="one-price" class="one-price" data-one-price-url="{esc(data_url)}" data-generated-at="{esc(generated_at or '')}" aria-labelledby="one-price-title">
      <div class="one-price-head">
        <div><h2 id="one-price-title">一房一价</h2><p>按预售证聚合房号、面积、单价、总价、销售与异常状态；支持明细表与真实楼层分布两种视图。</p></div>
        <a href="{esc(data_url)}" download>JSON 明细</a>
      </div>
{status_html}
      <div class="one-price-summary" data-role="one-price-summary">{summary_html}</div>
      <div class="room-controls">
        <div class="controls-heading">
          <div class="view-switch" role="group" aria-label="一房一价视图">
            <button type="button" data-role="view-mode" data-mode="table" aria-pressed="true">明细表</button>
            <button type="button" data-role="view-mode" data-mode="floor" aria-pressed="false">楼层分布</button>
          </div>
          <div class="filter-actions">
            <button type="button" class="filter-toggle" data-role="filter-toggle" aria-expanded="true" aria-controls="price-filter-panel"><svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 6h16M7 12h10M10 18h4"/></svg><span>筛选</span><span class="filter-count" data-role="filter-count" hidden>0</span></button>
            <button type="button" data-role="reset-filters">清除</button>
          </div>
        </div>
        <div class="filter-panel" id="price-filter-panel" data-role="filter-panel" role="region" aria-label="一房一价筛选条件">
          <div class="filter-row filter-primary">
            <label class="select-field"><span>预售证</span><select data-role="certificate-filter" aria-label="筛选预售证"><option value="all">全部</option></select></label>
            <label class="select-field"><span>楼栋</span><select data-role="building-filter" aria-label="筛选楼栋"><option value="all">全部</option></select></label>
            <label class="select-field"><span>单元</span><select data-role="unit-filter" aria-label="筛选单元"><option value="all">全部</option></select></label>
            <label class="select-field search-field"><span>搜索</span><input data-role="room-search" type="search" placeholder="房号 / 楼层 / 户型" autocomplete="off"></label>
          </div>
          <div class="filter-row filter-secondary">
            <div class="room-filters" role="group" aria-label="房源状态筛选">
              <button type="button" data-role="room-filter" data-filter="all" aria-pressed="true"><span>全部</span></button>
              <button type="button" data-role="room-filter" data-filter="available" aria-pressed="false"><i class="state-dot" aria-hidden="true"></i><span>可售</span></button>
              <button type="button" data-role="room-filter" data-filter="sold" aria-pressed="false"><i class="state-dot" aria-hidden="true"></i><span>已售</span></button>
              <button type="button" data-role="room-filter" data-filter="abnormal" aria-pressed="false"><i class="state-dot" aria-hidden="true"></i><span>异常</span></button>
            </div>
            <div class="range-filter" role="group" aria-label="单价范围，单位元每平方米">
              <span class="range-name">单价</span>
              <input data-role="price-min" type="number" min="0" step="100" inputmode="numeric" placeholder="最低" aria-label="单价下限">
              <span class="range-sep" aria-hidden="true">—</span>
              <input data-role="price-max" type="number" min="0" step="100" inputmode="numeric" placeholder="最高" aria-label="单价上限">
              <span class="range-unit">元/㎡</span>
            </div>
            <div class="range-filter" role="group" aria-label="总价范围，单位万元">
              <span class="range-name">总价</span>
              <input data-role="total-min" type="number" min="0" step="10000" inputmode="numeric" placeholder="最低" aria-label="总价下限">
              <span class="range-sep" aria-hidden="true">—</span>
              <input data-role="total-max" type="number" min="0" step="10000" inputmode="numeric" placeholder="最高" aria-label="总价上限">
              <span class="range-unit">万元</span>
            </div>
            <div class="discount-filter" role="group" aria-label="价格折扣">
              <label class="discount-input"><span>折扣</span><input data-role="discount-filter" type="number" min="1" max="100" step="1" value="100" inputmode="numeric" aria-label="价格折扣百分比"></label>
              <div class="discount-presets" aria-label="常用折扣">
                <button type="button" data-role="discount-preset" data-discount="100" aria-pressed="true">100%</button>
                <button type="button" data-role="discount-preset" data-discount="95" aria-pressed="false">95%</button>
                <button type="button" data-role="discount-preset" data-discount="90" aria-pressed="false">90%</button>
                <button type="button" data-role="discount-preset" data-discount="85" aria-pressed="false">85%</button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <button type="button" class="floor-filter-floating" data-role="open-floor-filters" aria-controls="price-filter-panel">筛选</button>
      <button type="button" class="floor-filter-scrim" data-role="close-floor-filters" aria-label="关闭筛选侧栏"></button>
      <div class="floor-toolbar" aria-label="楼层分布缩放控制" hidden>
        <span class="floor-data-time"><span>数据时间</span><strong data-role="floor-data-time">{esc(generated_label)}</strong></span>
        <button type="button" data-role="zoom-in">放大</button>
        <button type="button" data-role="zoom-out">缩小</button>
        <button type="button" data-role="reset-zoom">复位</button>
        <button type="button" data-role="floor-fullscreen" aria-pressed="false">全屏地图</button>
        <label class="zoom-control">缩放<input data-role="zoom-range" type="range" min="18" max="220" step="1" value="100" aria-label="楼层分布缩放比例"></label>
        <button type="button" data-role="all-buildings">全部楼栋</button>
        <button type="button" data-role="download-floor-image">下载图片</button>
        <span><output data-role="zoom-scale">100%</output></span>
      </div>
      <p class="floor-note">楼层分布按“楼栋 + 单元”排布：楼栋从左到右、楼层从上到下、同一楼层横向一排。地图式操作：拖拽 / 滚轮上下平移，双指捏合等比缩放；已售为红色，可售为绿色，右上角小方块表示单价且相同价格同色；筛选外房源保留原位置并变成灰色方块。图片导出会带上当前筛选结果与数据时间。</p>
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



ONE_PRICE_CSS = r'''.one-price{overflow:hidden;margin:0 0 24px;border:1px solid var(--line);border-radius:18px;background:var(--panel);box-shadow:var(--shadow)}.one-price.empty{display:grid;min-height:170px;place-items:center;color:var(--muted)}.one-price-head{display:flex;justify-content:space-between;gap:16px;align-items:start;padding:18px 18px 14px}.one-price-head h2{margin:0}.one-price-head p{margin:4px 0 0;color:var(--muted);font-size:13px}.one-price-head a{display:inline-flex;min-height:36px;align-items:center;padding:0 12px;border-radius:10px;background:var(--panel-soft);color:var(--brand-ink);font-size:12px;font-weight:800;text-decoration:none;white-space:nowrap}.one-price-error{margin:0;padding:13px 18px;background:color-mix(in srgb,#b42318 10%,var(--panel));color:#b42318;font-weight:750}.one-price-note{margin:0;padding:14px 18px;color:var(--muted)}.one-price-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:1px;background:var(--panel-soft)}.one-price-metric{min-width:0;padding:13px;background:var(--panel)}.one-price-metric span{display:block;color:var(--muted);font-size:11px}.one-price-metric strong{display:block;margin-top:2px;font-size:21px;letter-spacing:-.045em}.one-price-metric.available strong{color:#137a4b}.one-price-metric.sold strong{color:#a35613}.one-price-metric.abnormal strong{color:#a33815}@media (prefers-color-scheme:dark){.one-price-metric.available strong{color:#75d9a5}.one-price-metric.sold strong{color:#f0b76a}.one-price-metric.abnormal strong{color:#ff9d7a}.one-price-error{background:#43110c;color:#ffab94}}.room-controls{position:relative;z-index:6;display:flex;flex-direction:column;gap:9px;padding:12px 14px;border-top:1px solid var(--line);background:var(--panel-soft)}.controls-heading{display:flex;align-items:center;justify-content:space-between;gap:10px}.view-switch{display:grid;grid-template-columns:repeat(2,minmax(78px,1fr));gap:3px;padding:3px;border:1px solid var(--line);border-radius:13px;background:var(--panel)}.view-switch button{height:34px;padding:0 12px;border:0;border-radius:10px;background:transparent;color:var(--muted);font:inherit;font-size:12px;font-weight:800;cursor:pointer;transition:background .18s var(--ease-out),color .18s var(--ease-out)}.view-switch button[aria-pressed=true]{background:var(--brand);color:#fff}.filter-actions{display:flex;align-items:center;gap:6px}.filter-actions button{display:inline-flex;min-height:36px;align-items:center;justify-content:center;gap:6px;padding:0 12px;border:1px solid var(--line);border-radius:999px;background:var(--panel);color:var(--ink);font:inherit;font-size:12px;font-weight:800;cursor:pointer;transition:background .18s var(--ease-out),border-color .18s var(--ease-out),color .18s var(--ease-out)}.filter-actions button:hover{border-color:color-mix(in srgb,var(--brand) 35%,var(--line));color:var(--brand-ink)}.filter-actions button:disabled{cursor:not-allowed;opacity:.45}.filter-actions button:focus-visible,.view-switch button:focus-visible,.room-filters button:focus-visible{outline:3px solid color-mix(in srgb,var(--focus) 56%,transparent);outline-offset:2px}.filter-toggle svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;transition:transform .18s var(--ease-out)}.filter-toggle[aria-expanded=false] svg{transform:rotate(-90deg)}.filter-toggle.is-active{border-color:color-mix(in srgb,var(--brand) 36%,var(--line));background:color-mix(in srgb,var(--brand) 10%,var(--panel));color:var(--brand-ink)}.filter-count{min-width:19px;padding:2px 5px;border-radius:999px;background:var(--brand);color:#fff;font-size:10px;line-height:1.2;font-variant-numeric:tabular-nums}.filter-panel{display:flex;min-width:0;flex-direction:column;gap:8px}.filter-panel[hidden]{display:none}.filter-row{display:grid;min-width:0;gap:7px}.filter-primary{grid-template-columns:minmax(160px,1.05fr) minmax(130px,.9fr) minmax(115px,.75fr) minmax(220px,1.25fr)}.filter-secondary{grid-template-columns:minmax(305px,auto) minmax(285px,1fr) minmax(275px,1fr);align-items:center}.select-field{display:grid;min-width:0;grid-template-columns:auto minmax(0,1fr);align-items:center;gap:8px;height:38px;padding:0 10px;border:1px solid var(--line);border-radius:11px;background:var(--panel);color:var(--muted);font-size:11px;font-weight:800;letter-spacing:-.01em}.select-field span{white-space:nowrap}.select-field select,.select-field input{min-width:0;height:34px;border:0;background:transparent;color:var(--ink);font:inherit;font-size:13px;font-weight:600;outline:none}.select-field select{appearance:none;padding-right:20px;background-image:linear-gradient(45deg,transparent 0 46%,currentColor 46% 54%,transparent 54%),linear-gradient(135deg,transparent 0 46%,currentColor 46% 54%,transparent 54%);background-repeat:no-repeat;background-position:right 6px center,right 12px center;background-size:5px 5px}.select-field:focus-within{border-color:var(--focus);box-shadow:0 0 0 3px color-mix(in srgb,var(--focus) 16%,transparent)}.room-filters{display:flex;min-width:0;align-items:center;gap:5px;padding:3px;border:1px solid var(--line);border-radius:13px;background:var(--panel)}.room-filters button{display:inline-flex;height:34px;align-items:center;justify-content:center;gap:6px;padding:0 10px;border:0;border-radius:10px;background:transparent;color:var(--muted);font:inherit;font-size:12px;font-weight:800;cursor:pointer;transition:background .18s var(--ease-out),color .18s var(--ease-out)}.room-filters button[aria-pressed=true]{background:var(--panel-soft);color:var(--ink);box-shadow:inset 0 0 0 1px var(--line)}.room-filters button[data-filter=available][aria-pressed=true]{color:#116b43;background:color-mix(in srgb,#34c759 15%,var(--panel))}.room-filters button[data-filter=sold][aria-pressed=true]{color:#a33815;background:color-mix(in srgb,#ff9f0a 18%,var(--panel))}.room-filters button[data-filter=abnormal][aria-pressed=true]{color:#b42318;background:color-mix(in srgb,#ff453a 14%,var(--panel))}.state-dot{width:7px;height:7px;border-radius:999px;background:var(--muted)}.room-filters button[data-filter=available] .state-dot{background:#34c759}.room-filters button[data-filter=sold] .state-dot{background:#ff9f0a}.room-filters button[data-filter=abnormal] .state-dot{background:#ff453a}.range-filter{display:grid;min-width:0;grid-template-columns:auto minmax(78px,1fr) auto minmax(78px,1fr) auto;align-items:center;gap:6px;min-height:40px;padding:3px 9px;border:1px solid var(--line);border-radius:13px;background:var(--panel);color:var(--muted);font-size:11px;font-weight:800}.range-filter input{min-width:0;height:32px;border:0;background:transparent;color:var(--ink);font:inherit;font-size:13px;font-weight:650;font-variant-numeric:tabular-nums;text-align:right;outline:none}.range-filter input::placeholder{color:var(--muted);font-weight:550;text-align:right}.range-sep{color:var(--line-strong)}.range-name,.range-unit{white-space:nowrap}.range-filter:focus-within{border-color:var(--focus);box-shadow:0 0 0 3px color-mix(in srgb,var(--focus) 16%,transparent)}@media (prefers-color-scheme:dark){.view-switch button[aria-pressed=true],.filter-count{color:#07131d}.room-filters button[data-filter=available][aria-pressed=true]{color:#8ef0b1}.room-filters button[data-filter=sold][aria-pressed=true]{color:#ffd6a1}.room-filters button[data-filter=abnormal][aria-pressed=true]{color:#ffaaa0}.filter-toggle.is-active{background:color-mix(in srgb,#2997ff 18%,var(--panel));color:#8fc6ff}}.floor-note{margin:0;padding:9px 15px;border-top:1px solid var(--line);background:var(--panel);color:var(--muted);font-size:12px}.room-table-wrap{overflow-x:auto;border-top:1px solid var(--line)}.room-table{width:100%;min-width:1030px;border-collapse:collapse;font-size:13px}.room-table th,.room-table td{padding:11px 13px;border-top:1px solid var(--line);text-align:left;vertical-align:top;white-space:nowrap}.room-table thead th{position:sticky;top:0;background:var(--panel);color:var(--muted);font-size:11px}.room-table td.loading{color:var(--muted)}.status{display:inline-flex;height:24px;align-items:center;padding:0 8px;border-radius:999px;background:var(--panel-soft);color:var(--muted);font-size:11px;font-weight:800}.status.available{color:#137a4b;background:color-mix(in srgb,#137a4b 12%,var(--panel))}.status.sold{color:#a35613;background:color-mix(in srgb,#a35613 12%,var(--panel))}.status.abnormal{margin-left:5px;color:#a33815;background:color-mix(in srgb,#a33815 12%,var(--panel))}@media (prefers-color-scheme:dark){.status.available{color:#75d9a5}.status.sold{color:#f0b76a}.status.abnormal{color:#ff9d7a}}.floor-results{--floor-scale:1;--pan-x:0px;--pan-y:0px;--map-surface:#f0f2f5;--map-panel:#ffffff;--map-panel-soft:#f7f8fa;--map-ink:#1d1d1f;--map-muted:#6e6e73;--map-line:#d2d2d7;--map-line-strong:#a1a1a6;--map-brand:#0071e3;--map-brand-ink:#0066cc;--map-focus:#0071e3;--map-available:#34c759;--map-sold:#ff3b30;--map-ghost:#8e8e93;--floor-axis:52px;--floor-height:96px;--room-width:112px;position:relative;padding:0;border-top:1px solid var(--map-line);background:var(--map-surface);color:var(--map-ink)}
.one-price.floor-fullscreen{position:fixed;inset:0;z-index:80;display:flex;flex-direction:column;border:0;border-radius:0;background:#f0f2f5;overflow:hidden}.one-price.floor-fullscreen>*:not(.room-controls):not(.floor-toolbar):not(.floor-results){display:none}.one-price.floor-fullscreen .room-controls{position:absolute;top:14px;left:14px;right:14px;z-index:30;max-height:calc(100% - 28px);overflow:auto;border:1px solid color-mix(in srgb,#ffffff 58%,transparent);border-radius:18px;background:color-mix(in srgb,#ffffff 88%,transparent);box-shadow:0 18px 48px #0000001f;backdrop-filter:saturate(180%) blur(24px);-webkit-backdrop-filter:saturate(180%) blur(24px)}.one-price.floor-fullscreen .filter-primary{grid-template-columns:repeat(4,minmax(145px,1fr))}.one-price.floor-fullscreen .filter-secondary{grid-template-columns:minmax(305px,auto) minmax(285px,1fr) minmax(275px,1fr)}.one-price.floor-fullscreen .floor-toolbar{position:absolute;right:16px;bottom:16px;z-index:30;justify-content:center;max-width:calc(100% - 32px);border:1px solid color-mix(in srgb,#ffffff 58%,transparent);border-radius:18px;box-shadow:0 18px 48px #00000024}.one-price.floor-fullscreen .back-overview{top:auto;right:auto;bottom:76px;left:16px}.one-price.floor-fullscreen .floor-render-status{bottom:76px}.one-price.floor-fullscreen .floor-results{display:flex;flex:1;min-height:0;flex-direction:column;border-top:0}.one-price.floor-fullscreen .floor-stage.floor-map{flex:1;height:auto;min-height:0}.one-price.floor-fullscreen .floor-fullscreen-floating{display:none}.floor-fullscreen-floating{position:absolute;top:12px;right:12px;z-index:13;display:inline-flex;min-height:40px;align-items:center;justify-content:center;padding:0 15px;border:0;border-radius:999px;background:var(--map-brand);color:#fff;font:inherit;font-size:12px;font-weight:850;letter-spacing:-.01em;cursor:pointer;box-shadow:0 8px 24px #00000024;transition:transform .18s var(--ease-out),box-shadow .18s var(--ease-out),background .18s var(--ease-out)}.floor-fullscreen-floating:hover{background:var(--map-brand-ink);box-shadow:0 10px 28px #00000030}.floor-fullscreen-floating:active{transform:scale(.97)}.floor-fullscreen-floating:focus-visible{outline:3px solid color-mix(in srgb,var(--map-focus) 58%,transparent);outline-offset:3px}.floor-results>.loading{margin:0;padding:16px;color:var(--map-muted)}.floor-render-status{position:absolute;left:50%;bottom:12px;z-index:11;margin:0;padding:5px 10px;border:1px solid var(--map-line);border-radius:999px;background:color-mix(in srgb,var(--map-panel) 88%,transparent);color:var(--map-muted);font-size:10px;font-weight:750;box-shadow:0 8px 24px #00000014;transform:translateX(-50%);pointer-events:none}
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
@media (prefers-color-scheme:dark){.floor-results{--map-surface:#0b141c;--map-panel:#1d1d20;--map-panel-soft:#2c2c2e;--map-ink:#f5f5f7;--map-muted:#a1a1a6;--map-line:#38383a;--map-line-strong:#5a5a5e;--map-brand:#2997ff;--map-brand-ink:#64a8ff;--map-focus:#64a8ff;--map-available:#30d158;--map-sold:#ff453a;--map-ghost:#98989d}.one-price.floor-fullscreen{background:#0b141c}.one-price.floor-fullscreen .room-controls{border-color:#48484a;background:color-mix(in srgb,#1d1d20 88%,transparent);box-shadow:0 18px 48px #00000073}.one-price.floor-fullscreen .floor-toolbar{border-color:#48484a;box-shadow:0 18px 48px #00000073}.floor-toolbar,.zoom-control,.floor-toolbar span{background:color-mix(in srgb,#1d1d20 82%,transparent)}.floor-toolbar button,.floor-toolbar span,.zoom-control{border-color:#48484a}.floor-stage.floor-map{background-image:radial-gradient(circle at 50% 0,color-mix(in srgb,#2c2c2e 58%,transparent) 0,transparent 62%),repeating-linear-gradient(90deg,color-mix(in srgb,#f5f5f7 5%,transparent) 0 1px,transparent 1px 32px),repeating-linear-gradient(180deg,color-mix(in srgb,#f5f5f7 5%,transparent) 0 1px,transparent 1px 32px)}.floor-room{box-shadow:0 1px 2px #00000040}.floor-room.filtered-out,.floor-missing{background:color-mix(in srgb,#98989d 15%,transparent)}}.overview-grid{display:grid;width:100%;max-width:1440px;grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:18px;margin:0 auto}.building-overview{position:relative;min-width:0;padding:0;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink);font:inherit;cursor:pointer}.building-overview:hover,.building-overview:active{border-color:color-mix(in srgb,var(--brand) 48%,var(--line));transform:translateY(-1px)}.building-overview .floor-column-head{min-height:46px;border:0;background:transparent}.overview-body{position:relative;display:block;margin:0 8px 10px;height:calc(var(--floors,1)*10px + 18px)}.overview-face{position:absolute;inset:0;border:1px solid color-mix(in srgb,var(--ink) 28%,var(--line));border-radius:4px;background:linear-gradient(to top,color-mix(in srgb,#17935d calc(var(--match-ratio,1)*60%),transparent) 0,transparent calc(var(--match-ratio,1)*100%)),repeating-linear-gradient(to top,color-mix(in srgb,var(--ink) 18%,transparent) 0 1px,transparent 1px 10px)}.overview-scale{position:absolute;bottom:-19px;left:50%;white-space:nowrap;color:var(--muted);font-size:9px;font-weight:850;transform:translateX(-50%)}.building-overview:focus-visible{outline:3px solid var(--focus);outline-offset:3px}.room-foot{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 15px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}.room-foot p{margin:0}.room-foot button{height:36px;padding:0 13px;border:0;border-radius:10px;background:var(--brand);color:#fff;font:inherit;font-size:12px;font-weight:800;cursor:pointer}@media (prefers-color-scheme:dark){.room-foot button{color:#07131d}.view-switch button[aria-pressed=true],.room-filters button[aria-pressed=true]{color:#07131d}}.certificate-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1px;padding:1px;background:var(--panel-soft);border-top:1px solid var(--line)}.certificate-card{min-width:0;padding:14px;background:var(--panel)}.certificate-card h3{margin:0 0 8px;font-size:13px;line-height:1.45;overflow-wrap:anywhere}.certificate-card dl{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:0}.certificate-card div{min-width:0}.certificate-card dt{color:var(--muted);font-size:10px}.certificate-card dd{margin:2px 0 0;font-size:14px;font-weight:800}@media (max-width:1100px){.filter-primary{grid-template-columns:repeat(2,minmax(0,1fr))}.filter-secondary{grid-template-columns:1fr}}@media (max-width:760px){.floor-toolbar{right:10px;bottom:10px;max-width:calc(100% - 20px)}.floor-toolbar button{height:44px}.floor-toolbar span,.zoom-control{min-height:44px}.one-price-head{align-items:start;flex-direction:column}.one-price-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.one-price-metric:last-child{grid-column:1/-1}.room-controls{padding:10px}.controls-heading{align-items:stretch;flex-direction:column}.view-switch{grid-template-columns:1fr 1fr}.view-switch button,.room-filters button,.filter-actions button{min-height:42px}.filter-actions{display:grid;grid-template-columns:1fr 1fr}.filter-actions button{width:100%}.filter-primary{grid-template-columns:1fr}.select-field{height:44px}.select-field select,.select-field input{height:40px}.filter-secondary{align-items:stretch}.room-filters{overflow-x:auto;padding-bottom:2px}.range-filter{grid-template-columns:auto minmax(72px,1fr) auto minmax(72px,1fr) auto}.one-price.floor-fullscreen .room-controls{top:10px;left:10px;right:10px;max-height:calc(100% - 20px)}.one-price.floor-fullscreen .back-overview,.one-price.floor-fullscreen .floor-render-status{bottom:74px}.room-foot{align-items:stretch;flex-direction:column}.room-foot button{width:100%}.certificate-card dl{grid-template-columns:repeat(2,1fr)}}@media (max-width:430px){.filter-actions{grid-template-columns:1fr}.range-filter{grid-template-columns:auto minmax(58px,1fr) auto minmax(58px,1fr) auto}.range-unit{display:none}}@media (prefers-reduced-motion:reduce){.one-price *,.one-price *::before,.one-price *::after{transition-duration:.01ms!important;animation-duration:.01ms!important}}'''


FLOOR_MOBILE_CSS = r'''
.filter-panel{border-radius:18px}
.discount-filter{display:flex;align-items:center;justify-content:space-between;gap:8px;min-width:0;padding:7px 9px;border:1px solid var(--line);border-radius:12px;background:var(--panel-soft)}
.discount-input{display:flex;align-items:center;gap:7px;min-width:104px}
.discount-input span{color:var(--muted);font-size:10px;font-weight:750}
.discount-input input{width:68px;min-height:34px;padding:4px 8px;border:1px solid var(--line);border-radius:9px;background:var(--panel);color:var(--ink);font:inherit;font-size:13px;font-variant-numeric:tabular-nums;text-align:center}
.discount-presets{display:grid;grid-template-columns:repeat(4,minmax(44px,1fr));gap:4px;min-width:0}
.discount-presets button{min-height:32px;padding:0 5px;border:1px solid var(--line);border-radius:999px;background:var(--panel);color:var(--muted);font:inherit;font-size:11px;font-weight:750;cursor:pointer}
.discount-presets button[aria-pressed=true]{border-color:var(--brand);background:color-mix(in srgb,var(--brand) 10%,var(--panel));color:var(--brand-ink)}
.floor-column-head,.building-cell{backdrop-filter:none;-webkit-backdrop-filter:none;background:var(--map-panel)}
.floor-room{box-shadow:none;transition:none}
@media (hover:hover) and (prefers-reduced-motion:no-preference){.floor-room{transition:border-color .18s var(--ease-out)}}
.floor-data-time{flex:1 1 190px;flex-direction:column;align-items:flex-start;justify-content:center;min-width:0;min-height:34px;padding:4px 10px;text-align:left}
.floor-data-time span{min-height:0;padding:0;color:var(--map-muted);font-size:9px;line-height:1.2}
.floor-data-time strong{max-width:100%;overflow:hidden;color:var(--map-ink);font-size:11px;font-variant-numeric:tabular-nums;text-overflow:ellipsis;white-space:nowrap}
.floor-export-busy{position:absolute;left:50%;bottom:12px;z-index:20;margin:0;padding:6px 12px;border:1px solid var(--map-line);border-radius:999px;background:var(--map-panel);color:var(--map-ink);font-size:11px;font-weight:750;box-shadow:0 10px 30px #00000022;transform:translateX(-50%)}
body.one-price-filters-open{overflow:hidden}
.floor-filter-floating,.floor-filter-scrim{display:none}
@media (max-width:1100px){.filter-secondary{grid-template-columns:repeat(2,minmax(0,1fr))}.discount-filter{grid-column:1/-1}}
@media (max-width:760px){
  .one-price.floor-view .room-controls{position:fixed;top:0;left:0;bottom:0;z-index:70;width:min(88vw,360px);max-height:none;box-sizing:border-box;overflow-y:auto;overscroll-behavior:contain;border:0;border-radius:0 20px 20px 0;background:var(--panel);box-shadow:14px 0 44px #00000038;transition:transform .22s var(--ease-out),visibility .22s}
  .one-price.floor-view[data-filters-open=closed] .room-controls{visibility:hidden;transform:translateX(-102%)}
  .one-price.floor-view[data-filters-open=open] .room-controls{visibility:visible;transform:none}
  .one-price.floor-view[data-filters-open=closed]>.floor-filter-floating{position:fixed;top:calc(10px + env(safe-area-inset-top,0px));right:10px;z-index:70;display:inline-flex;min-height:42px;align-items:center;justify-content:center;padding:0 15px;border:0;border-radius:999px;background:var(--map-brand);color:#fff;font:inherit;font-size:12px;font-weight:850;box-shadow:0 10px 28px #00000030}
  .one-price.floor-view[data-filters-open=open]>.floor-filter-scrim{position:fixed;inset:0;z-index:60;display:block;border:0;padding:0;background:#00000066;backdrop-filter:saturate(120%) blur(2px)}
  .one-price.floor-fullscreen>.floor-filter-floating,.one-price.floor-fullscreen>.floor-filter-scrim{display:inline-flex}
  .one-price.floor-fullscreen[data-filters-open=closed]>.floor-filter-scrim{display:none}
  .one-price.floor-view .controls-heading{position:sticky;top:0;z-index:2;padding:8px;border-radius:0;background:var(--panel)}
  .one-price.floor-view .filter-panel{margin:0 8px 10px}
  .one-price.floor-view .filter-primary{grid-template-columns:1fr!important}
  .one-price.floor-view .filter-secondary{grid-template-columns:1fr!important}
  .floor-toolbar{flex-wrap:nowrap;gap:5px;padding:7px 9px;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none}
  .floor-toolbar::-webkit-scrollbar{display:none}
  .floor-toolbar button,.zoom-control{flex:0 0 auto}.floor-toolbar button{height:38px;padding:0 10px;font-size:11px;white-space:nowrap}
  .one-price.floor-fullscreen .floor-toolbar{right:10px;bottom:calc(10px + env(safe-area-inset-bottom,0px));left:10px;justify-content:flex-start;max-height:48px;overflow-x:auto}
  .floor-data-time{flex:0 0 auto;max-width:150px}.zoom-control{gap:6px}.zoom-control input{width:112px}
  .filter-panel{gap:7px;padding:8px}.discount-filter{align-items:stretch;flex-direction:column}.discount-presets{width:100%}
  .room-filters{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))}.room-filters button{justify-content:center;padding:0 4px}
  .range-filter{grid-template-columns:auto minmax(64px,1fr) 7px minmax(64px,1fr) auto}
}
@media (max-width:430px){.discount-presets{grid-template-columns:repeat(2,minmax(0,1fr))}.range-unit{display:none}}
'''


ONE_PRICE_JS = r'''(function(){
  'use strict';
  var root=document.querySelector('[data-one-price-url]');
  if(!root)return;
  var url=root.getAttribute('data-one-price-url');
  var view='table',filter='all',certificate='all',building='all',unit='all',query='',limit=100;
  var bounds={priceMin:null,priceMax:null,totalMin:null,totalMax:null};
  var discountRate=100,renderTimer=null,dataTime=root.getAttribute('data-generated-at')||'';
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
  var discountInput=root.querySelector('[data-role="discount-filter"]');
  var roomControls=root.querySelector('.room-controls');
  var filterPanel=root.querySelector('[data-role="filter-panel"]');
  var filterToggle=root.querySelector('[data-role="filter-toggle"]');
  var filterCount=root.querySelector('[data-role="filter-count"]');
  var resetFiltersButton=root.querySelector('[data-role="reset-filters"]');
  var downloadFloorButton=root.querySelector('[data-role="download-floor-image"]');
  var floorDataTime=root.querySelector('[data-role="floor-data-time"]');
  var filtersOpen=filterPanel?!(filterPanel.hidden||window.matchMedia('(max-width: 760px)').matches):false;
  if(filterPanel)filterPanel.hidden=!filtersOpen;
  var rooms=[];
  var priceGroups=new Map();
  function text(value){return value===null||value===undefined||value===''?'—':String(value);}
  function pickRoom(room){var picked=Object.assign({},room,{
    buildName:room.buildName!==undefined?room.buildName:room.buildingName,
    unitName:room.unitName!==undefined?room.unitName:room.unit,
    floor:room.floor!==undefined?room.floor:room.floorName,
    roomName:room.roomName,
    roomLayout:room.roomLayout!==undefined?room.roomLayout:room.houseType,
    area:room.area!==undefined?room.area:room.buildArea
  });picked.searchText=[picked.certificateName,picked.buildName,picked.unitName,picked.floor,picked.roomName,picked.roomLayout,picked.price,picked.totalPrice].join(' ').toLowerCase();return picked}
  function numericValue(value){if(value===null||value===undefined||value==='')return null;var parsed=Number(value);return isFinite(parsed)?parsed:null;}
  function totalYuan(value){return numericValue(value);}
  function discounted(value){var parsed=numericValue(value);return parsed===null?null:parsed*discountRate/100}
  function number(value){var parsed=Number(value);return isFinite(parsed)?parsed.toLocaleString('zh-CN'):text(value);}
  function area(value){var parsed=Number(value);return isFinite(parsed)?parsed.toLocaleString('zh-CN',{maximumFractionDigits:2})+' ㎡':text(value);}
  function money(value){var parsed=Number(value);return isFinite(parsed)?parsed.toLocaleString('zh-CN',{maximumFractionDigits:0})+' 元/㎡':text(value);}
  function total(value){var parsed=Number(value);return isFinite(parsed)?parsed.toLocaleString('zh-CN',{maximumFractionDigits:0})+' 元':text(value);}
  function setDataTime(value){
    dataTime=text(value||dataTime);root.setAttribute('data-generated-at',dataTime==='—'?'':dataTime);
    if(floorDataTime)floorDataTime.textContent=dataTime;
  }
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
    var price=discounted(room.price);var totalPrice=discounted(room.totalPrice);
    if(bounds.priceMin!==null&&(price===null||price<bounds.priceMin))return false;
    if(bounds.priceMax!==null&&(price===null||price>bounds.priceMax))return false;
    if(bounds.totalMin!==null&&(totalPrice===null||totalPrice<bounds.totalMin*10000))return false;
    if(bounds.totalMax!==null&&(totalPrice===null||totalPrice>bounds.totalMax*10000))return false;
    var haystack=room.searchText||[room.certificateName,room.buildName,room.unitName,room.floor,room.roomName,room.roomLayout,room.price,room.totalPrice].join(' ').toLowerCase();
    return query.trim().toLowerCase().split(/\s+/).filter(Boolean).every(function(word){return haystack.indexOf(word)>=0});
  }
  function filterRooms(){
    return scopedRooms().filter(roomMatches);
  }
  function activeFilterCount(){
    var count=0;
    if(certificate!=='all')count++;
    if(building!=='all')count++;
    if(unit!=='all')count++;
    if(filter!=='all')count++;
    if(query.trim())count++;
    Object.keys(bounds).forEach(function(key){if(bounds[key]!==null&&isFinite(bounds[key]))count++});
    if(discountRate!==100)count++;
    return count;
  }
  function syncDiscountControls(){
    if(discountInput)discountInput.value=String(discountRate);
    root.querySelectorAll('[data-role="discount-preset"]').forEach(function(button){
      button.setAttribute('aria-pressed',Number(button.getAttribute('data-discount'))===discountRate?'true':'false')
    });
  }
  function syncFilterControls(){
    var count=activeFilterCount();
    root.dataset.filtersOpen=filtersOpen?'open':'closed';
    if(roomControls)roomControls.dataset.filtersOpen=filtersOpen?'open':'closed';
    if(filterPanel)filterPanel.hidden=!filtersOpen;
    document.body.classList.toggle('one-price-filters-open',filtersOpen&&view==='floor'&&window.matchMedia('(max-width: 760px)').matches);
    if(filterToggle){
      filterToggle.setAttribute('aria-expanded',filtersOpen?'true':'false');
      filterToggle.classList.toggle('is-active',count>0);
    }
    if(filterCount){
      filterCount.textContent=String(count);
      filterCount.hidden=count===0;
    }
    if(resetFiltersButton)resetFiltersButton.disabled=count===0;
  }
  function clearAllFilters(){
    certificate='all';building='all';unit='all';filter='all';query='';limit=100;
    bounds={priceMin:null,priceMax:null,totalMin:null,totalMax:null};
    discountRate=100;syncDiscountControls();
    if(certificateSelect)certificateSelect.value='all';
    if(buildingSelect)buildingSelect.value='all';
    if(unitSelect)unitSelect.value='all';
    if(search)search.value='';
    root.querySelectorAll('[data-role="room-filter"]').forEach(function(item){item.setAttribute('aria-pressed',item.getAttribute('data-filter')==='all'?'true':'false')});
    [['price-min','priceMin'],['price-max','priceMax'],['total-min','totalMin'],['total-max','totalMax']].forEach(function(pair){
      var input=root.querySelector('[data-role="'+pair[0]+'"]');if(input)input.value='';
    });
    render();
  }
  function row(room){
    var tr=document.createElement('tr');
    [room.buildName,room.unitName,room.floor,room.roomName,room.roomLayout].forEach(function(value){
      var cell=document.createElement('td');cell.textContent=text(value);tr.appendChild(cell);
    });
    [area(room.area),money(discounted(room.price)),total(discounted(room.totalPrice))].forEach(function(value){
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
    var available=Number(room.saleStatus)===2;
    var article=document.createElement('article');article.className='floor-room '+(available?'available':'sold')+(matched?'':' filtered-out');article.tabIndex=0;
    article.setAttribute('aria-disabled',matched?'false':'true');
    if(!matched){
      article.setAttribute('data-room-status',available?'available':'sold');
      article.setAttribute('aria-label',text(room.roomName)+'，筛选外');
      article.textContent='—';return article;
    }
    var price=discounted(room.price);var group=priceGroups.get(priceKey(room));
    article.setAttribute('data-price',price===null?'—':String(price));article.setAttribute('data-price-value',price===null?'':String(price));article.setAttribute('data-total-price',discounted(room.totalPrice)===null?'—':String(discounted(room.totalPrice)));article.setAttribute('data-original-price',text(room.price));
    article.setAttribute('data-price-group',priceKey(room));article.setAttribute('data-room-status',available?'available':'sold');
    article.setAttribute('aria-label',text(room.buildName)+text(room.unitName)+text(room.floor)+' '+text(room.roomName)+(available?'，可售':'，已售')+'，折后单价 '+money(price)+'，折后总价 '+total(discounted(room.totalPrice)));
    if(group)article.style.setProperty('--price-color',group);
    var priceLabel=document.createElement('span');priceLabel.className='floor-price';priceLabel.textContent=money(price);article.appendChild(priceLabel);
    var name=document.createElement('strong');name.textContent=text(room.roomName);article.appendChild(name);
    var meta=document.createElement('span');meta.className='floor-meta';meta.textContent=text(room.roomLayout)+' · '+area(room.area);article.appendChild(meta);
    var totalPrice=document.createElement('span');totalPrice.className='floor-total';totalPrice.textContent=total(discounted(room.totalPrice));article.appendChild(totalPrice);
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
  function detailBuildingLimit(){
    if(window.matchMedia('(max-width: 520px)').matches)return 3;
    if(window.matchMedia('(max-width: 760px)').matches)return 4;
    if(window.matchMedia('(max-width: 1100px)').matches)return 8;
    return 16;
  }
  var DETAIL_BUILDING_LIMIT=detailBuildingLimit();var floorSignature='';var floorRenderToken=0;
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
            return fragment;
          });
        });
        matrix.appendChild(row);
      });
      canvas.appendChild(matrix);stage.appendChild(canvas);stage.appendChild(status);
    }
    floorResults.appendChild(stage);if(backButton)floorResults.appendChild(backButton);
    var fullscreenAction=document.createElement('button');fullscreenAction.type='button';fullscreenAction.className='floor-fullscreen-floating';fullscreenAction.setAttribute('data-role','floor-fullscreen');fullscreenAction.setAttribute('aria-pressed',floorFullscreen?'true':'false');fullscreenAction.textContent=floorFullscreen?'退出全屏':'全屏地图';floorResults.appendChild(fullscreenAction);
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
      var frameStart=performance.now();var fragment=document.createDocumentFragment();
      while(cursor<jobs.length&&performance.now()-frameStart<10){var result=jobs[cursor++]();if(fragment)fragment.appendChild(result)}
      if(cursor>=jobs.length&&canvas.firstChild)canvas.firstChild.appendChild(fragment);
      var percent=jobs.length?Math.round(cursor/jobs.length*100):100;status.textContent='楼层分布渲染中 '+percent+'%';
      if(cursor<jobs.length)requestAnimationFrame(renderFloorBatch);else finishRender();
    }
    if(jobs.length)requestAnimationFrame(renderFloorBatch);else finishRender();
  }
  var viewState={scale:1,x:0,y:0};
  function clampScale(value){return Math.min(2.2,Math.max(.18,value))}
  function fitView(canvas){
    if(!canvas)return;var stage=canvas.closest('.floor-stage');if(!stage)return;
    var insets=floorViewportInsets(stage);var width=Math.max(1,canvas.offsetWidth);var height=Math.max(1,canvas.offsetHeight);var availableHeight=Math.max(1,stage.clientHeight-insets.top-insets.bottom);
    var fitAll=Math.min((stage.clientWidth-32)/width,(availableHeight-32)/height,1);
    var fitHeight=Math.min((availableHeight-32)/height,1);
    viewState.scale=clampScale(fitAll>=.55?fitAll:fitHeight);
    viewState.x=(stage.clientWidth-width*viewState.scale)/2;viewState.y=insets.top+(availableHeight-height*viewState.scale)/2;
    applyViewState(canvas);queueClamp(canvas);var percent=Math.round(viewState.scale*100);
    if(zoomScale)zoomScale.textContent=percent+'%';if(zoomRange)zoomRange.value=String(percent);
  }
  function applyViewState(canvas){
    floorResults.style.setProperty('--floor-scale',viewState.scale.toFixed(3));
    floorResults.style.setProperty('--pan-x',viewState.x.toFixed(2)+'px');
    floorResults.style.setProperty('--pan-y',viewState.y.toFixed(2)+'px');
    if(canvas)canvas.style.transform='translate3d('+viewState.x.toFixed(2)+'px,'+viewState.y.toFixed(2)+'px,0) scale('+viewState.scale.toFixed(4)+')';
  }
  function floorViewportInsets(stage){
    var top=0,bottom=0;
    if(root.classList.contains('floor-fullscreen')){
      if(filtersOpen&&roomControls)top=Math.ceil(roomControls.getBoundingClientRect().height)+28;
      if(floorToolbar)bottom=Math.ceil(floorToolbar.getBoundingClientRect().height)+28;
    }
    return{top:top,bottom:bottom};
  }
  function clampPan(canvas){
    if(!canvas)return;var stage=canvas.closest('.floor-stage');if(!stage)return;
    var insets=floorViewportInsets(stage);var width=canvas.offsetWidth*viewState.scale;var height=canvas.offsetHeight*viewState.scale;var availableHeight=Math.max(1,stage.clientHeight-insets.top-insets.bottom);
    viewState.x=stage.clientWidth>=width?(stage.clientWidth-width)/2:Math.min(0,Math.max(stage.clientWidth-width,viewState.x));
    viewState.y=availableHeight>=height?insets.top+(availableHeight-height)/2:Math.min(insets.top,Math.max(stage.clientHeight-insets.bottom-height,viewState.y));
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
  function scheduleRender(){
    if(renderTimer)window.clearTimeout(renderTimer);
    renderTimer=window.setTimeout(function(){renderTimer=null;render()},180);
  }
  function render(){
    floorRenderToken++;
    root.classList.toggle('floor-view',view==='floor');
    refreshBuildingOptions();refreshUnitOptions();syncFilterControls();
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
    var discountLabel=discountRate===100?'':' · 折后 '+discountRate+'%';
    count.textContent=(view==='table'?'显示 '+Math.min(limit,filtered.length)+' / '+filtered.length+' 套房源':'楼层分布显示 '+filtered.length+' / '+visibleRooms.length+' 套匹配房源')+discountLabel;
    more.hidden=view!=='table'||limit>=filtered.length;setSummary(visibleRooms);
  }
  function syncBackButton(){if(backToOverview)backToOverview.hidden=!(view==='floor'&&(building!=='all'||unit!=='all'))}
  var zoomScale=root.querySelector('[data-role="zoom-scale"]');var zoomRange=root.querySelector('[data-role="zoom-range"]');var zoomIn=root.querySelector('[data-role="zoom-in"]');var zoomOut=root.querySelector('[data-role="zoom-out"]');var resetZoom=root.querySelector('[data-role="reset-zoom"]');var floorFullscreen=false;var floorFullscreenScroll={x:0,y:0};
  function floorFullscreenButtons(){return Array.prototype.slice.call(root.querySelectorAll('[data-role="floor-fullscreen"]'))}
  function syncFloorFullscreen(){floorFullscreenButtons().forEach(function(button){button.setAttribute('aria-pressed',floorFullscreen?'true':'false');button.textContent=floorFullscreen?'退出全屏':'全屏地图'})}
  function refitFloorView(){requestAnimationFrame(function(){requestAnimationFrame(function(){if(view!=='floor')return;var canvas=floorResults.querySelector('.floor-canvas');if(canvas)fitView(canvas)})})}
  function restoreFloorScroll(){requestAnimationFrame(function(){window.scrollTo(floorFullscreenScroll.x,floorFullscreenScroll.y);refitFloorView()})}
  function setFloorFullscreen(enabled,useNative){
    if(enabled===floorFullscreen)return;
    if(enabled){if(window.matchMedia('(min-width: 761px)').matches)filtersOpen=true;syncFilterControls();floorFullscreenScroll={x:window.scrollX,y:window.scrollY}}
    floorFullscreen=enabled;root.classList.toggle('floor-fullscreen',enabled);syncFloorFullscreen();
    if(enabled&&useNative&&root.requestFullscreen){try{var request=root.requestFullscreen();if(request&&request.catch)request.catch(function(){})}catch(error){}}
    if(!enabled&&document.fullscreenElement===root&&document.exitFullscreen){try{var exit=document.exitFullscreen();if(exit&&exit.catch)exit.catch(function(){})}catch(error){}}
    if(enabled)refitFloorView();else restoreFloorScroll();
  }
  function zoomFromControl(next){var stage=floorResults.querySelector('.floor-stage');if(!stage){setZoom(next);return}var rect=stage.getBoundingClientRect();setZoom(next,rect.width/2,rect.height/2)}
  if(zoomIn)zoomIn.addEventListener('click',function(){zoomFromControl((viewState.scale+.18)*100)});
  if(zoomOut)zoomOut.addEventListener('click',function(){zoomFromControl((viewState.scale-.18)*100)});
  if(resetZoom)resetZoom.addEventListener('click',function(){resetView(floorResults.querySelector('.floor-canvas'))});
  root.addEventListener('click',function(event){var button=event.target.closest('[data-role="floor-fullscreen"]');if(button)setFloorFullscreen(!floorFullscreen,true)});
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
  if(filterToggle)filterToggle.addEventListener('click',function(){filtersOpen=!filtersOpen;syncFilterControls();if(view==='floor')refitFloorView()});
  root.addEventListener('click',function(event){
    var opener=event.target.closest('[data-role="open-floor-filters"]');
    var closer=event.target.closest('[data-role="close-floor-filters"]');
    if(!opener&&!closer)return;
    event.preventDefault();filtersOpen=Boolean(opener);syncFilterControls();if(view==='floor')refitFloorView();
  });
  if(resetFiltersButton)resetFiltersButton.addEventListener('click',clearAllFilters);
  root.querySelectorAll('[data-role="room-filter"]').forEach(function(button){
    button.addEventListener('click',function(){
      root.querySelectorAll('[data-role="room-filter"]').forEach(function(item){item.setAttribute('aria-pressed','false')});
      button.setAttribute('aria-pressed','true');filter=button.getAttribute('data-filter');limit=100;render();
    });
  });
  search.addEventListener('input',function(){query=search.value;limit=100;scheduleRender()});
  certificateSelect.addEventListener('change',function(){certificate=certificateSelect.value;building='all';unit='all';limit=100;render()});
  buildingSelect.addEventListener('change',function(){building=buildingSelect.value;unit='all';limit=100;render()});
  unitSelect.addEventListener('change',function(){unit=unitSelect.value;limit=100;render()});
  [['price-min','priceMin'],['price-max','priceMax'],['total-min','totalMin'],['total-max','totalMax']].forEach(function(pair){
    var input=root.querySelector('[data-role="'+pair[0]+'"]');if(!input)return;
    input.addEventListener('input',function(){bounds[pair[1]]=input.value===''?null:Number(input.value);if(input.value!==''&&!isFinite(bounds[pair[1]]))bounds[pair[1]]=null;limit=100;scheduleRender()});
  });
  function setDiscount(value){
    var parsed=Math.round(Number(value));
    if(!isFinite(parsed))parsed=100;
    discountRate=Math.min(100,Math.max(1,parsed));syncDiscountControls();limit=100;render();
  }
  if(discountInput){
    discountInput.addEventListener('input',function(){
      if(discountInput.value==='')return;
      var parsed=Math.round(Number(discountInput.value));if(isFinite(parsed)&&parsed>=1&&parsed<=100)discountRate=parsed;limit=100;scheduleRender();
    });
    discountInput.addEventListener('change',function(){setDiscount(discountInput.value)});
  }
  root.querySelectorAll('[data-role="discount-preset"]').forEach(function(button){
    button.addEventListener('click',function(){setDiscount(button.getAttribute('data-discount'))});
  });
  more.addEventListener('click',function(){limit+=200;render()});
  function exportFilterSummary(){
    var values=[];
    if(certificate!=='all')values.push('预售证 '+certificateSelect.options[certificateSelect.selectedIndex].textContent);
    if(building!=='all')values.push(building+'栋');
    if(unit!=='all')values.push(unit+'单元');
    if(filter!=='all')values.push({available:'可售',sold:'已售',abnormal:'异常'}[filter]||filter);
    if(query.trim())values.push('“'+query.trim()+'”');
    if(bounds.priceMin!==null||bounds.priceMax!==null)values.push('单价 '+text(bounds.priceMin)+'-'+text(bounds.priceMax));
    if(bounds.totalMin!==null||bounds.totalMax!==null)values.push('总价 '+text(bounds.totalMin)+'-'+text(bounds.totalMax)+'万元');
    if(discountRate!==100)values.push('折后 '+discountRate+'%');
    return values.length?values.join(' · '):'全部房源';
  }
  function exportModel(){
    var allRooms=scopedRooms();var columns=[];var columnSeen=new Set();var floors=[];var floorSeen=new Set();var grouped=new Map();var maxRooms=1;
    allRooms.forEach(function(room){
      var key=matrixKey(room);var floor=text(room.floor);
      if(!columnSeen.has(key)){columnSeen.add(key);columns.push({key:key,building:text(room.building),unitName:text(room.unitName)});grouped.set(key,new Map())}
      if(!floorSeen.has(floor)){floorSeen.add(floor);floors.push(floor)}
      var floorMap=grouped.get(key);if(!floorMap.has(floor))floorMap.set(floor,[]);
      var values=floorMap.get(floor);values.push(room);maxRooms=Math.max(maxRooms,values.length);
    });
    columns.sort(function(left,right){return naturalCompare(left.building,right.building)||naturalCompare(left.unitName,right.unitName)});
    floors.sort(function(left,right){var ln=floorNumber(left);var rn=floorNumber(right);if(isFinite(ln)&&isFinite(rn)&&ln!==rn)return rn-ln;if(isFinite(ln))return -1;if(isFinite(rn))return 1;return naturalCompare(left,right)});
    grouped.forEach(function(floorMap){floorMap.forEach(function(values){values.sort(function(left,right){return naturalCompare(left.roomName,right.roomName)})})});
    return {rooms:allRooms,columns:columns,floors:floors,grouped:grouped,maxRooms:maxRooms};
  }
  function truncateText(context,value,maxWidth){
    var output=String(value);
    if(context.measureText(output).width<=maxWidth)return output;
    while(output&&context.measureText(output+'…').width>maxWidth)output=output.slice(0,-1);
    return output+'…';
  }
  function roundRect(context,x,y,width,height,radius){
    context.beginPath();context.moveTo(x+radius,y);context.arcTo(x+width,y,x+width,y+height,radius);context.arcTo(x+width,y+height,x,y+height,radius);context.arcTo(x,y+height,x,y,radius);context.arcTo(x,y,x+width,y,radius);context.closePath();
  }
  function drawFloorCard(context,room,x,y,width,height){
    var matched=roomMatches(room);var available=Number(room.saleStatus)===2;var abnormal=Number(room.abnormalStatus)===1;
    var fill=matched?(available?'#eefaf4':'#fff3e9'):'#f0f1f3';var ink=matched?'#202224':'#797f88';var accent=matched?(available?'#1a7f4e':'#d97b31'):'#a7adba';
    context.fillStyle=fill;roundRect(context,x,y,width,height,8);context.fill();
    context.fillStyle=accent;roundRect(context,x,y,4,height,2);context.fill();
    context.strokeStyle=matched?'#00000014':'#0000000d';context.lineWidth=1;roundRect(context,x+.5,y+.5,width-1,height-1,8);context.stroke();
    context.fillStyle=ink;context.textBaseline='top';context.textAlign='left';
    context.font='800 15px -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif';
    context.fillText(truncateText(context,text(room.roomName),width-26),x+11,y+9);
    context.font='600 11px -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif';context.fillStyle=matched?'#606770':'#8d939d';
    context.fillText(truncateText(context,text(room.roomLayout)+' · '+area(room.area),width-22),x+11,y+30);
    if(matched){
      context.fillStyle='#0071e3';context.font='800 13px -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif';
      context.fillText(truncateText(context,money(discounted(room.price)),width-22),x+11,y+48);
      context.fillStyle='#4b5158';context.font='700 10px -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif';
      context.fillText(truncateText(context,total(discounted(room.totalPrice)),width-22),x+11,y+66);
      var label=available?'可售':'已售';context.font='800 9px sans-serif';var pillWidth=context.measureText(label).width+13;
      context.fillStyle=available?'#dff4e8':'#ffe4cd';roundRect(context,x+width-pillWidth-9,y+8,pillWidth,16,8);context.fill();
      context.fillStyle=available?'#12693f':'#a45513';context.textAlign='center';context.fillText(label,x+width-pillWidth/2-9,y+12);context.textAlign='left';
      if(abnormal){context.fillStyle='#b42318';context.font='800 9px sans-serif';context.fillText('异常',x+width-32,y+30)}
    }else{
      context.fillStyle='#797f88';context.font='750 14px sans-serif';context.textAlign='center';context.fillText('—',x+width/2,y+53);context.textAlign='left';
    }
  }
  function dataUrlBlob(href){
    var binary=atob(href.split(',')[1]);var bytes=new Uint8Array(binary.length);
    for(var index=0;index<binary.length;index++)bytes[index]=binary.charCodeAt(index);
    return new Blob([bytes],{type:'image/png'});
  }
  function canvasBlob(canvas){
    return new Promise(function(resolve,reject){
      if(canvas.toBlob){canvas.toBlob(function(blob){blob?resolve(blob):reject(new Error('浏览器未返回图片数据'))},'image/png');return}
      try{var href=canvas.toDataURL('image/png');if(href.indexOf('data:image/png')!==0)throw new Error('图片格式不受支持');resolve(dataUrlBlob(href))}catch(error){reject(error)}
    });
  }
  function exportFloorImage(){
    return new Promise(function(resolve,reject){
      if(view!=='floor'){reject(new Error('请先切换到楼层分布视图'));return}
      if(!scopedRooms().length){reject(new Error('当前筛选没有可导出的楼栋'));return}
      var busy=document.createElement('p');busy.className='floor-export-busy';busy.setAttribute('role','status');busy.textContent='正在生成图片…';floorResults.appendChild(busy);
      window.requestAnimationFrame(function(){
        try{
          var model=exportModel();var title=(document.querySelector('.hero h1')||{}).textContent||'楼盘楼层分布';var timeLabel=dataTime&&dataTime!=='—'?dataTime:'未记录';
          var discountLabel=discountRate===100?'原价':'折后 '+discountRate+'%';var cardWidth=126;var cardHeight=88;var cardGap=7;var columnGap=12;var axisWidth=46;var headerHeight=58;var rowHeight=98;var margin=28;
          var overview=model.columns.length>DETAIL_BUILDING_LIMIT&&building==='all'&&unit==='all';
          var contentWidth,contentHeight,columnWidth=model.maxRooms*cardWidth+(model.maxRooms-1)*cardGap;
          var overviewColumns,overviewRows,columnsPerBand,bands;
          if(overview){
            overviewColumns=Math.min(5,Math.max(2,Math.ceil(Math.sqrt(model.columns.length))));overviewRows=Math.ceil(model.columns.length/overviewColumns);
            contentWidth=margin*2+overviewColumns*236+(overviewColumns-1)*16;contentHeight=overviewRows*202+(overviewRows-1)*16;
          }else{
            columnsPerBand=Math.max(1,Math.min(12,Math.ceil(Math.sqrt(model.columns.length))));bands=Math.ceil(model.columns.length/columnsPerBand);
            contentWidth=margin*2+axisWidth+columnsPerBand*(columnWidth+columnGap)-columnGap;contentHeight=bands*(headerHeight+model.floors.length*rowHeight+26)+(bands-1)*30;
          }
          var width=Math.max(1080,Math.ceil(contentWidth));var height=Math.ceil(172+contentHeight+70);var scale=width<1600?2:1.5;
          var maxSide=8192,maxPixels=16000000;
          if(width*scale>maxSide||height*scale>maxSide)scale=Math.min(scale,maxSide/Math.max(width,height));
          if(width*height*scale*scale>maxPixels)scale=Math.min(scale,Math.sqrt(maxPixels/(width*height)));
          scale=Math.max(.35,scale);var canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(width*scale));canvas.height=Math.max(1,Math.round(height*scale));
          var context=canvas.getContext('2d');if(!context)throw new Error('当前浏览器不支持图片画布');
          context.scale(scale,scale);context.fillStyle='#f5f7fa';context.fillRect(0,0,width,height);context.textBaseline='top';context.textAlign='left';
          context.fillStyle='#0071e3';context.font='850 12px sans-serif';context.fillText('FLOOR MAP',margin,26);
          context.fillStyle='#1d1d1f';context.font='850 29px -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif';context.fillText(truncateText(context,title,width-360),margin,45);
          context.textAlign='right';context.fillStyle='#6e6e73';context.font='750 11px sans-serif';context.fillText('数据时间',width-margin,28);
          context.fillStyle='#1d1d1f';context.font='800 17px sans-serif';context.fillText(truncateText(context,timeLabel,330),width-margin,44);
          context.fillStyle='#0071e3';context.font='800 12px sans-serif';context.fillText(discountLabel,width-margin,68);
          context.textAlign='left';context.fillStyle='#fff';roundRect(context,margin,98,width-margin*2,34,12);context.fill();context.strokeStyle='#d8dade';context.stroke();
          context.fillStyle='#495057';context.font='700 12px sans-serif';context.fillText(truncateText(context,'筛选：'+exportFilterSummary(),width-margin*2-24),margin+12,109);
          var top=150;
          if(overview){
            model.columns.forEach(function(column,index){
              var columnIndex=index%overviewColumns;var rowIndex=Math.floor(index/overviewColumns);var x=margin+columnIndex*(236+16);var y=top+rowIndex*(202+16);var floorMap=model.grouped.get(column.key);var values=[];floorMap.forEach(function(floorRooms){values.push.apply(values,floorRooms)});
              var matched=values.filter(roomMatches);var available=values.filter(function(room){return Number(room.saleStatus)===2}).length;var prices=matched.map(function(room){return discounted(room.price)}).filter(function(value){return value!==null});var totals=matched.map(function(room){return discounted(room.totalPrice)}).filter(function(value){return value!==null});
              var average=function(values){return values.length?values.reduce(function(left,right){return left+right},0)/values.length:null};
              context.fillStyle='#fff';roundRect(context,x,y,236,202,15);context.fill();context.strokeStyle='#d8dade';context.stroke();
              context.fillStyle='#0071e3';context.font='800 11px sans-serif';context.fillText('BUILDING',x+16,y+15);
              context.fillStyle='#1d1d1f';context.font='850 21px sans-serif';context.fillText(truncateText(context,text(column.building),150),x+16,y+32);
              context.textAlign='right';context.fillText(truncateText(context,'单元 '+text(column.unitName),60),x+220,y+36);context.textAlign='left';
              context.fillStyle='#495057';context.font='700 12px sans-serif';context.fillText(floorMap.size+' 层 · '+values.length+' 套',x+16,y+72);context.fillText(matched.length+' 套匹配 · 可售 '+available,x+16,y+94);
              context.fillStyle='#0071e3';context.font='800 14px sans-serif';context.fillText(truncateText(context,'均单价 '+(average(prices)===null?'—':money(average(prices))),204),x+16,y+124);
              context.fillStyle='#4b5158';context.font='700 12px sans-serif';context.fillText(truncateText(context,'均总价 '+(average(totals)===null?'—':total(average(totals))),204),x+16,y+146);
              context.fillStyle='#e8f2ff';roundRect(context,x+16,y+170,204,7,4);context.fill();context.fillStyle='#0071e3';roundRect(context,x+16,y+170,Math.max(2,204*matched.length/Math.max(1,values.length)),7,4);context.fill();
            });
          }else{
            for(var band=0;band<bands;band++){
              var bandColumns=model.columns.slice(band*columnsPerBand,(band+1)*columnsPerBand);var bandTop=top+band*(headerHeight+model.floors.length*rowHeight+56);
              context.fillStyle='#6e6e73';context.font='750 11px sans-serif';context.fillText('楼层',margin,bandTop+21);
              bandColumns.forEach(function(column,columnIndex){
                var x=margin+axisWidth+columnIndex*(columnWidth+columnGap);
                context.fillStyle='#fff';roundRect(context,x,bandTop,columnWidth,headerHeight-14,12);context.fill();context.strokeStyle='#d8dade';context.stroke();
                context.fillStyle='#1d1d1f';context.font='850 16px sans-serif';context.fillText(truncateText(context,text(column.building),columnWidth/2),x+10,bandTop+7);
                context.fillStyle='#6e6e73';context.font='700 11px sans-serif';context.fillText(truncateText(context,'单元 '+text(column.unitName),columnWidth-20),x+10,bandTop+30);
              });
              model.floors.forEach(function(floor,rowIndex){
                var y=bandTop+headerHeight+rowIndex*rowHeight;context.fillStyle='#6e6e73';context.font='750 12px sans-serif';context.textAlign='right';context.fillText(truncateText(context,floor,axisWidth-10),margin+axisWidth-10,y+35);context.textAlign='left';
                bandColumns.forEach(function(column,columnIndex){
                  var x=margin+axisWidth+columnIndex*(columnWidth+columnGap);var values=model.grouped.get(column.key).get(floor);
                  if(values&&values.length){values.forEach(function(room,itemIndex){drawFloorCard(context,room,x+itemIndex*(cardWidth+cardGap),y,cardWidth,cardHeight)})}
                  else{context.strokeStyle='#c8ccd4';context.setLineDash([5,4]);roundRect(context,x,y,cardWidth,cardHeight,8);context.stroke();context.setLineDash([]);context.fillStyle='#a7adba';context.font='700 13px sans-serif';context.textAlign='center';context.fillText('—',x+cardWidth/2,y+36);context.textAlign='left'}
                });
              });
            }
          }
          context.fillStyle='#fff';roundRect(context,margin,height-58,width-margin*2,38,12);context.fill();context.strokeStyle='#d8dade';context.stroke();
          context.fillStyle='#495057';context.font='700 11px sans-serif';context.fillText('武汉一房一价 · 楼层分布',margin+14,height-46);
          context.textAlign='right';context.fillStyle='#1d1d1f';context.font='800 12px sans-serif';context.fillText('数据时间：'+timeLabel,width-margin-14,height-45);context.textAlign='left';
          canvasBlob(canvas).then(function(blob){downloadBlob(blob,'楼层分布-'+safeFilename(title)+'-'+safeFilename(timeLabel)+'.png');busy.remove();resolve()}).catch(function(error){busy.remove();reject(error)});
        }catch(error){busy.remove();reject(error)}
      });
    });
  }
  if(downloadFloorButton)downloadFloorButton.addEventListener('click',function(){
    downloadFloorButton.disabled=true;exportFloorImage().catch(function(error){
      var message=document.createElement('p');message.className='floor-export-busy';message.setAttribute('role','alert');message.textContent='图片生成失败：'+error.message;floorResults.appendChild(message);window.setTimeout(function(){message.remove()},5000);window.alert('图片生成失败：'+error.message)
    }).then(function(){downloadFloorButton.disabled=false});
  });
  function downloadBlob(blob,filename){
    var link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download=filename;document.body.appendChild(link);link.click();
    window.setTimeout(function(){URL.revokeObjectURL(link.href);link.remove()},1000);
  }
  function safeFilename(value){return String(value).replace(/[\\/:*?"|]/g,'-').replace(/\s+/g,'-').slice(0,48)}
  syncDiscountControls();syncFilterControls();
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
      (certificate.rooms||[]).forEach(function(room){
        var picked=Object.assign({},pickRoom(room),{certificateId:id,certificateName:name});
        picked.searchText=(name+' '+picked.searchText).toLowerCase();rooms.push(picked);
      });
    });
    setDataTime(data&&data.generatedAt);priceGroups=buildPricePalette(rooms);render();
  }).catch(function(error){
    tbody.replaceChildren(document.createElement('tr'));
    var cell=document.createElement('td');cell.colSpan=11;cell.className='loading';
    cell.textContent='一房一价明细载入失败：'+error.message;tbody.firstChild.appendChild(cell);
    floorRenderToken++;floorResults.replaceChildren();var floorError=document.createElement('p');floorError.className='loading';floorError.textContent='楼层分布载入失败：'+error.message;floorResults.appendChild(floorError);if(backToOverview)floorResults.appendChild(backToOverview);
    count.textContent='载入失败';more.hidden=true;
  });
})();
'''
