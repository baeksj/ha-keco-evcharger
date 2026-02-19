from __future__ import annotations

from typing import Any

import httpx

from .const import API_BASE


class KecoApiClient:
    def __init__(self, api_key: str, timeout: float = 12.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    async def _get(self, path: str, **params: Any) -> dict[str, Any]:
        query = {
            "serviceKey": self._api_key,
            "dataType": "JSON",
            **params,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{API_BASE}/{path}", params=query)
            resp.raise_for_status()
            payload = resp.json()

        code = str(payload.get("resultCode", ""))
        if code and code != "00":
            msg = payload.get("resultMsg", "unknown error")
            raise RuntimeError(f"KECO API error {code}: {msg}")
        return payload

    async def validate_key(self) -> None:
        await self._get("getChargerInfo", pageNo=1, numOfRows=1, zcode="11")

    async def search_stations(self, query: str, zcode: str = "11") -> list[dict[str, Any]]:
        # Public API has no keyword endpoint. We fetch regional page and filter locally.
        data = await self._get("getChargerInfo", pageNo=1, numOfRows=9999, zcode=zcode)
        items = data.get("items", {}).get("item", []) or []

        q = (query or "").strip().lower()
        if not q:
            return []

        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for it in items:
            stat_id = (it.get("statId") or "").strip()
            stat_nm = (it.get("statNm") or "").strip()
            addr = (it.get("addr") or "").strip()
            busi_nm = (it.get("busiNm") or "").strip()
            if not stat_id or stat_id in seen:
                continue

            hay = f"{stat_nm} {addr} {busi_nm} {stat_id}".lower()
            if q in hay:
                seen.add(stat_id)
                out.append(
                    {
                        "statId": stat_id,
                        "statNm": stat_nm,
                        "addr": addr,
                        "busiNm": busi_nm,
                    }
                )
        return out

    async def get_station_chargers(self, stat_id: str) -> list[dict[str, Any]]:
        data = await self._get("getChargerInfo", pageNo=1, numOfRows=200, statId=stat_id)
        return data.get("items", {}).get("item", []) or []
