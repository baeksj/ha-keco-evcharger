from __future__ import annotations

DOMAIN = "keco_evcharger"
PLATFORMS = ["sensor"]

CONF_API_KEY = "api_key"
CONF_STATIONS = "stations"
DEFAULT_UPDATE_INTERVAL = 300

API_BASE = "https://apis.data.go.kr/B552584/EvCharger"

STAT_TEXT = {
    "1": "통신이상",
    "2": "충전대기",
    "3": "충전중",
    "4": "운영중지",
    "5": "점검중",
    "9": "상태미확인",
}
