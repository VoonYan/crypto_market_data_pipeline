-- Type and clean coin metadata snapshots. All snapshots are kept
-- (point-in-time history); the current view is derived in dim_coin.

with source as (

    select * from {{ source('coingecko', 'coins') }}

)

select
    cast(coin_id as varchar)              as coin_id,
    upper(cast(symbol as varchar))        as symbol,
    cast(name as varchar)                 as coin_name,
    cast(market_cap_rank as integer)      as market_cap_rank,
    cast(circulating_supply as double)    as circulating_supply,
    cast(total_supply as double)          as total_supply,
    cast(ath as double)                   as ath_usd,
    cast(ath_date as timestamp)           as ath_at,
    cast(_loaded_at as timestamp)         as loaded_at
from source
