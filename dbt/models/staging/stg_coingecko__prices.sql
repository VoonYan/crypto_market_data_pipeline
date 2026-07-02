-- Clean and deduplicate raw hourly price points.
-- Raw files are append-only, so overlapping load windows can produce
-- duplicate (coin, hour) rows: keep the most recently loaded one.

with source as (

    select * from {{ source('coingecko', 'prices') }}

),

typed as (

    select
        cast(coin_id as varchar)                            as coin_id,
        to_timestamp(ts_ms / 1000)                          as price_at,
        cast(price_usd as double)                           as price_usd,
        cast(market_cap_usd as double)                      as market_cap_usd,
        cast(volume_24h_usd as double)                      as volume_24h_usd,
        cast(_loaded_at as timestamp)                       as loaded_at
    from source
    where price_usd is not null
      and price_usd > 0

),

deduped as (

    select
        *,
        row_number() over (
            partition by coin_id, price_at
            order by loaded_at desc
        ) as rn
    from typed

)

select
    coin_id,
    price_at,
    price_usd,
    market_cap_usd,
    volume_24h_usd,
    loaded_at
from deduped
where rn = 1
