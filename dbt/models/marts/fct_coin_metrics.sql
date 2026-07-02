-- Analytics mart: per-coin daily metrics built with window functions.
-- Rebuilt as a table each run (windowed metrics need full history, so this
-- model is intentionally NOT incremental — cheap on this data volume).
--
-- Only complete days are included so rolling metrics aren't skewed by the
-- partial current day.

with daily as (

    select * from {{ ref('fct_daily_ohlcv') }}
    where is_complete_day

),

returns as (

    select
        coin_id,
        price_date,
        close_usd,
        volume_usd,
        market_cap_usd,
        close_usd / nullif(lag(close_usd) over w, 0) - 1          as daily_return,
        ln(close_usd / nullif(lag(close_usd) over w, 0))          as daily_log_return
    from daily
    window w as (partition by coin_id order by price_date)

),

metrics as (

    select
        coin_id,
        price_date,
        close_usd,
        volume_usd,
        market_cap_usd,
        daily_return,
        daily_log_return,

        -- moving averages
        avg(close_usd) over (
            partition by coin_id order by price_date
            rows between 6 preceding and current row
        )                                                          as ma_7d,
        avg(close_usd) over (
            partition by coin_id order by price_date
            rows between 29 preceding and current row
        )                                                          as ma_30d,

        -- rolling volatility (stddev of log returns, annualized: crypto trades 365d)
        stddev_samp(daily_log_return) over (
            partition by coin_id order by price_date
            rows between 6 preceding and current row
        ) * sqrt(365)                                              as volatility_7d_ann,
        stddev_samp(daily_log_return) over (
            partition by coin_id order by price_date
            rows between 29 preceding and current row
        ) * sqrt(365)                                              as volatility_30d_ann,

        -- drawdown from running peak
        close_usd / nullif(
            max(close_usd) over (
                partition by coin_id order by price_date
                rows between unbounded preceding and current row
            ), 0
        ) - 1                                                      as drawdown_from_peak

    from returns

)

select * from metrics
