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

    return f'''<section class="one-price" data-one-price-url="{esc(data_url)}" aria-labelledby="one-price-title">
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
        <div class="numeric-filters" aria-label="价格筛选">
          <label>单价下限<input data-role="price-min" type="number" min="0" step="100" inputmode="numeric" placeholder="元/㎡"></label>
          <label>单价上限<input data-role="price-max" type="number" min="0" step="100" inputmode="numeric" placeholder="元/㎡"></label>
          <label>总价下限<input data-role="total-min" type="number" min="0" step="10000" inputmode="numeric" placeholder="万元"></label>
          <label>总价上限<input data-role="total-max" type="number" min="0" step="10000" inputmode="numeric" placeholder="万元"></label>
        </div>
      </div>
      <p class="floor-note">楼层分布按楼栋从左到右、楼层从上到下、同一楼层横向一排整体排布；已售为红色，可售为绿色并展示单价、总价；可售房源相同单价使用同一色块。</p>
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



ONE_PRICE_CSS = r'''.one-price{overflow:hidden;margin:0 0 24px;border:1px solid var(--line);border-radius:18px;background:var(--panel);box-shadow:var(--shadow)}.one-price.empty{display:grid;min-height:170px;place-items:center;color:var(--muted)}.one-price-head{display:flex;justify-content:space-between;gap:16px;align-items:start;padding:18px 18px 14px}.one-price-head h2{margin:0}.one-price-head p{margin:4px 0 0;color:var(--muted);font-size:13px}.one-price-head a{display:inline-flex;min-height:36px;align-items:center;padding:0 12px;border-radius:10px;background:var(--panel-soft);color:var(--brand-ink);font-size:12px;font-weight:800;text-decoration:none;white-space:nowrap}.one-price-error{margin:0;padding:13px 18px;background:color-mix(in srgb,#b42318 10%,var(--panel));color:#b42318;font-weight:750}.one-price-note{margin:0;padding:14px 18px;color:var(--muted)}.one-price-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:1px;background:var(--panel-soft)}.one-price-metric{min-width:0;padding:13px;background:var(--panel)}.one-price-metric span{display:block;color:var(--muted);font-size:11px}.one-price-metric strong{display:block;margin-top:2px;font-size:21px;letter-spacing:-.045em}.one-price-metric.available strong{color:#137a4b}.one-price-metric.sold strong{color:#a35613}.one-price-metric.abnormal strong{color:#a33815}@media (prefers-color-scheme:dark){.one-price-metric.available strong{color:#75d9a5}.one-price-metric.sold strong{color:#f0b76a}.one-price-metric.abnormal strong{color:#ff9d7a}.one-price-error{background:#43110c;color:#ffab94}}.room-controls{display:grid;grid-template-columns:auto minmax(170px,220px) minmax(140px,180px) minmax(130px,170px) minmax(220px,1fr);gap:9px;padding:13px 14px;border-top:1px solid var(--line);background:var(--panel-soft)}.room-controls label,.room-filters,.numeric-filters{display:flex;min-width:0;align-items:center;gap:7px;color:var(--muted);font-size:12px;font-weight:750}.room-controls select,.room-controls input{min-width:0;flex:1;height:38px;padding:0 10px;border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--ink);font:inherit;font-size:13px;outline:none}.room-controls input:focus-visible,.room-controls select:focus-visible{border-color:var(--focus)}.view-switch{display:flex;gap:5px}.view-switch button,.room-filters button{height:38px;padding:0 11px;border:0;border-radius:10px;background:var(--panel);color:var(--muted);font:inherit;font-size:12px;font-weight:800;cursor:pointer}.view-switch button[aria-pressed=true],.room-filters button[aria-pressed=true]{background:var(--brand);color:#fff}.room-filters,.numeric-filters{grid-column:1/-1;flex-wrap:wrap}.room-filters{justify-content:flex-start;overflow:visible}.numeric-filters{display:grid;grid-template-columns:repeat(4,minmax(130px,1fr));gap:7px}.numeric-filters label{flex-direction:column;align-items:stretch;gap:4px}.numeric-filters input{width:100%}.floor-note{margin:0;padding:9px 15px;border-top:1px solid var(--line);background:var(--panel);color:var(--muted);font-size:12px}.room-table-wrap{overflow-x:auto;border-top:1px solid var(--line)}.room-table{width:100%;min-width:1030px;border-collapse:collapse;font-size:13px}.room-table th,.room-table td{padding:11px 13px;border-top:1px solid var(--line);text-align:left;vertical-align:top;white-space:nowrap}.room-table thead th{position:sticky;top:0;background:var(--panel);color:var(--muted);font-size:11px}.room-table td.loading{color:var(--muted)}.status{display:inline-flex;height:24px;align-items:center;padding:0 8px;border-radius:999px;background:var(--panel-soft);color:var(--muted);font-size:11px;font-weight:800}.status.available{color:#137a4b;background:color-mix(in srgb,#137a4b 12%,var(--panel))}.status.sold{color:#a35613;background:color-mix(in srgb,#a35613 12%,var(--panel))}.status.abnormal{margin-left:5px;color:#a33815;background:color-mix(in srgb,#a33815 12%,var(--panel))}@media (prefers-color-scheme:dark){.status.available{color:#75d9a5}.status.sold{color:#f0b76a}.status.abnormal{color:#ff9d7a}}.floor-results{padding:14px;border-top:1px solid var(--line);background:var(--panel)}.floor-results>.loading{margin:0;color:var(--muted)}.floor-scroll{overflow-x:auto;padding:2px 2px 5px}.floor-matrix{display:grid;grid-template-columns:minmax(56px,64px) repeat(var(--floor-columns,1),minmax(136px,1fr));gap:7px;min-width:max-content;align-items:stretch}.floor-corner,.floor-column-head,.floor-label{color:var(--muted);font-size:11px;font-weight:800}.floor-corner{display:flex;min-height:46px;align-items:center;justify-content:flex-end;text-align:right}.floor-column-head{display:flex;min-height:46px;flex-direction:column;justify-content:center;gap:2px;padding:0 10px;border:1px solid var(--line);border-radius:10px;background:var(--panel-soft);text-align:center}.floor-column-head strong{color:var(--ink);font-size:13px}.floor-column-head span{font-size:10px}.floor-label{position:sticky;left:0;z-index:1;display:flex;min-height:48px;align-items:center;justify-content:flex-end;padding-right:6px;background:var(--panel);text-align:right}.floor-missing{display:flex;min-height:112px;align-items:center;justify-content:center;border:1px dashed var(--line);border-radius:10px;background:color-mix(in srgb,var(--muted) 6%,var(--panel));color:var(--muted);font-size:11px;font-weight:800}.room-cells{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(126px,1fr);gap:7px;min-width:max-content}.floor-room{position:relative;min-width:0;min-height:112px;padding:8px 9px 8px 11px;border:1px solid var(--line);border-left:5px solid var(--price-color,var(--brand));border-radius:10px;background:color-mix(in srgb,var(--price-color,var(--brand)) 13%,var(--panel));color:var(--ink);cursor:default}.floor-room.available{border-left-color:var(--price-color,var(--brand));background:color-mix(in srgb,#137a4b 10%,var(--panel))}.floor-room.sold{border-left-color:#b42318;background:color-mix(in srgb,#b42318 14%,var(--panel))}.floor-room:focus-visible{outline:3px solid var(--focus);outline-offset:3px}.floor-price{display:block;margin:0 0 4px;color:var(--muted);font-size:10px;font-weight:800;letter-spacing:0}.floor-room strong{display:block;font-size:14px;letter-spacing:-.02em;overflow-wrap:anywhere}.floor-meta{display:block;margin-top:3px;color:var(--muted);font-size:10px;font-weight:750;overflow-wrap:anywhere}.floor-total{display:block;margin-top:4px;color:var(--muted);font-size:10px;font-weight:750}.floor-room .status{margin-top:6px}.floor-room .status+.status{margin-left:5px}.price-swatch{position:absolute;top:7px;right:7px;width:15px;height:15px;border:2px solid var(--panel);border-radius:4px;background:var(--price-color,var(--brand))}.room-foot{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 15px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}.room-foot p{margin:0}.room-foot button{height:36px;padding:0 13px;border:0;border-radius:10px;background:var(--brand);color:#fff;font:inherit;font-size:12px;font-weight:800;cursor:pointer}@media (prefers-color-scheme:dark){.room-foot button{color:#07131d}.view-switch button[aria-pressed=true],.room-filters button[aria-pressed=true]{color:#07131d}}.certificate-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1px;padding:1px;background:var(--panel-soft);border-top:1px solid var(--line)}.certificate-card{min-width:0;padding:14px;background:var(--panel)}.certificate-card h3{margin:0 0 8px;font-size:13px;line-height:1.45;overflow-wrap:anywhere}.certificate-card dl{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:0}.certificate-card div{min-width:0}.certificate-card dt{color:var(--muted);font-size:10px}.certificate-card dd{margin:2px 0 0;font-size:14px;font-weight:800}@media (max-width:760px){.one-price-head{align-items:start;flex-direction:column}.one-price-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.one-price-metric:last-child{grid-column:1/-1}.room-controls{grid-template-columns:1fr}.view-switch{display:grid;grid-template-columns:1fr 1fr}.view-switch button,.room-filters button{min-height:44px}.room-controls select,.room-controls input{min-height:44px}.numeric-filters{grid-template-columns:1fr 1fr}.room-filters{justify-content:flex-start}.room-foot{align-items:stretch;flex-direction:column}.room-foot button{width:100%}.certificate-card dl{grid-template-columns:repeat(2,1fr)}}@media (max-width:430px){.numeric-filters{grid-template-columns:1fr}}@media (prefers-reduced-motion:reduce){.one-price *,.one-price *::before,.one-price *::after{transition-duration:.01ms!important;animation-duration:.01ms!important}}'''


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
      if(Number(room.saleStatus)!==2)return;
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
  function filterRooms(){
    var words=query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return rooms.filter(function(room){
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
      return words.every(function(word){return haystack.indexOf(word)>=0});
    });
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
    var available=Number(room.saleStatus)===2;var group=available?priceGroups.get(priceKey(room)):null;
    var article=document.createElement('article');article.className='floor-room'+(available?' available':' sold');article.tabIndex=0;
    article.setAttribute('data-price',text(room.price));article.setAttribute('data-price-value',numericValue(room.price)===null?'':String(numericValue(room.price)));article.setAttribute('data-total-price',text(room.totalPrice));
    article.setAttribute('data-price-group',available?priceKey(room):'sold');article.setAttribute('data-room-status',available?'available':'sold');
    if(group)article.style.setProperty('--price-color',group);
    article.setAttribute('aria-label',text(room.buildName)+text(room.unitName)+text(room.floor)+' '+text(room.roomName)+(available?'，可售':'，已售')+'，单价 '+money(room.price)+'，总价 '+total(room.totalPrice));
    var price=document.createElement('span');price.className='floor-price';price.textContent=money(room.price);article.appendChild(price);
    var name=document.createElement('strong');name.textContent=text(room.roomName);article.appendChild(name);
    var meta=document.createElement('span');meta.className='floor-meta';meta.textContent=text(room.roomLayout)+' · '+area(room.area);article.appendChild(meta);
    var totalPrice=document.createElement('span');totalPrice.className='floor-total';totalPrice.textContent=total(room.totalPrice);article.appendChild(totalPrice);
    var badge=document.createElement('span');badge.className='status '+(available?'available':'sold');badge.textContent=available?'可售':'已售';article.appendChild(badge);
    if(Number(room.abnormalStatus)===1){var abnormal=document.createElement('span');abnormal.className='status abnormal';abnormal.textContent='异常';article.appendChild(abnormal);}
    if(group){var swatch=document.createElement('span');swatch.className='price-swatch';swatch.setAttribute('aria-hidden','true');article.appendChild(swatch);}
    return article;
  }
  function floorHeader(column){
    var head=document.createElement('div');head.className='floor-column-head';
    var building=document.createElement('strong');building.textContent=text(column.building);head.appendChild(building);
    var unit=document.createElement('span');unit.textContent='单元 '+text(column.unitName);head.appendChild(unit);
    return head;
  }
  function renderFloorView(filtered){
    floorResults.replaceChildren();
    if(!filtered.length){var empty=document.createElement('p');empty.className='loading';empty.textContent='没有符合筛选条件的房源';floorResults.appendChild(empty);return;}
    var columns=[];var columnSeen=new Set();var floors=[];var floorSeen=new Set();var floorRooms=new Map();
    filtered.forEach(function(room){
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
    var scroll=document.createElement('div');scroll.className='floor-scroll';
    var matrix=document.createElement('div');matrix.className='floor-matrix';matrix.style.setProperty('--floor-columns',String(columns.length));
    matrix.setAttribute('aria-label','楼栋从左到右、楼层从上到下、同一楼层横向一排的一房一价分布');
    var corner=document.createElement('div');corner.className='floor-corner';corner.textContent='楼层 / 楼栋';matrix.appendChild(corner);
    columns.forEach(function(column){matrix.appendChild(floorHeader(column))});
    floors.forEach(function(floor){
      var label=document.createElement('div');label.className='floor-label';label.textContent=floor;matrix.appendChild(label);
      columns.forEach(function(column){
        var rooms=floorRooms.get(column.key);
        var values=rooms&&rooms.get(floor);
        if(values&&values.length){
          var cells=document.createElement('div');cells.className='room-cells';
          values.sort(function(left,right){return naturalCompare(left.roomName,right.roomName)}).forEach(function(room){cells.appendChild(roomCell(room))});
          matrix.appendChild(cells);
        }else{
          var missing=document.createElement('div');missing.className='floor-missing';missing.textContent='—';
          missing.setAttribute('aria-label',text(column.building)+' '+text(column.unitName)+' '+floor+' 无房源');matrix.appendChild(missing);
        }
      });
    });
    scroll.appendChild(matrix);floorResults.appendChild(scroll);
  }
  function render(){
    refreshBuildingOptions();refreshUnitOptions();
    var filtered=filterRooms();
    if(view==='table'){
      var fragment=document.createDocumentFragment();
      filtered.slice(0,limit).forEach(function(room){fragment.appendChild(row(room))});
      if(!filtered.length){var empty=document.createElement('tr');var cell=document.createElement('td');cell.colSpan=11;cell.className='loading';cell.textContent='没有符合筛选条件的房源';empty.appendChild(cell);fragment.appendChild(empty);}
      tbody.replaceChildren(fragment);floorResults.replaceChildren();
    }else{renderFloorView(filtered);}
    tableWrap.hidden=view!=='table';floorResults.hidden=view==='table';
    count.textContent=view==='table'?'显示 '+Math.min(limit,filtered.length)+' / '+filtered.length+' 套房源':'楼层分布显示 '+filtered.length+' 套房源';
    more.hidden=view!=='table'||limit>=filtered.length;setSummary(rooms);
  }
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
