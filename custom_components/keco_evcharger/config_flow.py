from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .api import KecoApiClient
from .const import (
    CONF_API_KEY,
    CONF_ENABLED_CHARGERS,
    CONF_STAT_ID,
    CONF_STAT_NM,
    CONF_ADDR,
    CONF_BUSI_NM,
    DOMAIN,
)

ZCODE_OPTIONS = {
    "11": "서울",
    "26": "부산",
    "27": "대구",
    "28": "인천",
    "29": "광주",
    "30": "대전",
    "31": "울산",
    "36": "세종",
    "41": "경기",
    "42": "강원",
    "43": "충북",
    "44": "충남",
    "45": "전북",
    "46": "전남",
    "47": "경북",
    "48": "경남",
    "50": "제주",
}


class KecoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self) -> None:
        self._api_key: str = ""
        self._search_results: list[dict[str, Any]] = []
        self._search_zcode: str = "11"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        existing = self._async_current_entries()
        if existing:
            self._api_key = existing[0].data.get(CONF_API_KEY, "")
            return await self.async_step_search_station()

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            client = KecoApiClient(api_key)
            try:
                await client.validate_key()
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                self._api_key = api_key
                return await self.async_step_search_station()

        schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_search_station(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get("reset", False):
                self._search_results = []
                self._search_zcode = "11"
                schema = vol.Schema(
                    {
                        vol.Required("zcode", default="11"): vol.In(ZCODE_OPTIONS),
                        vol.Required("query", default=""): str,
                        vol.Optional("reset", default=False): bool,
                    }
                )
                return self.async_show_form(step_id="search_station", data_schema=schema)

            query = user_input["query"].strip()
            zcode = str(user_input.get("zcode", "11"))
            self._search_zcode = zcode
            client = KecoApiClient(self._api_key)
            try:
                self._search_results = await client.search_stations(query, zcode=zcode)
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                if not self._search_results:
                    errors["base"] = "no_results"
                else:
                    return await self.async_step_pick_station()

        schema = vol.Schema(
            {
                vol.Required("zcode", default=self._search_zcode): vol.In(ZCODE_OPTIONS),
                vol.Required("query", default=""): str,
                vol.Optional("reset", default=False): bool,
            }
        )
        return self.async_show_form(step_id="search_station", data_schema=schema, errors=errors)

    async def async_step_pick_station(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            idx = int(user_input["station"])
            picked = self._search_results[idx]
            stat_id = picked.get(CONF_STAT_ID, "")

            await self.async_set_unique_id(stat_id)
            self._abort_if_unique_id_configured()

            title = f"{picked.get(CONF_STAT_NM, stat_id)} ({stat_id})"
            return self.async_create_entry(
                title=title,
                data={
                    CONF_API_KEY: self._api_key,
                    CONF_STAT_ID: stat_id,
                    CONF_STAT_NM: picked.get(CONF_STAT_NM, ""),
                    CONF_ADDR: picked.get(CONF_ADDR, ""),
                    CONF_BUSI_NM: picked.get(CONF_BUSI_NM, ""),
                },
                options={CONF_ENABLED_CHARGERS: []},
            )

        options = {
            str(i): f"{s.get(CONF_STAT_NM,'')} | {s.get(CONF_ADDR,'')} | {s.get(CONF_BUSI_NM,'')} | {s.get(CONF_STAT_ID,'')}"
            for i, s in enumerate(self._search_results)
        }
        schema = vol.Schema({vol.Required("station"): vol.In(options)})
        return self.async_show_form(step_id="pick_station", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "KecoOptionsFlow":
        return KecoOptionsFlow(config_entry)


class KecoOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry
        self.client = KecoApiClient(entry.data[CONF_API_KEY])

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        stat_id = self.entry.data.get(CONF_STAT_ID, "")

        try:
            chargers = await self.client.get_station_chargers(stat_id)
        except Exception:  # noqa: BLE001
            return self.async_show_form(step_id="init", data_schema=vol.Schema({}), errors={"base": "cannot_connect"})

        ids = sorted({str(c.get("chgerId", "")).strip() for c in chargers if str(c.get("chgerId", "")).strip()})
        options = {cid: f"충전기 {cid}" for cid in ids}

        if user_input is not None:
            selected = user_input.get(CONF_ENABLED_CHARGERS, [])
            return self.async_create_entry(
                title="",
                data={
                    **self.entry.options,
                    CONF_ENABLED_CHARGERS: selected,
                },
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLED_CHARGERS,
                    default=self.entry.options.get(CONF_ENABLED_CHARGERS, ids),
                ): cv.multi_select(options)
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
