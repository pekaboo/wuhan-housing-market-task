from __future__ import annotations

import re
from typing import Any

from .render import esc, integer


def _area(value: Any) -> str:
    try:
        return f'{float(value):,.2f} ㎡'
    except (TypeError, ValueError):
        return esc(value if value not in (None, '') else '—')


def _build_rows(room_type: dict[str, Any]) -> str:
    builds = room_type.get('buildList')
    builds = builds if isinstance(builds, list) else []
    if not builds:
        return '<p class="room-type-note">暂无楼栋分布。</p>'
    rows = []
    for build in builds:
        if not isinstance(build, dict):
            continue
        rows.append(
            f'''<li>
              <strong>{esc(build.get('buildShortName') or build.get('buildName') or '—')}</strong>
              <span>{esc(build.get('unitName') or '—')} 单元 · {integer(build.get('floorTotal'))} 层 · {esc(build.get('buildType') or '—')}</span>
              <span>总 {integer(build.get('roomTotal'))} / 可售 {integer(build.get('availableRoomNum'))} / 已售 {integer(build.get('soldNum'))}</span>
            </li>'''
        )
    return f'<ul class="room-type-builds">{"".join(rows)}</ul>' if rows else '<p class="room-type-note">暂无楼栋分布。</p>'


def room_type_section(snapshot: dict[str, Any] | None, data_url: str | None) -> str:
    if not data_url:
        return '<section class="room-types empty" aria-label="户型图">未获取户型图数据</section>'

    room_types = snapshot.get('types') if isinstance(snapshot, dict) else None
    room_types = room_types if isinstance(room_types, list) else []
    cards: list[str] = []
    dialogs: list[str] = []

    for index, item in enumerate(room_types):
        if not isinstance(item, dict):
            continue
        room_type_id = esc(item.get('id') or index)
        layout = item.get('roomLayout') or item.get('name') or f'户型 {index + 1}'
        image = item.get('img')
        effect_image = item.get('effectImage')
        dialog_id = f'room-type-dialog-{index}'
        cards.append(
            f'''<button type="button" class="room-type-card" data-role="room-type-trigger" data-dialog-id="{dialog_id}" aria-haspopup="dialog">
              <span class="room-type-thumb">{'<img src="' + esc(image) + '" alt="' + esc(layout) + ' 户型图" loading="lazy" decoding="async">' if image else '<span>暂无图</span>'}</span>
              <span class="room-type-body">
                <strong>{esc(layout)}</strong>
                <span>{_area(item.get('area'))} · 可售 {integer(item.get('availableRoomNum'))} 套</span>
                <span>{esc(item.get('name') or '—')}</span>
                <em>点击查看大图</em>
              </span>
            </button>'''
        )
        dialogs.append(
            f'''<dialog id="{dialog_id}" class="room-type-dialog" data-role="room-type-dialog" aria-labelledby="{dialog_id}-title">
              <article>
                <header>
                  <div><p>户型图</p><h3 id="{dialog_id}-title">{esc(layout)}</h3></div>
                  <button type="button" data-role="room-type-close">关闭</button>
                </header>
                <div class="room-type-images">
                  {'<img src="' + esc(image) + '" alt="' + esc(layout) + ' 户型图大图">' if image else '<p class="room-type-note">该户型暂无图片。</p>'}
                  {('<img src="' + esc(effect_image) + '" alt="' + esc(layout) + ' 效果图">') if effect_image else ''}
                </div>
                <dl class="room-type-meta">
                  <div><dt>面积</dt><dd>{_area(item.get('area'))}</dd></div>
                  <div><dt>户型</dt><dd>{esc(layout)}</dd></div>
                  <div><dt>可售</dt><dd>{integer(item.get('availableRoomNum'))} 套</dd></div>
                  <div><dt>编号</dt><dd>{room_type_id}</dd></div>
                </dl>
                {_build_rows(item)}
              </article>
            </dialog>'''
        )

    status = (snapshot or {}).get('status')
    status_html = ''
    if status == 'error':
        status_html = f'<p class="one-price-error" role="alert">接口获取失败：{esc((snapshot or {}).get("message") or "未知错误")}</p>'
    elif not room_types:
        status_html = '<p class="room-type-note">该楼盘暂无户型图。</p>'

    markup = f'''<section class="room-types" data-room-type-url="{esc(data_url)}" aria-labelledby="room-types-title">
      <div class="one-price-head">
        <div><h2 id="room-types-title">户型图</h2><p>点击户型卡片查看大图、面积、可售数量与楼栋分布。</p></div>
        <a href="{esc(data_url)}" download>JSON 明细</a>
      </div>
      {status_html}
      <div class="room-type-grid">{''.join(cards) or '<p class="room-type-note">暂无户型图。</p>'}</div>
      {''.join(dialogs)}
    </section>'''
    return re.sub(r'[ \t]+\n', '\n', markup)


