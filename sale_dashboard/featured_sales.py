from __future__ import annotations

import json
import re
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


def _project_snapshot(project_id: Any, snapshots: dict[Any, dict[str, Any]] | None) -> dict[str, Any] | None:
    if snapshots is None:
        return None
    candidates = [project_id, str(project_id)]
    if str(project_id).isdigit():
        candidates.append(int(project_id))
    for candidate in candidates:
        snapshot = snapshots.get(candidate)
        if isinstance(snapshot, dict):
            return snapshot
    return None


def _normalized_building_key(value: Any) -> str:
    return str(value or '').strip().replace('#', '').replace('号', '').casefold()


def _project_location(project: dict[str, Any], official_build_names: list[Any]) -> dict[str, Any]:
    for field, kind in (
        ('address', '地址/街道'),
        ('streetName', '街道'),
        ('street', '街道'),
        ('areaName', '区域'),
        ('businessArea', '商圈'),
        ('districtName', '行政区'),
    ):
        value = str(project.get(field) or '').strip()
        if value:
            return {'kind': kind, 'value': value}

    names = [str(name or '').strip() for name in official_build_names if name]
    descriptive_names = [name for name in names if any(word in name for word in ('项目', '地块', '居住')) and not re.fullmatch(r'.*楼\d*号?', name)]
    if descriptive_names or names:
        source_name = sorted(descriptive_names or names, key=len, reverse=True)[0]
        clue = re.sub(r'(?:变更)?[0-9０-９]+$', '', source_name).strip(' -_·．.')
        if clue.endswith('）') and clue.count('（') < clue.count('）'):
            clue = clue[:-1]
        if clue:
            return {'kind': '项目/地块线索', 'value': clue}
    return {}


def _district_hint(values: list[Any]) -> str | None:
    match = re.search(
        r'(武汉经开|东湖高新|光谷|洪山|汉阳|武昌|江岸|江汉|硚口|青山|东西湖|蔡甸|江夏|黄陂|新洲|汉南)',
        ' '.join(str(value or '') for value in values),
    )
    return match.group(1) if match else None


def _inventory_snapshot(one_price: dict[str, Any] | None, room_types: dict[str, Any] | None) -> dict[str, Any]:
    certificates = one_price.get('certificates') if isinstance(one_price, dict) else None
    certificates = certificates if isinstance(certificates, list) else []
    rooms = [
        room
        for certificate in certificates
        if isinstance(certificate, dict)
        for room in certificate.get('rooms') or []
        if isinstance(room, dict)
    ]
    available_rooms = [room for room in rooms if room.get('saleStatus') == 2]
    areas = [value for value in (_number(room.get('area')) for room in available_rooms) if value is not None]
    prices = [value for value in (_number(room.get('totalPrice')) for room in available_rooms) if value is not None]
    types = room_types.get('types') if isinstance(room_types, dict) else None
    types = types if isinstance(types, list) else []
    completions = {
        str(item.get('completionTime'))
        for item in certificates
        if isinstance(item, dict) and item.get('completionTime')
    }
    deliveries = {
        str(item.get('deliveryTime'))
        for item in certificates
        if isinstance(item, dict) and item.get('deliveryTime')
    }
    deliveries.update(str(room.get('delivery')) for room in rooms if room.get('delivery'))
    return {
        'certificateCount': len(certificates),
        'roomCount': sum(int(item.get('houseNum') or 0) for item in certificates if isinstance(item, dict)),
        'availableCount': sum(int(item.get('availableRoomNum') or 0) for item in certificates if isinstance(item, dict)),
        'soldCount': sum(int(item.get('soldNum') or 0) for item in certificates if isinstance(item, dict)),
        'abnormalCount': sum(int(item.get('abnormalNum') or 0) for item in certificates if isinstance(item, dict)),
        'availableAveragePrice': sum(prices) / sum(areas) if areas else None,
        'roomTypeCount': len(types),
        'completionTime': min(completions) if completions else None,
        'deliveryTime': min(deliveries) if deliveries else None,
    }


