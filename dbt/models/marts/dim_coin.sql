-- Current coin dimension: latest metadata snapshot per coin.

with snapshots as (

    select * from {{ ref('stg_coingecko__coins') }}

),

latest as (

    select
        *,
        row_number() over (
            partition by coin_id
            order by loaded_at desc
        ) as rn
    from snapshots

)

select
    coin_id,
    symbol,
    coin_name,
    market_cap_rank,
    circulating_supply,
    total_supply,
    ath_usd,
    ath_at,
    loaded_at as snapshot_at
from latest
where rn = 1
