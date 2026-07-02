-- Aggregate hourly price points into daily OHLCV candles.
--
-- open/close: first/last hourly price of the UTC day
-- high/low:   max/min hourly price of the UTC day
-- volume:     24h-rolling volume at day close (CoinGecko reports rolling
--             volume, not per-hour traded volume, so day-close snapshot
--             is the least-wrong daily figure)

with hourly as (

    select * from {{ ref('stg_coingecko__prices') }}

),

daily as (

    select
        coin_id,
        cast(price_at as date)                                          as price_date,
        arg_min(price_usd, price_at)                                    as open_usd,
        max(price_usd)                                                  as high_usd,
        min(price_usd)                                                  as low_usd,
        arg_max(price_usd, price_at)                                    as close_usd,
        arg_max(volume_24h_usd, price_at)                               as volume_usd,
        arg_max(market_cap_usd, price_at)                               as market_cap_usd,
        count(*)                                                        as n_hourly_points
    from hourly
    group by 1, 2

)

select * from daily
