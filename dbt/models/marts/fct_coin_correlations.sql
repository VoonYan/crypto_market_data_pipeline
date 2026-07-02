-- Pairwise 30-day rolling correlation of daily log returns between coins.
-- Grain: one row per (base_coin, quote_coin, date), base < quote to avoid
-- duplicate mirrored pairs.

with metrics as (

    select
        coin_id,
        price_date,
        daily_log_return
    from {{ ref('fct_coin_metrics') }}
    where daily_log_return is not null

),

pairs as (

    select
        a.coin_id            as base_coin_id,
        b.coin_id            as quote_coin_id,
        a.price_date,
        a.daily_log_return   as base_return,
        b.daily_log_return   as quote_return
    from metrics a
    join metrics b
      on a.price_date = b.price_date
     and a.coin_id < b.coin_id

),

rolling as (

    select
        base_coin_id,
        quote_coin_id,
        price_date,
        corr(base_return, quote_return) over (
            partition by base_coin_id, quote_coin_id
            order by price_date
            rows between 29 preceding and current row
        )                                        as corr_30d,
        count(*) over (
            partition by base_coin_id, quote_coin_id
            order by price_date
            rows between 29 preceding and current row
        )                                        as n_obs
    from pairs

)

select
    base_coin_id,
    quote_coin_id,
    price_date,
    corr_30d,
    n_obs
from rolling
where n_obs >= 15  -- require a minimum window before trusting the estimate
