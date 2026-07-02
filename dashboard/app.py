"""Streamlit dashboard reading the exported analytics marts.

Run locally:  streamlit run dashboard/app.py
Deploys as-is to Streamlit Community Cloud (reads committed parquet marts).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

MARTS_DIR = Path(__file__).resolve().parents[1] / "data" / "marts"

st.set_page_config(page_title="Crypto Market Pipeline", layout="wide")


@st.cache_data(ttl=3600)
def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(MARTS_DIR / f"{name}.parquet")


dim_coin = load("dim_coin")
ohlcv = load("fct_daily_ohlcv")
metrics = load("fct_coin_metrics")
corrs = load("fct_coin_correlations")

st.title("Crypto Market Data Pipeline")
st.caption(
    "Analytics marts produced by an incremental ELT pipeline: "
    "CoinGecko API → parquet landing → DuckDB + dbt → this dashboard. "
    f"Data through {ohlcv['price_date'].max()}."
)

coins = sorted(ohlcv["coin_id"].unique())
default_ix = coins.index("bitcoin") if "bitcoin" in coins else 0
coin = st.sidebar.selectbox("Coin", coins, index=default_ix)
st.sidebar.markdown(f"**Coins tracked:** {len(coins)}")
st.sidebar.markdown(f"**Daily candles:** {len(ohlcv):,}")

# --- KPI row -----------------------------------------------------------------
m = metrics[metrics["coin_id"] == coin].sort_values("price_date")
latest = m.iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Close (USD)", f"{latest['close_usd']:,.2f}",
          f"{latest['daily_return']:+.2%}" if pd.notna(latest["daily_return"]) else None)
c2.metric("30d volatility (ann.)", f"{latest['volatility_30d_ann']:.1%}"
          if pd.notna(latest["volatility_30d_ann"]) else "–")
c3.metric("Drawdown from peak", f"{latest['drawdown_from_peak']:.1%}")
c4.metric("Volume (24h, USD)", f"{latest['volume_usd']:,.0f}")

# --- Candlestick + MAs ---------------------------------------------------------
o = ohlcv[(ohlcv["coin_id"] == coin) & ohlcv["is_complete_day"]].sort_values("price_date")
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=o["price_date"], open=o["open_usd"], high=o["high_usd"],
    low=o["low_usd"], close=o["close_usd"], name="OHLC",
))
fig.add_trace(go.Scatter(x=m["price_date"], y=m["ma_7d"], name="MA 7d", line=dict(width=1)))
fig.add_trace(go.Scatter(x=m["price_date"], y=m["ma_30d"], name="MA 30d", line=dict(width=1)))
fig.update_layout(title=f"{coin} — daily OHLC with moving averages",
                  xaxis_rangeslider_visible=False, height=450)
st.plotly_chart(fig, use_container_width=True)

# --- Volatility + drawdown -------------------------------------------------------
left, right = st.columns(2)
with left:
    vfig = px.line(m, x="price_date", y=["volatility_7d_ann", "volatility_30d_ann"],
                   title="Rolling volatility (annualized)")
    vfig.update_layout(height=350, legend_title=None)
    st.plotly_chart(vfig, use_container_width=True)
with right:
    dfig = px.area(m, x="price_date", y="drawdown_from_peak", title="Drawdown from running peak")
    dfig.update_layout(height=350, yaxis_tickformat=".0%")
    st.plotly_chart(dfig, use_container_width=True)

# --- Correlation heatmap ---------------------------------------------------------
st.subheader("30-day return correlations (latest)")
latest_date = corrs["price_date"].max()
snap = corrs[corrs["price_date"] == latest_date]
matrix = pd.concat([
    snap.rename(columns={"base_coin_id": "a", "quote_coin_id": "b"})[["a", "b", "corr_30d"]],
    snap.rename(columns={"quote_coin_id": "a", "base_coin_id": "b"})[["a", "b", "corr_30d"]],
]).pivot(index="a", columns="b", values="corr_30d")
hfig = px.imshow(matrix, zmin=-1, zmax=1, color_continuous_scale="RdBu_r", aspect="auto")
hfig.update_layout(height=500, xaxis_title=None, yaxis_title=None)
st.plotly_chart(hfig, use_container_width=True)

st.caption("Source: CoinGecko API · Pipeline: Python + DuckDB + dbt · Refreshed daily by GitHub Actions")
