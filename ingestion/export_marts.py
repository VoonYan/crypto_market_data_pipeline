"""Export mart tables from the DuckDB warehouse to parquet.

The warehouse file is gitignored (it's derivable), but the exported marts are
committed so the Streamlit dashboard — and anyone cloning the repo — can use
the analytics tables without running the pipeline.
"""
from __future__ import annotations

import logging

import duckdb

from . import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MARTS = ["dim_coin", "fct_daily_ohlcv", "fct_coin_metrics", "fct_coin_correlations"]


def main() -> None:
    config.MARTS_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(config.WAREHOUSE_PATH), read_only=True)
    for mart in MARTS:
        out = config.MARTS_EXPORT_DIR / f"{mart}.parquet"
        con.execute(f"COPY (SELECT * FROM marts.{mart}) TO '{out.as_posix()}' (FORMAT PARQUET)")
        n = con.execute(f"SELECT count(*) FROM marts.{mart}").fetchone()[0]
        logger.info("Exported %s (%s rows) -> %s", mart, n, out.name)
    con.close()


if __name__ == "__main__":
    main()
