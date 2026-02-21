from __future__ import annotations

from datetime import timedelta
from typing import Any

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KecoApiClient
from .const import (
    CONF_ADDR,
    CONF_BUSI_NM,
    CONF_MAX_CONSECUTIVE_FAILURES,
    CONF_STAT_ID,
    CONF_STAT_NM,
    DEFAULT_MAX_CONSECUTIVE_FAILURES,
    DEFAULT_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class KecoCoordinator(DataUpdateCoordinator[dict[str, list[dict[str, Any]]]]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: KecoApiClient,
        station: dict[str, str],
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
        max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="keco_evcharger",
            update_interval=timedelta(seconds=update_interval),
        )
        self.client = client
        self.station = station
        self._max_consecutive_failures = max(1, int(max_consecutive_failures))
        # Keep last known charger rows to avoid transient `unavailable`
        # when upstream API temporarily omits one charger in a station response.
        self._last_rows_by_chger_id: dict[str, dict[str, Any]] = {}
        # API error tolerance:
        # - failures 1~2: keep previous state (do not mark entities unavailable)
        # - failure 3+: mark unavailable by raising UpdateFailed
        self._consecutive_failures = 0

    @classmethod
    def from_entry(cls, hass: HomeAssistant, entry, client: KecoApiClient):
        # backward compatibility for early single-entry/stations[] prototype
        stat_id = entry.data.get(CONF_STAT_ID)
        if not stat_id:
            stations = (entry.options or {}).get("stations", [])
            first = stations[0] if stations else {}
            station = {
                CONF_STAT_ID: first.get(CONF_STAT_ID, ""),
                CONF_STAT_NM: first.get(CONF_STAT_NM, ""),
                CONF_ADDR: first.get(CONF_ADDR, ""),
                CONF_BUSI_NM: first.get(CONF_BUSI_NM, ""),
            }
        else:
            station = {
                CONF_STAT_ID: entry.data.get(CONF_STAT_ID, ""),
                CONF_STAT_NM: entry.data.get(CONF_STAT_NM, ""),
                CONF_ADDR: entry.data.get(CONF_ADDR, ""),
                CONF_BUSI_NM: entry.data.get(CONF_BUSI_NM, ""),
            }

        max_failures = int((entry.options or {}).get(CONF_MAX_CONSECUTIVE_FAILURES, DEFAULT_MAX_CONSECUTIVE_FAILURES))
        return cls(hass, client, station, DEFAULT_UPDATE_INTERVAL, max_failures)

    async def _async_update_data(self) -> dict[str, list[dict[str, Any]]]:
        stat_id = self.station.get(CONF_STAT_ID, "")
        if not stat_id:
            return {}

        try:
            rows = await self.client.get_station_chargers(stat_id)
            self._consecutive_failures = 0

            # Refresh last-known cache from latest payload.
            seen: set[str] = set()
            for row in rows:
                chger_id = str(row.get("chgerId", "")).strip()
                if not chger_id:
                    continue
                seen.add(chger_id)
                self._last_rows_by_chger_id[chger_id] = row

            # If a charger is temporarily missing in this poll, keep last known row.
            merged: list[dict[str, Any]] = list(rows)
            for chger_id, cached in self._last_rows_by_chger_id.items():
                if chger_id in seen:
                    continue
                merged.append(cached)

            return {stat_id: merged}

        except Exception as err:  # noqa: BLE001
            self._consecutive_failures += 1

            if self._consecutive_failures < self._max_consecutive_failures:
                _LOGGER.warning(
                    "KECO API error (%s/%s). Keeping previous state: %s",
                    self._consecutive_failures,
                    self._max_consecutive_failures,
                    err,
                )
                return self.data or {}

            raise UpdateFailed(str(err)) from err