ROOM_TYPE_CSS = r'''.room-types{overflow:hidden;margin:0 0 24px;border:1px solid var(--line);border-radius:18px;background:var(--panel);box-shadow:var(--shadow)}.room-types.empty{display:grid;min-height:170px;place-items:center;color:var(--muted)}.room-type-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1px;padding:1px;background:var(--panel-soft)}.room-type-card{display:grid;grid-template-rows:auto 1fr;min-width:0;padding:0;border:0;background:var(--panel);color:var(--ink);font:inherit;text-align:left;cursor:pointer}.room-type-card:hover .room-type-body strong{color:var(--brand-ink)}.room-type-thumb{position:relative;display:grid;aspect-ratio:16/10;place-items:center;background:var(--panel-soft);overflow:hidden}.room-type-thumb img{width:100%;height:100%;object-fit:contain}.room-type-thumb>span{color:var(--muted);font-size:12px}.room-type-body{display:flex;flex-direction:column;gap:4px;min-width:0;padding:12px 13px}.room-type-body strong{font-size:14px;letter-spacing:-.03em}.room-type-body span{color:var(--muted);font-size:12px;overflow-wrap:anywhere}.room-type-body em{color:var(--brand-ink);font-size:11px;font-style:normal;font-weight:800}.room-type-note{margin:0;padding:14px 16px;color:var(--muted)}.room-type-dialog{width:min(920px,calc(100vw - 32px));max-width:100%;max-height:calc(100vh - 32px);padding:0;border:1px solid var(--line);border-radius:20px;background:var(--panel);color:var(--ink);box-shadow:0 30px 80px #00000038}.room-type-dialog::backdrop{background:#0b141ecc;backdrop-filter:blur(6px)}.room-type-dialog article{max-height:calc(100vh - 32px);overflow:auto}.room-type-dialog header{position:sticky;top:0;display:flex;justify-content:space-between;gap:14px;align-items:center;padding:15px 17px;border-bottom:1px solid var(--line);background:var(--panel)}.room-type-dialog header p{margin:0;color:var(--brand-ink);font-size:11px;font-weight:850;letter-spacing:.12em;text-transform:uppercase}.room-type-dialog h3{margin:2px 0 0;font-size:21px;letter-spacing:-.045em}.room-type-dialog header button{height:37px;padding:0 13px;border:0;border-radius:10px;background:var(--brand);color:#fff;font:inherit;font-size:12px;font-weight:800;cursor:pointer}@media (prefers-color-scheme:dark){.room-type-dialog header button{color:#07131d}}.room-type-images{display:grid;grid-template-columns:minmax(0,1fr);gap:10px;padding:15px 17px;background:var(--panel-soft)}.room-type-images img{display:block;width:100%;max-width:100%;height:auto;background:var(--panel)}.room-type-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;margin:0;background:var(--panel-soft);border-top:1px solid var(--line)}.room-type-meta div{min-width:0;padding:12px 14px;background:var(--panel)}.room-type-meta dt{color:var(--muted);font-size:11px}.room-type-meta dd{margin:2px 0 0;font-size:15px;font-weight:800;overflow-wrap:anywhere}.room-type-builds{display:grid;gap:9px;margin:0;padding:14px 17px 17px;list-style:none}.room-type-builds li{display:grid;gap:3px;padding:11px 12px;border:1px solid var(--line);border-radius:12px;background:var(--panel-soft)}.room-type-builds strong{font-size:13px}.room-type-builds span{color:var(--muted);font-size:12px}@media (max-width:760px){.room-type-grid{grid-template-columns:1fr}.room-type-meta{grid-template-columns:repeat(2,minmax(0,1fr))}.room-type-dialog{width:calc(100vw - 20px);max-height:calc(100vh - 20px)}}'''


ROOM_TYPE_JS = r'''(function(){
  'use strict';
  document.addEventListener('click',function(event){
    var trigger=event.target.closest('[data-role="room-type-trigger"]');
    if(trigger){
      var dialog=document.getElementById(trigger.getAttribute('data-dialog-id'));
      if(dialog && typeof dialog.showModal==='function')dialog.showModal();else if(dialog)dialog.setAttribute('open','');
      return;
    }
    var close=event.target.closest('[data-role="room-type-close"]');
    if(close){
      var dialog=close.closest('dialog');
      if(dialog)dialog.close();
    }
  });
  document.addEventListener('click',function(event){
    var dialog=event.target.closest('[data-role="room-type-dialog"]');
    if(dialog && event.target===dialog)dialog.close();
  });
})();
'''
