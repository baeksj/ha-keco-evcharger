from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENABLED_CHARGERS, CONF_STAT_ID, CONF_STAT_NM, DOMAIN, STAT_TEXT
from .coordinator import KecoCoordinator


def _parse_ts(v: str | None) -> datetime | None:
    if not v:
        return None
    raw = str(v).strip()
    if not raw or raw in {"0", "00000000000000"}:
        return None
    try:
        # KECO timestamp payload is local Korea time (YYYYmmddHHMMSS).
        # Home Assistant timestamp sensors need timezone-aware datetime.
        dt = datetime.strptime(raw, "%Y%m%d%H%M%S")
        return dt.replace(tzinfo=ZoneInfo("Asia/Seoul"))
    except ValueError:
        return None


@dataclass(frozen=True, kw_only=True)
class KecoSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    enabled_default: bool = True


SENSOR_TYPES: tuple[KecoSensorDescription, ...] = (
    KecoSensorDescription(
        key="status_text",
        name="상태",
        value_fn=lambda d: STAT_TEXT.get(str(d.get("stat", "")), f"미정의({d.get('stat', '')})"),
        icon="mdi:ev-station",
    ),
    KecoSensorDescription(
        key="status_code",
        name="상태 코드",
        value_fn=lambda d: str(d.get("stat", "")),
        enabled_default=False,
        icon="mdi:code-tags",
    ),
    KecoSensorDescription(
        key="stat_upd_dt",
        name="상태 갱신 시각",
        value_fn=lambda d: _parse_ts(d.get("statUpdDt")),
        device_class="timestamp",
    ),
    KecoSensorDescription(
        key="now_tsdt",
        name="현재 충전 시작 시각",
        value_fn=lambda d: _parse_ts(d.get("nowTsdt")),
        device_class="timestamp",
    ),
    KecoSensorDescription(
        key="last_tsdt",
        name="직전 충전 시작 시각",
        value_fn=lambda d: _parse_ts(d.get("lastTsdt")),
        device_class="timestamp",
        enabled_default=False,
    ),
    KecoSensorDescription(
        key="last_tedt",
        name="직전 충전 종료 시각",
        value_fn=lambda d: _parse_ts(d.get("lastTedt")),
        device_class="timestamp",
        enabled_default=False,
    ),
    KecoSensorDescription(
        key="output_kw",
        name="출력(kW)",
        value_fn=lambda d: float(d.get("output")) if str(d.get("output", "")).strip() else None,
        native_unit_of_measurement="kW",
        enabled_default=False,
        icon="mdi:flash",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: KecoCoordinator = data["coordinator"]

    stat_id = coordinator.station.get(CONF_STAT_ID, "")
    station_name = coordinator.station.get(CONF_STAT_NM, stat_id)

    selected = entry.options.get(CONF_ENABLED_CHARGERS, [])
    selected_ids = {str(x) for x in selected} if selected else None

    entities: list[KecoChargerSensor] = []
    for charger in coordinator.data.get(stat_id, []):
        chger_id = str(charger.get("chgerId", ""))
        if not chger_id:
            continue
        if selected_ids is not None and chger_id not in selected_ids:
            continue

        for desc in SENSOR_TYPES:
            entities.append(
                KecoChargerSensor(
                    coordinator=coordinator,
                    entry_id=entry.entry_id,
                    station_name=station_name,
                    stat_id=stat_id,
                    chger_id=chger_id,
                    description=desc,
                )
            )

    async_add_entities(entities)


class KecoChargerSensor(CoordinatorEntity[KecoCoordinator], SensorEntity):
    entity_description: KecoSensorDescription

    def __init__(
        self,
        *,
        coordinator: KecoCoordinator,
        entry_id: str,
        station_name: str,
        stat_id: str,
        chger_id: str,
        description: KecoSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._stat_id = stat_id
        self._chger_id = chger_id
        self._station_name = station_name
        self._attr_unique_id = f"{entry_id}_{stat_id}_{chger_id}_{description.key}"
        self._attr_name = f"{station_name} {chger_id} {description.name}"
        self._attr_entity_registry_enabled_default = description.enabled_default

    @property
    def native_value(self):
        row = self._charger_row
        if not row:
            return None
        return self.entity_description.value_fn(row)

    @property
    def extra_state_attributes(self):
        row = self._charger_row
        if not row:
            return None
        return {
            "statId": row.get("statId"),
            "chgerId": row.get("chgerId"),
            "statNm": row.get("statNm"),
            "addr": row.get("addr"),
            "busiNm": row.get("busiNm"),
            "chgerType": row.get("chgerType"),
            "output": row.get("output"),
            "method": row.get("method"),
        }

    @property
    def device_info(self):
        row = self._charger_row or {}
        return {
            "identifiers": {(DOMAIN, f"{self._stat_id}_{self._chger_id}")},
            "name": f"{self._station_name} #{self._chger_id}",
            "manufacturer": row.get("busiNm") or "공공충전인프라",
            "model": "KECO EV Charger",
            "suggested_area": "EV",
        }

    @property
    def _charger_row(self) -> dict[str, Any] | None:
        rows = self.coordinator.data.get(self._stat_id, [])
        for row in rows:
            if str(row.get("chgerId", "")) == self._chger_id:
                return row
        return None
