-- Daily OHLCV fact table with returns. INCREMENTAL: on each run only the
-- last few days are reprocessed (3-day lookback handles late-arriving hourly
-- points and the previously-partial current day) and merged on the unique key.

{{
    config(
        materialized='incremental',
        unique_key=['coin_id', 'price_date'],
        incremental_strategy='delete+insert'
    )
}}

with daily as (

    select * from {{ ref('int_prices__daily_ohlcv') }}

    {% if is_incremental() %}
    where price_date >= (
        select coalesce(max(price_date), '1900-01-01') - interval 3 day
        from {{ this }}
    )
    {% endif %}

),

with_returns as (

    select
        coin_id,
        price_date,
        open_usd,
        high_usd,
        low_usd,
        close_usd,
        volume_usd,
        market_cap_usd,
        n_hourly_points,
        -- a day is complete when (almost) all 24 hourly points arrived
        n_hourly_points >= 20                                     as is_complete_day,
        close_usd / nullif(open_usd, 0) - 1                       as intraday_return,
        (high_usd - low_usd) / nullif(open_usd, 0)                as intraday_range_pct
    from daily

)

select * from with_returns
