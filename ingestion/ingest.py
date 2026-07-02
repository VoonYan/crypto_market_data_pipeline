"""Incremental ingestion: land raw hourly price data + coin metadata as parquet.

Usage:
    python -m ingestion.ingest            # live API, incremental from watermark
    python -m ingestion.ingest --sample   # deterministic synthetic data (offline dev/CI tests)

Each run appends one parquet file per entity under data/raw/, named by load
timestamp. Files are append-only and immutable: dbt handles dedup downstream.
"""
from __future__ import annotations

import argparse
import logging
import math
import random
import time
from datetime import datetime, timezone

import pandas as pd

from . import config, state
from .coingecko import CoinGeckoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _rows_from_market_chart(coin_id: str, payload: dict, loaded_at: str) -> pd.DataFrame:
    """Flatten the market_chart payload into tidy hourly rows."""
    prices = {int(ts): p for ts, p in payload.get("prices", [])}
    caps = {int(ts): c for ts, c in payload.get("market_caps", [])}
    vols = {int(ts): v for ts, v in payload.get("total_volumes", [])}
    rows = [
        {
            "coin_id": coin_id,
            "ts_ms": ts,
            "price_usd": price,
            "market_cap_usd": caps.get(ts),
            "volume_24h_usd": vols.get(ts),
            "_loaded_at": loaded_at,
        }
        for ts, price in sorted(prices.items())
    ]
    return pd.DataFrame(rows)


def _sample_prices(coin_id: str, from_ts: int, to_ts: int, loaded_at: str) -> pd.DataFrame:
    """Synthetic hourly random-walk data with the exact live schema.

    Deterministic per (coin, hour) so re-runs and incremental appends line up.
    """
    rng = random.Random(coin_id)
    base = 10 ** rng.uniform(0, 4.7)  # coin-specific price level
    rows = []
    start_hour = from_ts // 3600 + 1
    end_hour = to_ts // 3600
    for h in range(start_hour, end_hour + 1):
        wave = math.sin(h / 24.0) * 0.02 + math.sin(h / (24.0 * 7)) * 0.05
        noise = random.Random(f"{coin_id}-{h}").gauss(0, 0.008)
        price = base * (1 + wave + noise)
        rows.append(
            {
                "coin_id": coin_id,
                "ts_ms": h * 3600 * 1000,
                "price_usd": price,
                "market_cap_usd": price * 1_000_000,
                "volume_24h_usd": abs(noise) * price * 50_000_000,
                "_loaded_at": loaded_at,
            }
        )
    return pd.DataFrame(rows)


def ingest_prices(client: CoinGeckoClient | None, sample: bool) -> None:
    st = state.load_state(config.STATE_PATH)
    loaded_at = datetime.now(timezone.utc).isoformat()
    now_ts = int(time.time())
    frames: list[pd.DataFrame] = []

    for coin_id in config.COINS:
        watermark = state.get_watermark(st, coin_id)
        from_ts = (
            watermark + 1
            if watermark
            else now_ts - config.BACKFILL_DAYS * 86400
        )
        # Cap the window so the API keeps returning hourly granularity.
        from_ts = max(from_ts, now_ts - config.MAX_WINDOW_DAYS * 86400)
        if from_ts >= now_ts - 3600:
            logger.info("%s: watermark is current, nothing to fetch", coin_id)
            continue

        logger.info(
            "%s: fetching %s -> %s (%s)",
            coin_id,
            datetime.fromtimestamp(from_ts, timezone.utc),
            datetime.fromtimestamp(now_ts, timezone.utc),
            "incremental" if watermark else "backfill",
        )
        if sample:
            df = _sample_prices(coin_id, from_ts, now_ts, loaded_at)
        else:
            payload = client.market_chart_range(coin_id, from_ts, now_ts)
            df = _rows_from_market_chart(coin_id, payload, loaded_at)

        if df.empty:
            logger.info("%s: no new rows", coin_id)
            continue
        frames.append(df)
        state.set_watermark(st, coin_id, int(df["ts_ms"].max() // 1000))

    if not frames:
        logger.info("No new price data across all coins.")
        return

    out = pd.concat(frames, ignore_index=True)
    config.RAW_PRICES_DIR.mkdir(parents=True, exist_ok=True)
    fname = datetime.now(timezone.utc).strftime("prices_%Y%m%dT%H%M%SZ.parquet")
    out.to_parquet(config.RAW_PRICES_DIR / fname, index=False)
    state.save_state(config.STATE_PATH, st)
    logger.info("Landed %s rows -> %s", len(out), fname)


def ingest_coin_metadata(client: CoinGeckoClient | None, sample: bool) -> None:
    """Daily snapshot of coin metadata (rank, supply, ATH). Point-in-time,
    append-only: history of snapshots enables slowly-changing analysis."""
    loaded_at = datetime.now(timezone.utc).isoformat()
    if sample:
        records = [
            {
                "id": c,
                "symbol": c[:3],
                "name": c.title(),
                "market_cap_rank": i + 1,
                "circulating_supply": 1_000_000.0,
                "total_supply": 2_000_000.0,
                "ath": 100.0,
                "ath_date": "2025-01-01T00:00:00.000Z",
            }
            for i, c in enumerate(config.COINS)
        ]
    else:
        records = client.coins_markets(config.COINS)

    df = pd.DataFrame(records)[
        [
            "id", "symbol", "name", "market_cap_rank",
            "circulating_supply", "total_supply", "ath", "ath_date",
        ]
    ].rename(columns={"id": "coin_id"})
    df["_loaded_at"] = loaded_at

    config.RAW_COINS_DIR.mkdir(parents=True, exist_ok=True)
    fname = datetime.now(timezone.utc).strftime("coins_%Y%m%dT%H%M%SZ.parquet")
    df.to_parquet(config.RAW_COINS_DIR / fname, index=False)
    logger.info("Landed %s coin metadata rows -> %s", len(df), fname)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", action="store_true", help="generate synthetic data offline")
    args = parser.parse_args()

    client = None if args.sample else CoinGeckoClient()
    ingest_prices(client, sample=args.sample)
    ingest_coin_metadata(client, sample=args.sample)


if __name__ == "__main__":
    main()
