from __future__ import annotations

from datetime import timedelta
from typing import Any

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KecoApiClient
from .const import CONF_STATIONS, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class KecoCoordinator(DataUpdateCoordinator[dict[str, list[dict[str, Any]]]]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: KecoApiClient,
        stations: list[dict[str, str]],
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name="keco_evcharger",
            update_interval=timedelta(seconds=update_interval),
        )
        self.client = client
        self.stations = stations

    @classmethod
    def from_entry(cls, hass: HomeAssistant, entry, client: KecoApiClient):
        options = entry.options or {}
        stations = options.get(CONF_STATIONS, [])
        return cls(hass, client, stations, DEFAULT_UPDATE_INTERVAL)

    async def _async_update_data(self) -> dict[str, list[dict[str, Any]]]:
        try:
            data: dict[str, list[dict[str, Any]]] = {}
            for st in self.stations:
                stat_id = st.get("statId", "")
                if not stat_id:
                    continue
                data[stat_id] = await self.client.get_station_chargers(stat_id)
            return data
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
