from __future__ import annotations

from typing import Any, Protocol

from .client import SaleApiError


class OnePriceClient(Protocol):
    def fetch_presale_certificates(self, project_id: int | str) -> list[dict[str, Any]]: ...
    def fetch_room_items(self, project_id: int | str, evidence_id: int | str) -> list[dict[str, Any]]: ...


def build_one_price_snapshot(client: OnePriceClient, project_id: int | str) -> dict[str, Any]:
    try:
        certificates = client.fetch_presale_certificates(project_id)
    except SaleApiError as exc:
        return {'status': 'error', 'message': str(exc), 'certificates': []}

    enriched: list[dict[str, Any]] = []
    for certificate in certificates:
        item = dict(certificate)
        evidence_id = item.get('id')
        try:
            item['rooms'] = [] if evidence_id is None else client.fetch_room_items(project_id, evidence_id)
        except SaleApiError as exc:
            return {
                'status': 'error',
                'message': str(exc),
                'certificates': enriched,
            }
        enriched.append(item)

    return {
        'status': 'complete' if certificates else 'empty',
        'certificates': enriched,
    }


def summarize_one_price(snapshot: dict[str, Any]) -> dict[str, int]:
    rooms = [
        room
        for certificate in snapshot.get('certificates', [])
        if isinstance(certificate, dict)
        for room in certificate.get('rooms', [])
        if isinstance(room, dict)
    ]
    return {
        'certificates': len(snapshot.get('certificates', [])),
        'rooms': len(rooms),
        'sold': sum(room.get('saleStatus') == 1 for room in rooms),
        'available': sum(room.get('saleStatus') == 2 for room in rooms),
        'abnormal': sum(room.get('abnormalStatus') == 1 for room in rooms),
    }
