"""Thin CoinGecko API client with retries, backoff and rate-limit handling."""
from __future__ import annotations

import logging
import time
from typing import Any

import requests

from . import config

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 5


class CoinGeckoClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        headers = {"Accept": "application/json"}
        if config.API_KEY:
            headers["x-cg-demo-api-key"] = config.API_KEY
        self.session.headers.update(headers)

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        url = f"{config.COINGECKO_BASE_URL}{path}"
        for attempt in range(1, MAX_RETRIES + 1):
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                time.sleep(config.REQUEST_PACING_SECONDS)
                return resp.json()
            if resp.status_code == 429:
                wait = BACKOFF_BASE_SECONDS * 2**attempt
                logger.warning("Rate limited (429). Sleeping %ss (attempt %s)", wait, attempt)
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = BACKOFF_BASE_SECONDS * attempt
                logger.warning("Server error %s. Sleeping %ss", resp.status_code, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
        raise RuntimeError(f"Giving up on {path} after {MAX_RETRIES} retries")

    def market_chart_range(
        self, coin_id: str, from_ts: int, to_ts: int
    ) -> dict[str, list[list[float]]]:
        """Hourly prices / market caps / 24h-rolling volumes for a unix-ts window.

        CoinGecko returns hourly granularity for windows between 1 and 90 days.
        """
        return self._get(
            f"/coins/{coin_id}/market_chart/range",
            {"vs_currency": config.VS_CURRENCY, "from": from_ts, "to": to_ts},
        )

    def coins_markets(self, coin_ids: list[str]) -> list[dict[str, Any]]:
        """Current market snapshot + metadata for a list of coins (1 call)."""
        return self._get(
            "/coins/markets",
            {
                "vs_currency": config.VS_CURRENCY,
                "ids": ",".join(coin_ids),
                "order": "market_cap_desc",
                "per_page": len(coin_ids),
                "sparkline": "false",
            },
        )
