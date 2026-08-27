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
        <div class="floor-toolbar" aria-label="3D 楼栋视角控制" hidden>
          <button type="button" data-role="zoom-in">放大</button>
          <button type="button" data-role="zoom-out">缩小</button>
          <button type="button" data-role="reset-camera">复位视角</button>
          <div class="camera-presets" role="group" aria-label="预设视角">
            <button type="button" data-role="camera-preset" data-preset="front" aria-pressed="false">正视</button>
            <button type="button" data-role="camera-preset" data-preset="iso" aria-pressed="true">轴测</button>
            <button type="button" data-role="camera-preset" data-preset="top" aria-pressed="false">俯视</button>
          </div>
          <label class="camera-zoom-control">缩放<input data-role="camera-zoom" type="range" min="45" max="220" step="1" value="100" aria-label="3D 楼栋缩放比例"></label>
          <button type="button" data-role="all-buildings">全部楼栋</button>
          <span>3D 楼栋 · <output data-role="camera-scale">100%</output></span>
        </div>
        <div class="numeric-filters" aria-label="价格筛选">
          <label>单价下限<input data-role="price-min" type="number" min="0" step="100" inputmode="numeric" placeholder="元/㎡"></label>
          <label>单价上限<input data-role="price-max" type="number" min="0" step="100" inputmode="numeric" placeholder="元/㎡"></label>
          <label>总价下限<input data-role="total-min" type="number" min="0" step="10000" inputmode="numeric" placeholder="万元"></label>
          <label>总价上限<input data-role="total-max" type="number" min="0" step="10000" inputmode="numeric" placeholder="万元"></label>
        </div>
      </div>
      <p class="floor-note">3D 楼栋按“楼栋 + 单元”作为一个立体单元渲染；楼层从上到下、同层房源横向排布。拖拽旋转 · 滚轮缩放 · 缩放滑杆 · 方向键微调，并提供正视 / 轴测 / 俯视预设。已售为红色，可售为绿色；右上角小方块表示单价，相同价格同色；筛选外房源保留原位置并变成灰色方块。</p>
      <div class="room-table-wrap">
        <table class="room-table">
          <caption class="sr-only">一房一价房源明细</caption>
          <thead><tr><th>楼栋</th><th>单元</th><th>楼层</th><th>房号</th><th>户型</th><th>面积</th><th>单价</th><th>总价</th><th>状态</th><th>标记</th><th>交付</th></tr></thead>
          <tbody data-role="room-results"><tr><td colspan="11" class="loading">正在载入房源明细…</td></tr></tbody>
        </table>
      </div>
      <div class="floor-results" data-role="floor-results" hidden aria-live="polite"><p class="loading">正在载入楼层分布…</p></div>
      <div class="room-foot"><p data-role="room-count" role="status" aria-live="polite">等待载入</p><button type="button" data-role="room-more" hidden>显示更多房源</button></div>
      <div class="certificate-list">{''.join(certificate_cards) or '<p class="one-price-note">暂无预售证摘要。</p>'}</div>
    </section>'''



ONE_PRICE_CSS = r'''.one-price{overflow:hidden;margin:0 0 24px;border:1px solid var(--line);border-radius:18px;background:var(--panel);box-shadow:var(--shadow)}.one-price.empty{display:grid;min-height:170px;place-items:center;color:var(--muted)}.one-price-head{display:flex;justify-content:space-between;gap:16px;align-items:start;padding:18px 18px 14px}.one-price-head h2{margin:0}.one-price-head p{margin:4px 0 0;color:var(--muted);font-size:13px}.one-price-head a{display:inline-flex;min-height:36px;align-items:center;padding:0 12px;border-radius:10px;background:var(--panel-soft);color:var(--brand-ink);font-size:12px;font-weight:800;text-decoration:none;white-space:nowrap}.one-price-error{margin:0;padding:13px 18px;background:color-mix(in srgb,#b42318 10%,var(--panel));color:#b42318;font-weight:750}.one-price-note{margin:0;padding:14px 18px;color:var(--muted)}.one-price-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:1px;background:var(--panel-soft)}.one-price-metric{min-width:0;padding:13px;background:var(--panel)}.one-price-metric span{display:block;color:var(--muted);font-size:11px}.one-price-metric strong{display:block;margin-top:2px;font-size:21px;letter-spacing:-.045em}.one-price-metric.available strong{color:#137a4b}.one-price-metric.sold strong{color:#a35613}.one-price-metric.abnormal strong{color:#a33815}@media (prefers-color-scheme:dark){.one-price-metric.available strong{color:#75d9a5}.one-price-metric.sold strong{color:#f0b76a}.one-price-metric.abnormal strong{color:#ff9d7a}.one-price-error{background:#43110c;color:#ffab94}}.room-controls{display:grid;grid-template-columns:auto minmax(170px,220px) minmax(140px,180px) minmax(130px,170px) minmax(220px,1fr);gap:9px;padding:13px 14px;border-top:1px solid var(--line);background:var(--panel-soft)}.room-controls label,.room-filters,.numeric-filters{display:flex;min-width:0;align-items:center;gap:7px;color:var(--muted);font-size:12px;font-weight:750}.room-controls select,.room-controls input{min-width:0;flex:1;height:38px;padding:0 10px;border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--ink);font:inherit;font-size:13px;outline:none}.room-controls input:focus-visible,.room-controls select:focus-visible{border-color:var(--focus)}.view-switch{display:flex;gap:5px}.view-switch button,.room-filters button{height:38px;padding:0 11px;border:0;border-radius:10px;background:var(--panel);color:var(--muted);font:inherit;font-size:12px;font-weight:800;cursor:pointer}.view-switch button[aria-pressed=true],.room-filters button[aria-pressed=true]{background:var(--brand);color:#fff}.room-filters,.numeric-filters{grid-column:1/-1;flex-wrap:wrap}.room-filters{justify-content:flex-start;overflow:visible}.numeric-filters{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:7px}.numeric-filters label{flex-direction:column;align-items:stretch;gap:4px}.numeric-filters input{width:100%}.floor-note{margin:0;padding:9px 15px;border-top:1px solid var(--line);background:var(--panel);color:var(--muted);font-size:12px}.room-table-wrap{overflow-x:auto;border-top:1px solid var(--line)}.room-table{width:100%;min-width:1030px;border-collapse:collapse;font-size:13px}.room-table th,.room-table td{padding:11px 13px;border-top:1px solid var(--line);text-align:left;vertical-align:top;white-space:nowrap}.room-table thead th{position:sticky;top:0;background:var(--panel);color:var(--muted);font-size:11px}.room-table td.loading{color:var(--muted)}.status{display:inline-flex;height:24px;align-items:center;padding:0 8px;border-radius:999px;background:var(--panel-soft);color:var(--muted);font-size:11px;font-weight:800}.status.available{color:#137a4b;background:color-mix(in srgb,#137a4b 12%,var(--panel))}.status.sold{color:#a35613;background:color-mix(in srgb,#a35613 12%,var(--panel))}.status.abnormal{margin-left:5px;color:#a33815;background:color-mix(in srgb,#a33815 12%,var(--panel))}@media (prefers-color-scheme:dark){.status.available{color:#75d9a5}.status.sold{color:#f0b76a}.status.abnormal{color:#ff9d7a}}.floor-results{--camera-x:-23deg;--camera-y:33deg;--camera-scale:1;--spatial-panel:#0b141d;--panel:#0b141d;--panel-soft:#162532;--ink:#edf4fa;--muted:#a9bdcc;--line:#293d4f;--brand:#69b6e8;--brand-ink:#07131d;--focus:#a7f3d0;position:relative;padding:0;border-top:1px solid #293d4f;background:radial-gradient(1100px 460px at 50% -8%,#173d55,transparent 72%),linear-gradient(180deg,#0a141e,#070f17);color:var(--ink)}
.floor-results>.loading{margin:0;padding:14px;color:var(--muted)}
.floor-toolbar{position:sticky;top:0;z-index:30;display:flex;flex-wrap:wrap;align-items:center;gap:6px;padding:10px 14px;border-bottom:1px solid color-mix(in srgb,var(--ink) 14%,var(--line));background:color-mix(in srgb,var(--panel) 84%,transparent);backdrop-filter:blur(14px) saturate(1.2)}
.floor-toolbar button{height:32px;padding:0 10px;border:0;border-radius:8px;background:var(--panel-soft);color:var(--ink);font:inherit;font-size:11px;font-weight:850;cursor:pointer;transition:background .18s ease,color .18s ease,box-shadow .18s ease}
.floor-toolbar button:hover,.floor-toolbar button[aria-pressed=true]{background:var(--brand);color:#fff;box-shadow:0 7px 18px color-mix(in srgb,var(--brand) 30%,transparent)}
.floor-toolbar span{display:inline-flex;align-items:center;min-height:32px;padding:0 8px;border-radius:8px;background:var(--panel-soft);color:var(--muted);font-size:11px;font-weight:800}
.camera-presets{display:flex;gap:4px;padding:3px;border-radius:10px;background:color-mix(in srgb,var(--ink) 7%,transparent)}
.camera-zoom-control{display:flex;align-items:center;gap:7px;min-height:32px;padding:0 8px;border-radius:8px;background:var(--panel-soft);color:var(--muted);font-size:11px;font-weight:800}
.camera-zoom-control input{width:120px;accent-color:var(--brand)}
.floor-stage{position:relative;z-index:1;overflow:auto;padding:310px clamp(16px,4vw,64px) 160px;perspective:1600px;perspective-origin:50% 34%;cursor:grab;touch-action:pan-y;overscroll-behavior:contain;background:radial-gradient(900px 420px at 50% 12%,#1b4d6d59,transparent 72%),radial-gradient(1200px 520px at 50% 96%,#14465f47,transparent 76%),linear-gradient(180deg,transparent,#02081073);box-shadow:inset 0 1px 0 color-mix(in srgb,#fff 32%,transparent),inset 0 -1px 0 color-mix(in srgb,var(--ink) 12%,transparent)}
.floor-stage:active{cursor:grabbing}
.floor-stage:focus-visible{outline:3px solid var(--focus);outline-offset:-3px}
.floor-camera{will-change:transform}
.floor-matrix{display:block;width:100%;min-width:0;margin:auto}
.building-world{display:flex;flex-wrap:wrap;width:100%;align-items:end;transform-style:flat}
.building-world.detail-grid{gap:clamp(30px,4vw,76px)}
.building-world.overview-grid{justify-content:center;gap:18px 20px}
.building-3d{position:relative;min-width:190px;transform:rotateX(calc(var(--camera-x) + 0deg)) rotateY(calc(var(--camera-y) + 0deg)) scale3d(var(--camera-scale),var(--camera-scale),var(--camera-scale));transform-origin:50% 100%;transform-style:preserve-3d;transition:transform .2s cubic-bezier(.2,.75,.25,1)}
.building-3d::before{content:"";position:absolute;z-index:-2;top:7px;right:-25px;width:25px;height:calc(100% - 32px);pointer-events:none;border-right:1px solid color-mix(in srgb,var(--ink) 20%,var(--line));background:linear-gradient(90deg,color-mix(in srgb,var(--ink) 17%,var(--panel)),color-mix(in srgb,var(--ink) 8%,var(--panel)));transform:rotateY(68deg);transform-origin:left}
.building-3d::after{content:"";position:absolute;z-index:-2;top:-13px;left:-12px;width:calc(100% + 37px);height:20px;pointer-events:none;border:1px solid color-mix(in srgb,var(--ink) 17%,var(--line));background:linear-gradient(135deg,color-mix(in srgb,#fff 42%,var(--panel)),color-mix(in srgb,var(--brand) 20%,var(--panel)));transform:rotateX(74deg);transform-origin:bottom}
.building-overview{position:relative;width:88px;min-width:88px;padding:0;border:0;background:transparent;color:var(--ink);font:inherit;cursor:pointer;transform-style:preserve-3d}
.building-overview:hover .overview-face,.building-overview:active .overview-face{border-color:color-mix(in srgb,var(--brand) 45%,var(--line));background-position:50% 40%,0 0,0 0}
.building-overview:hover .overview-body,.building-overview:active .overview-body{transform:translateZ(5px)}
.building-overview .building-head{position:relative;left:auto;top:auto;width:auto;transform:translateZ(15px)}
.overview-body{position:relative;display:block;height:calc(var(--floors,1)*10px + 32px);transform-style:preserve-3d;transition:transform .18s ease-out}
.overview-body::before{content:"";position:absolute;z-index:-1;top:5px;right:-18px;width:18px;height:calc(100% - 10px);pointer-events:none;background:linear-gradient(90deg,color-mix(in srgb,var(--ink) 25%,var(--panel)),color-mix(in srgb,var(--ink) 10%,var(--panel)));transform:rotateY(68deg);transform-origin:left}
.overview-body::after{content:"";position:absolute;z-index:-1;top:-11px;left:-6px;width:calc(100% + 24px);height:16px;pointer-events:none;border:1px solid color-mix(in srgb,var(--ink) 16%,var(--line));background:linear-gradient(135deg,color-mix(in srgb,#fff 42%,var(--panel)),color-mix(in srgb,var(--brand) 22%,var(--panel)));transform:rotateX(74deg);transform-origin:bottom}
.overview-face{position:absolute;inset:0;border:1px solid color-mix(in srgb,var(--ink) 28%,var(--line));border-radius:4px;background:linear-gradient(to top,color-mix(in srgb,#17935d calc(var(--match-ratio,1)*58%),transparent) 0,transparent calc(var(--match-ratio,1)*100%)),repeating-linear-gradient(to top,color-mix(in srgb,var(--ink) 18%,transparent) 0 1px,transparent 1px 10px),linear-gradient(155deg,color-mix(in srgb,var(--brand) 33%,var(--panel)),color-mix(in srgb,var(--ink) 16%,var(--panel)));box-shadow:0 23px 38px #0b172429,0 2px 0 color-mix(in srgb,#fff 22%,transparent) inset;transition:background-position .2s ease,border-color .2s ease}
.overview-scale{position:absolute;bottom:-23px;left:50%;white-space:nowrap;color:var(--muted);font-size:9px;font-weight:850;transform:translateX(-50%) translateZ(3px)}
.building-overview:focus-visible{outline:3px solid var(--focus);outline-offset:6px}
.building-head{position:absolute;left:-14px;top:-34px;width:calc(100% + 28px);display:grid;gap:2px;padding:6px 8px;border:1px solid color-mix(in srgb,var(--ink) 13%,var(--line));border-radius:9px;background:color-mix(in srgb,var(--panel) 91%,transparent);box-shadow:0 16px 30px #0b17241c;text-align:center;transform:translateZ(17px);backdrop-filter:blur(8px) saturate(1.15)}
.building-head strong{color:var(--ink);font-size:13px}
.building-head span{color:var(--muted);font-size:10px}
.floor-slab{position:relative;display:grid;grid-template-columns:42px minmax(0,1fr);gap:5px;min-height:69px;margin-top:5px;padding:5px 6px;border:1px solid color-mix(in srgb,var(--ink) 23%,var(--line));border-radius:6px;background:linear-gradient(180deg,color-mix(in srgb,#fff 14%,var(--panel)),color-mix(in srgb,var(--ink) 5%,var(--panel)));transform:translateZ(calc(var(--level,0)*17px));transform-style:preserve-3d;box-shadow:0 9px 18px #0b172418,0 1px 0 color-mix(in srgb,#fff 20%,transparent) inset}
.floor-slab::before{content:"";position:absolute;z-index:-1;pointer-events:none;left:-5px;top:-2px;width:calc(100% + 10px);height:16px;border-top:1px solid color-mix(in srgb,var(--ink) 26%,var(--line));background:linear-gradient(90deg,color-mix(in srgb,var(--brand) 30%,var(--panel)),color-mix(in srgb,var(--ink) 12%,var(--panel)));transform:rotateX(76deg);transform-origin:top}
.floor-slab::after{content:"";position:absolute;z-index:-1;pointer-events:none;top:0;right:-17px;width:17px;height:100%;background:linear-gradient(90deg,color-mix(in srgb,var(--ink) 21%,var(--panel)),color-mix(in srgb,var(--ink) 8%,var(--panel)));transform:rotateY(76deg);transform-origin:right}
.floor-label{display:flex;min-height:57px;align-items:center;justify-content:center;border-radius:4px;background:linear-gradient(180deg,color-mix(in srgb,var(--ink) 9%,transparent),color-mix(in srgb,var(--ink) 4%,transparent));color:var(--muted);font-size:11px;font-weight:900}
.room-cells{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(112px,1fr);gap:8px}
.room-3d{position:relative;min-width:0;min-height:57px;padding:6px 7px 6px 9px;overflow:visible;border:1px solid color-mix(in srgb,var(--ink) 18%,transparent);border-radius:4px;background:linear-gradient(155deg,color-mix(in srgb,var(--price-color,var(--brand)) 25%,var(--panel)),color-mix(in srgb,var(--price-color,var(--brand)) 11%,var(--panel)));color:var(--ink);box-shadow:inset 0 -4px 0 color-mix(in srgb,var(--status-color,var(--brand)) 72%,#000),0 6px 13px #0b172417;transform:translateZ(3px);transform-style:preserve-3d;transition:transform .18s cubic-bezier(.2,.75,.25,1),box-shadow .18s ease,border-color .18s ease}
.room-3d::before{content:"";position:absolute;z-index:-1;top:5px;right:-9px;width:9px;height:calc(100% - 10px);pointer-events:none;background:linear-gradient(90deg,color-mix(in srgb,var(--price-color,var(--brand)) 32%,var(--panel)),color-mix(in srgb,var(--ink) 12%,var(--panel)));transform:rotateY(68deg);transform-origin:left}
.room-3d::after{content:"";position:absolute;z-index:-1;top:-7px;left:5px;width:calc(100% - 10px);height:7px;pointer-events:none;background:linear-gradient(180deg,color-mix(in srgb,#fff 35%,var(--panel)),color-mix(in srgb,var(--price-color,var(--brand)) 20%,var(--panel)));transform:rotateX(74deg);transform-origin:bottom}
.room-3d.available{--status-color:#17935d}
.room-3d.sold{--status-color:#c62828;background:linear-gradient(155deg,color-mix(in srgb,#c62828 22%,var(--panel)),color-mix(in srgb,#c62828 11%,var(--panel)))}
.room-3d:hover,.room-3d:focus-visible{z-index:6;border-color:color-mix(in srgb,var(--brand) 38%,var(--line));transform:translateZ(16px);box-shadow:inset 0 -4px 0 color-mix(in srgb,var(--status-color,var(--brand)) 72%,#000),0 16px 26px #0b172428}
.room-3d:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.room-3d.filtered-out,.floor-missing{--price-color:#7b8794;--status-color:#7b8794;min-height:57px;padding:0;border:1px solid #7b87945c;border-radius:4px;background:#7b879426;color:#7b8794;font-size:11px;font-weight:850;text-align:center}
.room-3d.filtered-out>*{display:none}
.room-3d.filtered-out::before,.room-3d.filtered-out::after{display:none}
.floor-missing{display:flex;align-items:center;justify-content:center}
.floor-price{display:block;color:var(--muted);font-size:9px;font-weight:850;line-height:1.2}
.room-3d strong{display:block;margin-top:1px;font-size:12px;line-height:1.2;letter-spacing:-.01em;overflow-wrap:anywhere}
.floor-meta{display:block;margin-top:2px;color:var(--muted);font-size:9px;font-weight:750;line-height:1.2;overflow-wrap:anywhere}
.floor-total{display:block;margin-top:2px;color:var(--muted);font-size:9px;font-weight:750}
.room-3d .status{margin-top:3px;height:17px;padding:0 5px;font-size:8px}
.room-3d .status+.status{margin-left:3px}
.price-chip{position:absolute;top:5px;right:5px;width:11px;height:11px;border:2px solid color-mix(in srgb,var(--panel) 88%,transparent);border-radius:3px;background:var(--price-color,var(--brand));box-shadow:0 1px 4px #00000038}
.building-ground{position:relative;height:17px;margin-top:7px;border-radius:6px;background:linear-gradient(90deg,color-mix(in srgb,var(--brand) 40%,var(--panel)),color-mix(in srgb,var(--ink) 18%,var(--panel)));box-shadow:0 19px 32px #0b172433;transform:translateZ(-4px) rotateX(14deg)}
.building-ground::before{content:"";position:absolute;z-index:-1;left:-16px;top:-9px;width:calc(100% + 32px);height:29px;border-radius:12px;background:radial-gradient(50% 50% at 50% 50%,color-mix(in srgb,var(--ink) 17%,transparent),transparent 72%);transform:rotateX(74deg);transform-origin:top;pointer-events:none}
.building-ground::after{content:"";position:absolute;top:16px;left:5%;width:90%;height:42px;border-radius:5px;background:linear-gradient(180deg,color-mix(in srgb,var(--brand) 18%,transparent),transparent 76%);transform:skewX(-10deg);opacity:.42;pointer-events:none}
.room-foot{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 15px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}.room-foot p{margin:0}.room-foot button{height:36px;padding:0 13px;border:0;border-radius:10px;background:var(--brand);color:#fff;font:inherit;font-size:12px;font-weight:800;cursor:pointer}@media (prefers-color-scheme:dark){.floor-results{background:radial-gradient(1100px 460px at 50% -8%,#123248,transparent 72%),linear-gradient(180deg,#08111a,#050b12)}.floor-stage{background:radial-gradient(850px 400px at 50% 10%,#12324842,transparent 72%),radial-gradient(1150px 500px at 50% 96%,#0d253738,transparent 76%);box-shadow:inset 0 1px 0 #ffffff1f,inset 0 -1px 0 #00000042}.floor-toolbar{background:#08111ae8;border-bottom-color:#26394a}.building-3d::after,.overview-body::after{background:linear-gradient(135deg,#405b6d,#182c3b)}.overview-face{box-shadow:0 24px 42px #00000052,0 2px 0 #ffffff14 inset}.building-ground::after{opacity:.28}.room-foot button{color:#07131d}.view-switch button[aria-pressed=true],.room-filters button[aria-pressed=true]{color:#07131d}}.certificate-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1px;padding:1px;background:var(--panel-soft);border-top:1px solid var(--line)}.certificate-card{min-width:0;padding:14px;background:var(--panel)}.certificate-card h3{margin:0 0 8px;font-size:13px;line-height:1.45;overflow-wrap:anywhere}.certificate-card dl{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:0}.certificate-card div{min-width:0}.certificate-card dt{color:var(--muted);font-size:10px}.certificate-card dd{margin:2px 0 0;font-size:14px;font-weight:800}@media (max-width:760px){.one-price-head{align-items:start;flex-direction:column}.one-price-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.one-price-metric:last-child{grid-column:1/-1}.room-controls{grid-template-columns:1fr}.floor-toolbar{padding:9px 12px}.camera-presets{flex:1 1 100%;justify-content:space-between}.camera-zoom-control{flex:1 1 100%;justify-content:space-between}.camera-zoom-control input{width:100%}.view-switch{display:grid;grid-template-columns:1fr 1fr}.view-switch button,.room-filters button{min-height:44px}.room-controls select,.room-controls input{min-height:44px}.numeric-filters{grid-template-columns:1fr 1fr}.room-filters{justify-content:flex-start}.room-foot{align-items:stretch;flex-direction:column}.room-foot button{width:100%}.certificate-card dl{grid-template-columns:repeat(2,1fr)}}@media (max-width:430px){.numeric-filters{grid-template-columns:1fr}}@media (prefers-reduced-motion:reduce){.one-price *,.one-price *::before,.one-price *::after{transition-duration:.01ms!important;animation-duration:.01ms!important}}'''


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
  function roomCell(room){
    var available=Number(room.saleStatus)===2;var group=priceGroups.get(priceKey(room));
    var article=document.createElement('article');article.className='room-3d'+(available?' available':' sold');article.tabIndex=0;article.classList.toggle('filtered-out',!roomMatches(room));article.setAttribute('aria-disabled',roomMatches(room)?'false':'true');
    article.setAttribute('data-price',text(room.price));article.setAttribute('data-price-value',numericValue(room.price)===null?'':String(numericValue(room.price)));article.setAttribute('data-total-price',text(room.totalPrice));
    article.setAttribute('data-price-group',priceKey(room));article.setAttribute('data-room-status',available?'available':'sold');
    if(group)article.style.setProperty('--price-color',group);
    article.setAttribute('aria-label',text(room.buildName)+text(room.unitName)+text(room.floor)+' '+text(room.roomName)+(available?'，可售':'，已售')+'，单价 '+money(room.price)+'，总价 '+total(room.totalPrice));
    var price=document.createElement('span');price.className='floor-price';price.textContent=money(room.price);article.appendChild(price);
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
  var DETAIL_BUILDING_LIMIT=16;
  function focusBuilding(column){building=text(column.building);unit=text(column.unitName);limit=100;render()}
  function renderFloorView(allRooms){
    floorResults.replaceChildren();
    if(!allRooms.length){var empty=document.createElement('p');empty.className='loading';empty.textContent='没有可展示的楼栋数据';floorResults.appendChild(empty);return;}
    var columns=[];var columnSeen=new Set();var floors=[];var floorSeen=new Set();var floorRooms=new Map();
    allRooms.forEach(function(room){
      var key=matrixKey(room);var floor=text(room.floor);
      if(!columnSeen.has(key)){
        columnSeen.add(key);columns.push({key:key,building:text(room.buildName),unitName:text(room.unitName)});floorRooms.set(key,new Map());
      }
      if(!floorSeen.has(floor)){floorSeen.add(floor);floors.push(floor);}
      var rooms=floorRooms.get(key);if(!rooms.has(floor))rooms.set(floor,[]);
      rooms.get(floor).push(room);
    });
    columns.sort(function(left,right){return naturalCompare(left.building,right.building)||naturalCompare(left.unitName,right.unitName)});
    floors.sort(function(left,right){var ln=floorNumber(left);var rn=floorNumber(right);if(isFinite(ln)&&isFinite(rn)&&ln!==rn)return rn-ln;if(isFinite(ln))return -1;if(isFinite(rn))return 1;return naturalCompare(left,right)});
    var scroll=document.createElement('div');scroll.className='floor-stage floor-scroll';scroll.tabIndex=0;scroll.setAttribute('role','application');scroll.setAttribute('aria-label','3D 楼栋分布，可拖拽旋转和缩放');scroll.setAttribute('aria-keyshortcuts','方向键旋转，加号放大，减号缩小，0 复位，1 正视，2 轴测，3 俯视');
    var matrix=document.createElement('div');matrix.className='floor-matrix floor-camera';matrix.style.setProperty('--floor-columns',String(columns.length));
    matrix.setAttribute('aria-label','3D 楼栋；楼栋从左到右、楼层从上到下、同一楼层横向一排');
    var world=document.createElement('div');world.className='building-world '+(columns.length>DETAIL_BUILDING_LIMIT?'overview-grid':'detail-grid');
    if(columns.length>DETAIL_BUILDING_LIMIT){
      columns.forEach(function(column){
        var values=[];floorRooms.get(column.key).forEach(function(floorRoomsForColumn){values.push.apply(values,floorRoomsForColumn)});
        var matched=values.filter(roomMatches).length;var ratio=values.length?matched/values.length:0;var columnFloors=floorRooms.get(column.key).size;
        var block=document.createElement('button');block.type='button';block.className='building-3d building-overview';block.style.setProperty('--floors',String(columnFloors));block.style.setProperty('--match-ratio',ratio.toFixed(3));
        block.setAttribute('aria-label','聚焦 '+text(column.building)+' 单元 '+text(column.unitName)+'，'+columnFloors+' 层，'+values.length+' 套房源');
        block.appendChild(floorHeader(column));
        var body=document.createElement('span');body.className='overview-body';
        var face=document.createElement('span');face.className='overview-face';face.setAttribute('aria-hidden','true');body.appendChild(face);
        var scale=document.createElement('span');scale.className='overview-scale';scale.textContent=columnFloors+'F · '+values.length+'套';body.appendChild(scale);
        block.appendChild(body);block.addEventListener('click',function(){focusBuilding(column)});world.appendChild(block);
      });
      matrix.appendChild(world);scroll.appendChild(matrix);floorResults.appendChild(scroll);return;
    }
    columns.forEach(function(column){
      var building=document.createElement('article');building.className='building-3d';building.appendChild(floorHeader(column));
      floors.forEach(function(floor,floorIndex){
        var slab=document.createElement('div');slab.className='floor-slab';slab.style.setProperty('--level',String(floors.length-floorIndex-1));
        var label=document.createElement('div');label.className='floor-label';label.textContent=floor;slab.appendChild(label);
        var cells=document.createElement('div');cells.className='room-cells';
        var values=floorRooms.get(column.key)&&floorRooms.get(column.key).get(floor);
        if(values&&values.length){
          values.sort(function(left,right){return naturalCompare(left.roomName,right.roomName)}).forEach(function(room){cells.appendChild(roomCell(room))});
        }else{
          var missing=document.createElement('div');missing.className='floor-missing';missing.textContent='—';
          missing.setAttribute('aria-label',text(column.building)+' '+text(column.unitName)+' '+floor+' 无房源');cells.appendChild(missing);
        }
        slab.appendChild(cells);building.appendChild(slab);
      });
      var ground=document.createElement('div');ground.className='building-ground';ground.setAttribute('aria-hidden','true');building.appendChild(ground);
      world.appendChild(building);
    });
    matrix.appendChild(world);scroll.appendChild(matrix);floorResults.appendChild(scroll);
  }
  var camera={x:-23,y:33,scale:1};var cameraScale=root.querySelector('[data-role="camera-scale"]');var cameraZoom=root.querySelector('[data-role="camera-zoom"]');
  function clearCameraPreset(){root.querySelectorAll('[data-role="camera-preset"]').forEach(function(button){button.setAttribute('aria-pressed','false')})}
  function setCamera(){
    camera.scale=Math.min(2.2,Math.max(.45,camera.scale));
    camera.x=Math.min(4,Math.max(-72,camera.x));camera.y=Math.min(72,Math.max(-72,camera.y));
    floorResults.style.setProperty('--camera-x',camera.x.toFixed(2)+'deg');
    floorResults.style.setProperty('--camera-y',camera.y.toFixed(2)+'deg');
    floorResults.style.setProperty('--camera-scale',camera.scale.toFixed(3));
    var percent=Math.round(camera.scale*100);
    if(cameraScale)cameraScale.textContent=percent+'%';
    if(cameraZoom)cameraZoom.value=String(percent);
  }
  function setCameraPreset(preset){
    clearCameraPreset();
    var button=root.querySelector('[data-role="camera-preset"][data-preset="'+preset+'"]');
    if(button)button.setAttribute('aria-pressed','true');
    if(preset==='front')camera={x:0,y:0,scale:camera.scale};
    else if(preset==='top')camera={x:-72,y:0,scale:camera.scale};
    else camera={x:-23,y:33,scale:camera.scale};
    setCamera();
  }
  function setZoom(value){camera.scale=Number(value)/100;setCamera()}
  function moveCamera(deltaX,deltaY){clearCameraPreset();camera.y+=deltaX;camera.x+=deltaY;setCamera()}
  function render(){
    refreshBuildingOptions();refreshUnitOptions();
    var visibleRooms=scopedRooms();var filtered=visibleRooms.filter(roomMatches);
    if(view==='table'){
      var fragment=document.createDocumentFragment();
      filtered.slice(0,limit).forEach(function(room){fragment.appendChild(row(room))});
      if(!filtered.length){var empty=document.createElement('tr');var cell=document.createElement('td');cell.colSpan=11;cell.className='loading';cell.textContent='没有符合筛选条件的房源';empty.appendChild(cell);fragment.appendChild(empty);}
      tbody.replaceChildren(fragment);floorResults.replaceChildren();
    }else{renderFloorView(visibleRooms);setCamera();}
    tableWrap.hidden=view!=='table';floorResults.hidden=view==='table';if(floorToolbar)floorToolbar.hidden=view!=='floor';
    count.textContent=view==='table'?'显示 '+Math.min(limit,filtered.length)+' / '+filtered.length+' 套房源':'3D 楼栋显示 '+filtered.length+' / '+visibleRooms.length+' 套匹配房源';
    more.hidden=view!=='table'||limit>=filtered.length;setSummary(visibleRooms);
  }
  var zoomIn=root.querySelector('[data-role="zoom-in"]');var zoomOut=root.querySelector('[data-role="zoom-out"]');var resetCamera=root.querySelector('[data-role="reset-camera"]');
  if(zoomIn)zoomIn.addEventListener('click',function(){clearCameraPreset();camera.scale+=.18;setCamera()});
  if(zoomOut)zoomOut.addEventListener('click',function(){clearCameraPreset();camera.scale-=.18;setCamera()});
  if(resetCamera)resetCamera.addEventListener('click',function(){setCameraPreset('iso');camera.scale=1;setCamera()});
  root.querySelectorAll('[data-role="camera-preset"]').forEach(function(button){button.addEventListener('click',function(){setCameraPreset(button.getAttribute('data-preset'))})});
  if(cameraZoom)cameraZoom.addEventListener('input',function(){clearCameraPreset();setZoom(cameraZoom.value)});
  var allBuildings=root.querySelector('[data-role="all-buildings"]');
  if(allBuildings)allBuildings.addEventListener('click',function(){building='all';unit='all';limit=100;render()});
  floorResults.addEventListener('wheel',function(event){
    if(view==='table'||!event.target.closest('.floor-stage'))return;
    event.preventDefault();clearCameraPreset();camera.scale-=event.deltaY*.0015;setCamera();
  },{passive:false});
  var drag=null;
  floorResults.addEventListener('pointerdown',function(event){
    if(view==='table'||!event.target.closest('.floor-stage'))return;if(event.target.closest('.building-overview'))return;
    drag={x:event.clientX,y:event.clientY,cameraX:camera.x,cameraY:camera.y};floorResults.setPointerCapture(event.pointerId);
  });
  floorResults.addEventListener('pointermove',function(event){
    if(!drag)return;moveCamera((event.clientX-drag.x)*.38,(event.clientY-drag.y)*.32);
  });
  ['pointerup','pointercancel'].forEach(function(type){floorResults.addEventListener(type,function(){drag=null})});
  floorResults.addEventListener('keydown',function(event){
    if(view==='table')return;
    var step=event.shiftKey?12:5;var key=event.key;
    if(key==='ArrowLeft'){event.preventDefault();moveCamera(-step,0)}
    else if(key==='ArrowRight'){event.preventDefault();moveCamera(step,0)}
    else if(key==='ArrowUp'){event.preventDefault();moveCamera(0,-step)}
    else if(key==='ArrowDown'){event.preventDefault();moveCamera(0,step)}
    else if(key==='+'||key==='='){event.preventDefault();clearCameraPreset();camera.scale+=.08;setCamera()}
    else if(key==='-'||key==='_'){event.preventDefault();clearCameraPreset();camera.scale-=.08;setCamera()}
    else if(key==='0'){event.preventDefault();setCameraPreset('iso');camera.scale=1;setCamera()}
    else if(key==='1')setCameraPreset('front');
    else if(key==='2')setCameraPreset('iso');
    else if(key==='3')setCameraPreset('top');
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
    floorResults.replaceChildren();var floorError=document.createElement('p');floorError.className='loading';floorError.textContent='楼层分布载入失败：'+error.message;floorResults.appendChild(floorError);
    count.textContent='载入失败';more.hidden=true;
  });
})();
'''
