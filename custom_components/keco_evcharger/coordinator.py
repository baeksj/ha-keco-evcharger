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
    CONF_STAT_ID,
    CONF_STAT_NM,
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
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="keco_evcharger",
            update_interval=timedelta(seconds=update_interval),
        )
        self.client = client
        self.station = station

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

        return cls(hass, client, station, DEFAULT_UPDATE_INTERVAL)

    async def _async_update_data(self) -> dict[str, list[dict[str, Any]]]:
        try:
            stat_id = self.station.get(CONF_STAT_ID, "")
            if not stat_id:
                return {}
            rows = await self.client.get_station_chargers(stat_id)
            return {stat_id: rows}
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
