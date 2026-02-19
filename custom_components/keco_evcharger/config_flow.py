from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .api import KecoApiClient
from .const import CONF_API_KEY, CONF_STATIONS, DOMAIN


class KecoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            client = KecoApiClient(api_key)
            try:
                await client.validate_key()
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id("keco_evcharger")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="KECO EV Charger",
                    data={CONF_API_KEY: api_key},
                    options={CONF_STATIONS: []},
                )

        schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "KecoOptionsFlow":
        return KecoOptionsFlow(config_entry)


class KecoOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry
        self.client = KecoApiClient(entry.data[CONF_API_KEY])
        self._search_results: list[dict[str, Any]] = []

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_station", "remove_station"],
        )

    async def async_step_add_station(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            query = user_input["query"].strip()
            self._search_results = await self.client.search_stations(query)
            if not self._search_results:
                errors["base"] = "no_results"
            else:
                return await self.async_step_pick_station()

        schema = vol.Schema({vol.Required("query"): str})
        return self.async_show_form(step_id="add_station", data_schema=schema, errors=errors)

    async def async_step_pick_station(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            idx = int(user_input["station"])
            picked = self._search_results[idx]

            current = list(self.entry.options.get(CONF_STATIONS, []))
            exists = any(s.get("statId") == picked.get("statId") for s in current)
            if not exists:
                current.append(picked)

            return self.async_create_entry(title="", data={**self.entry.options, CONF_STATIONS: current})

        options = {
            str(i): f"{s.get('statNm','')} | {s.get('addr','')} | {s.get('busiNm','')} | {s.get('statId','')}"
            for i, s in enumerate(self._search_results)
        }
        schema = vol.Schema({vol.Required("station"): vol.In(options)})
        return self.async_show_form(step_id="pick_station", data_schema=schema)

    async def async_step_remove_station(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        stations = list(self.entry.options.get(CONF_STATIONS, []))
        if not stations:
            return self.async_create_entry(title="", data={**self.entry.options})

        if user_input is not None:
            selected_ids = set(user_input.get("station_ids", []))
            next_stations = [s for s in stations if s.get("statId") not in selected_ids]
            return self.async_create_entry(title="", data={**self.entry.options, CONF_STATIONS: next_stations})

        options = {s.get("statId", ""): f"{s.get('statNm','')} ({s.get('statId','')})" for s in stations}
        schema = vol.Schema({vol.Optional("station_ids", default=[]): cv.multi_select(options)})
        return self.async_show_form(step_id="remove_station", data_schema=schema)