def _one_price_building_catalog(one_price: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    certificates = one_price.get('certificates') if isinstance(one_price, dict) else None
    certificates = certificates if isinstance(certificates, list) else []
    catalog: dict[str, dict[str, Any]] = {}
    for certificate in certificates:
        if not isinstance(certificate, dict):
            continue
        rooms = [room for room in certificate.get('rooms') or [] if isinstance(room, dict)]
        by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for room in rooms:
            by_key[_normalized_building_key(room.get('buildName'))].append(room)
        for key, key_rooms in by_key.items():
            if not key:
                continue
            short_name = str(key_rooms[0].get('buildName') or key)
            item = catalog.setdefault(
                key,
                {
                    'officialBuildName': f'{short_name}号楼' if short_name else '未知楼栋',
                    'shortBuildName': f'{short_name}#' if short_name else None,
                    'buildType': None,
                    'floorTotal': None,
                    'units': set(),
                    'roomCount': 0,
                    'soldCount': 0,
                    'availableCount': 0,
                    'presaleCertificates': set(),
                },
            )
            item['roomCount'] += len(key_rooms)
            item['soldCount'] += sum(room.get('saleStatus') == 1 for room in key_rooms)
            item['availableCount'] += sum(room.get('saleStatus') == 2 for room in key_rooms)
            for room in key_rooms:
                if room.get('unitName'):
                    item['units'].add(str(room.get('unitName')))
                floor = _number(room.get('floor'))
                if floor is not None:
                    item['floorTotal'] = max(item['floorTotal'] or 0, int(floor))
            if certificate.get('name'):
                item['presaleCertificates'].add(str(certificate.get('name')))
    for item in catalog.values():
        item['units'] = sorted(item['units'])
        item['presaleCertificates'] = sorted(item['presaleCertificates'])
    return catalog


def _merge_building_catalogs(base: dict[str, dict[str, Any]], enrichments: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    for key, enrichment in enrichments.items():
        item = base.setdefault(key, dict(enrichment))
        for field in ('officialBuildName', 'shortBuildName', 'buildType'):
            if enrichment.get(field):
                item[field] = enrichment[field]
        floor = enrichment.get('floorTotal')
        if floor is not None:
            item['floorTotal'] = max(item.get('floorTotal') or 0, int(floor))
        item['units'] = set(item.get('units') or ()); item['units'].update(enrichment.get('units') or ())
        if enrichment.get('presaleCertificates'):
            item['presaleCertificates'] = set(item.get('presaleCertificates') or ()); item['presaleCertificates'].update(enrichment['presaleCertificates'])
    for item in base.values():
        item['units'] = sorted(item['units'], key=lambda value: ([int(part) if part.isdigit() else part for part in re.split(r'(\d+)', value)]))
        item['presaleCertificates'] = sorted(item['presaleCertificates'])
    return base


def _building_catalog(room_types: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    types = room_types.get('types') if isinstance(room_types, dict) else None
    types = types if isinstance(types, list) else []
    catalog: dict[str, dict[str, Any]] = {}
    for room_type in types:
        if not isinstance(room_type, dict):
            continue
        for source in room_type.get('buildList') or []:
            if not isinstance(source, dict):
                continue
            key = _normalized_building_key(source.get('buildShortName') or source.get('buildName'))
            item = catalog.setdefault(
                key,
                {
                    'officialBuildName': source.get('buildName'),
                    'shortBuildName': source.get('buildShortName'),
                    'buildType': source.get('buildType'),
                    'floorTotal': None,
                    'units': set(),
                    'roomCount': 0,
                    'soldCount': 0,
                    'availableCount': 0,
                    'presaleCertificates': set(),
                },
            )
            if source.get('buildName'):
                item['officialBuildName'] = source.get('buildName')
            if source.get('buildType'):
                item['buildType'] = source.get('buildType')
            floor_total = _number(source.get('floorTotal'))
            if floor_total is not None:
                item['floorTotal'] = max(item['floorTotal'] or 0, int(floor_total))
            if source.get('unitName'):
                item['units'].add(str(source.get('unitName')))
            item['roomCount'] = max(item['roomCount'], int(source.get('roomTotal') or 0))
            item['soldCount'] = max(item['soldCount'], int(source.get('soldNum') or 0))
            item['availableCount'] = max(item['availableCount'], int(source.get('availableRoomNum') or 0))
            if source.get('evidenceName'):
                item['presaleCertificates'].add(str(source.get('evidenceName')))
    for item in catalog.values():
        item['units'] = sorted(item['units'], key=lambda value: ([int(part) if part.isdigit() else part for part in re.split(r'(\d+)', value)]))
        item['presaleCertificates'] = sorted(item['presaleCertificates'])
    return catalog


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
    one_price_snapshots: dict[Any, dict[str, Any]] | None = None,
    room_type_snapshots: dict[Any, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_projects = snapshot.get('projects') if isinstance(snapshot.get('projects'), list) else snapshot.get('list')
    source_projects = source_projects if isinstance(source_projects, list) else []
    source_project_ids = {str(item.get('id')) for item in source_projects if isinstance(item, dict)}
    all_projects = [item for item in (projects or []) if isinstance(item, dict)]
    metadata_by_key: dict[str, dict[str, Any]] = {}
    for item in all_projects:
        for key in (item.get('id'), item.get('name')):
            if key is not None:
                metadata_by_key[str(key)] = item
    selected_projects, _ = split_featured_projects(
        [item for item in source_projects if isinstance(item, dict)] + all_projects,
        featured_keys,
    )
    preserved_metadata = [
        metadata_by_key.get(str(project.get('id')), metadata_by_key.get(str(project.get('name')), {}))
        for project in selected_projects
    ]
    featured_projects = [
        {
            **metadata,
            **project,
            'projectSoldCount': metadata.get('soldNum'),
        }
        for metadata, project in zip(preserved_metadata, selected_projects, strict=True)
    ]

    project_reports: list[dict[str, Any]] = []
    for project in featured_projects:
        project_id = project.get('id')
        one_price = _project_snapshot(project_id, one_price_snapshots)
        room_types = _project_snapshot(project_id, room_type_snapshots)
        building_catalog = _merge_building_catalogs(_one_price_building_catalog(one_price), _building_catalog(room_types))
        rooms_by_building: dict[tuple[Any, Any], list[dict[str, Any]]] = defaultdict(list)
        for source_room in project.get('roomList') or []:
            if not isinstance(source_room, dict):
                continue
            room = _room(source_room)
            if room is None:
                continue
            key = (source_room.get('buildName'), source_room.get('shortBuildName') or source_room.get('buildName'))
            rooms_by_building[key].append(room)

        buildings = []
        for (build_name, short_name), rooms in rooms_by_building.items():
            building = _building_snapshot(rooms, build_name, short_name)
            catalog_item = building_catalog.get(_normalized_building_key(short_name))
            if catalog_item:
                building.update(
                    {
                        'officialBuildName': catalog_item['officialBuildName'],
                        'shortBuildName': catalog_item.get('shortBuildName') or short_name,
                        'buildType': catalog_item['buildType'],
                        'floorTotal': catalog_item['floorTotal'],
                        'units': catalog_item['units'],
                        'roomCount': catalog_item['roomCount'],
                        'currentSoldCount': catalog_item['soldCount'],
                        'currentAvailableCount': catalog_item['availableCount'],
                        'presaleCertificates': catalog_item['presaleCertificates'],
                    }
                )
            buildings.append(building)
        represented_keys = {_normalized_building_key(item.get('shortBuildName')) for item in buildings}
        for key, item in building_catalog.items():
            if key in represented_keys:
                continue
            buildings.append(
                {
                    'buildName': item['officialBuildName'],
                    'shortBuildName': item['shortBuildName'],
                    'soldCount': 0,
                    'totalArea': 0,
                    'totalPrice': 0,
                    'averagePrice': None,
                    'rooms': [],
                }
            )
        for building in buildings:
            catalog_item = building_catalog.get(_normalized_building_key(building.get('shortBuildName')))
            if catalog_item:
                building.update(
                    {
                        'officialBuildName': catalog_item['officialBuildName'],
                        'shortBuildName': catalog_item.get('shortBuildName') or building.get('shortBuildName'),
                        'buildType': catalog_item['buildType'],
                        'floorTotal': catalog_item['floorTotal'],
                        'units': catalog_item['units'],
                        'roomCount': catalog_item['roomCount'],
                        'currentSoldCount': catalog_item['soldCount'],
                        'currentAvailableCount': catalog_item['availableCount'],
                        'presaleCertificates': catalog_item['presaleCertificates'],
                    }
                )
        buildings.sort(key=lambda item: str(item.get('shortBuildName') or item.get('buildName') or ''))
        has_source = str(project.get('id')) in source_project_ids
        source_count = _number(project.get('soldNum')) if has_source else None
        sold_count = sum(building['soldCount'] for building in buildings)
        project_reports.append(
            {
                'projectId': project.get('id'),
                'name': project.get('name'),
                'location': _project_location(project, [item.get('officialBuildName') for item in building_catalog.values()]),
                'district': _district_hint([project.get('name'), project.get('address'), *[item.get('officialBuildName') for item in building_catalog.values()]]),
                'projectDate': project.get('date') or project.get('time'),
                'projectSoldCount': project.get('projectSoldCount'),
                'projectAveragePrice': project.get('salePrice'),
                'inventory': _inventory_snapshot(one_price, room_types),
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


def _money(value: Any, unit: str) -> str:
    parsed = _number(value)
    return f'{parsed:,.0f} {unit}' if parsed is not None else '—'


def _percentage(numerator: Any, denominator: Any) -> str:
    top, bottom = _number(numerator), _number(denominator)
    return f'{top / bottom * 100:.1f}%' if top is not None and bottom else '—'


def _fact(label: str, value: Any) -> str:
    if value in (None, '', [], {}):
        return ''
    rendered = value if isinstance(value, str) else str(value)
    return f'<div><span>{esc(label)}</span><strong>{esc(rendered)}</strong></div>'


def _project_facts(project: dict[str, Any]) -> str:
    inventory = project.get('inventory') if isinstance(project.get('inventory'), dict) else {}
    location = project.get('location') if isinstance(project.get('location'), dict) else {}
    rows = [
        _fact(location.get('kind') or '位置', location.get('value')),
        _fact('行政区/板块线索', project.get('district')),
        _fact('列表快照日期', project.get('projectDate')),
        _fact('挂牌均价', _money(project.get('projectAveragePrice'), '元/㎡') if project.get('projectAveragePrice') is not None else None),
        _fact('预售证', inventory.get('certificateCount')),
        _fact('总房源', integer(inventory.get('roomCount')) if inventory.get('roomCount') is not None else None),
        _fact('当前可售', integer(inventory.get('availableCount')) if inventory.get('availableCount') is not None else None),
        _fact('累计已售', integer(inventory.get('soldCount')) if inventory.get('soldCount') is not None else None),
        _fact('去化率', _percentage(inventory.get('soldCount'), inventory.get('roomCount')) if inventory.get('roomCount') else None),
        _fact('户型数', inventory.get('roomTypeCount')),
        _fact('可售均价', _money(inventory.get('availableAveragePrice'), '元/㎡') if inventory.get('availableAveragePrice') is not None else None),
        _fact('预计竣工', inventory.get('completionTime')),
        _fact('交付/装修', inventory.get('deliveryTime')),
    ]
    return f'<section class="facts" aria-label="项目详情">{"".join(rows)}</section>'


def _building_meta(building: dict[str, Any]) -> str:
    chips = [
        ('楼型', building.get('buildType')),
        ('楼层', f"{integer(building.get('floorTotal'))} 层" if building.get('floorTotal') is not None else None),
        ('单元', ' / '.join(building.get('units') or []) or None),
        ('总房源', integer(building.get('roomCount')) if building.get('roomCount') is not None else None),
        ('可售', integer(building.get('currentAvailableCount')) if building.get('currentAvailableCount') is not None else None),
        ('累计已售', integer(building.get('currentSoldCount')) if building.get('currentSoldCount') is not None else None),
    ]
    chips_html = ''.join(
        f'<span>{esc(label)} {esc(value)}</span>' for label, value in chips if value not in (None, '', [], {})
    )
    certificates = building.get('presaleCertificates') or []
    if certificates:
        chips_html += f'<span class="wide">预售证 {esc("；".join(certificates))}</span>'
    stats = []
    if building.get('totalArea'):
        stats.append(f"昨日面积 {_number(building.get('totalArea')):,.2f} ㎡")
    if building.get('totalPrice'):
        stats.append(f"昨日金额 {_money(building.get('totalPrice'), '元')}")
    if building.get('averagePrice') is not None:
        stats.append(f"昨日均价 {_money(building.get('averagePrice'), '元/㎡')}")
    stats_html = f'<p class="stats">{esc(" · ".join(stats))}</p>' if stats else ''
    return f'<div class="building-meta">{chips_html}</div>{stats_html}'


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
              <header>
                <div><h3>{esc(building.get('shortBuildName') or building.get('buildName') or '未知楼栋')}</h3>
                <p>{esc(building.get('officialBuildName') or building.get('buildName') or '')}</p></div>
                <span>昨日 {integer(building.get('soldCount'))} 套</span>
              </header>
              {_building_meta(building)}
              <div class="table-wrap"><table>
                <thead><tr><th>单元</th><th>楼层</th><th>房号</th><th>面积</th><th>总价</th><th>单价</th></tr></thead>
                <tbody>{rooms or '<tr><td colspan="6">昨日无成交</td></tr>'}</tbody>
              </table></div>
            </article>'''
        )
    body = ''.join(buildings) or '<section class="empty">昨日无成交 · 暂无楼栋明细</section>'
    project_id = project.get('projectId')
    detail_url = f'../projects/{esc(project_id)}/' if project_id is not None else ''
    detail_link = f'<a class="detail-link" href="{detail_url}">查看完整详情</a>' if detail_url else ''
    return (
        f'<article class="project"><header><div><p>Featured Project</p>'
        f'<h2>{esc(project.get("name") or "未知楼盘")}</h2></div>'
        f'<div class="project-result"><strong>{integer(project.get("soldCount"))} 套</strong>'
        f'<span>昨日成交</span>{count_note}{detail_link}</div></header>'
        f'{_project_facts(project)}{body}</article>'
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
*{{box-sizing:border-box}}body{{margin:0;background:var(--featured-surface);color:var(--featured-ink);font:15px/1.58 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}}.shell{{max-width:1180px;margin:0 auto;padding:0 clamp(15px,3vw,36px) 70px}}.breadcrumb{{padding:25px 0 13px;color:var(--featured-muted);font-size:13px}}.breadcrumb a{{color:var(--featured-ink-strong);font-weight:760;text-decoration:none}}.hero{{display:flex;justify-content:space-between;gap:20px;align-items:end;padding:8px 0 23px;border-bottom:1px solid var(--featured-line)}}.eyebrow{{margin:0;color:var(--featured-brand);font-size:11px;font-weight:850;letter-spacing:.16em;text-transform:uppercase}}h1{{margin:7px 0 8px;font-size:clamp(28px,4.5vw,46px);letter-spacing:-.05em}}.subtitle{{margin:0;max-width:680px;color:var(--featured-muted)}}.kpi{{display:grid;gap:3px;min-width:150px;min-height:96px;padding:16px 18px;border:1px solid var(--featured-line);border-radius:18px;background:var(--featured-panel);box-shadow:var(--featured-shadow)}}.kpi span{{color:var(--featured-muted);font-size:12px}}.kpi strong{{font-size:31px;letter-spacing:-.04em}}.error{{margin:15px 0;padding:13px 16px;border-radius:16px;background:#b4231812;color:#b42318;font-weight:720}}.project,.building,.history{{margin-top:15px;border:1px solid var(--featured-line);border-radius:20px;background:var(--featured-panel);box-shadow:var(--featured-shadow);overflow:hidden}}.project>header,.building>header{{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:15px 17px;background:color-mix(in srgb,var(--featured-panel) 88%,var(--featured-surface))}}.project h2,.building h3{{margin:0;letter-spacing:-.03em}}.project header p{{margin:0;color:var(--featured-brand);font-size:10px;font-weight:850;letter-spacing:.14em;text-transform:uppercase}}.project header strong,.building header span{{color:var(--featured-ink-strong);font-size:15px;font-weight:820}}.pill{{display:inline-flex;margin-left:7px;padding:3px 8px;border-radius:999px;background:color-mix(in srgb,#b42318 10%,var(--featured-panel));color:#b42318;font-size:11px;font-weight:780}}.building header p{{margin:3px 0 0;color:var(--featured-muted);font-size:12px}}.project-result{{display:grid;justify-items:end;gap:2px;text-align:right}}.project-result strong{{color:var(--featured-ink-strong);font-size:20px}}.project-result span{{color:var(--featured-muted);font-size:11px}}.detail-link{{color:var(--featured-brand);font-size:12px;font-weight:760;text-decoration:none}}.facts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:1px;margin:0;border-top:1px solid var(--featured-line);background:var(--featured-line)}}.facts div{{min-width:0;padding:12px 17px;background:color-mix(in srgb,var(--featured-panel) 88%,var(--featured-surface))}}.facts span{{display:block;color:var(--featured-muted);font-size:11px}}.facts strong{{display:block;margin-top:2px;font-size:13px;font-weight:760;overflow-wrap:anywhere}}.building-meta{{display:flex;flex-wrap:wrap;gap:7px;padding:12px 17px 0}}.building-meta span{{padding:4px 8px;border:1px solid var(--featured-line);border-radius:999px;background:color-mix(in srgb,var(--featured-panel) 84%,var(--featured-surface));color:var(--featured-muted);font-size:11px;font-weight:700}}.building-meta .wide{{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.building .stats{{margin:9px 17px 0;color:var(--featured-ink-strong);font-size:12px;font-weight:750}}.building p{{margin:0;padding:8px 17px 0;color:var(--featured-muted);font-size:12px}}.table-wrap{{overflow-x:auto;padding-bottom:8px}}table{{width:100%;min-width:720px;border-collapse:collapse;font-size:13px}}th,td{{padding:10px 13px;border-top:1px solid var(--featured-line);text-align:left;white-space:nowrap}}thead th{{color:var(--featured-muted);font-size:11px}}.empty{{display:grid;min-height:160px;place-items:center;color:var(--featured-muted)}}.history h2{{margin:0;padding:16px 17px;font-size:17px}}:is(a):focus-visible{{outline:3px solid var(--featured-brand);outline-offset:3px}}@media (max-width:760px){{.hero{{align-items:start;flex-direction:column}}.kpi{{width:100%}}}}
{APPLE_DESIGN_CSS}</style></head>
<body><div class="shell">
<nav class="breadcrumb"><a href="../">全部楼盘</a><span>/</span><span>重点楼盘昨日成交</span></nav>
<header class="hero"><div><p class="eyebrow">Featured Daily Sales</p><h1>重点楼盘昨日成交</h1>
<p class="subtitle">按官方昨日网签明细统计，逐楼栋管理到单元、楼层与房号；街道/地址缺失时展示备案项目或地块线索，不自动猜街道。</p></div>
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
