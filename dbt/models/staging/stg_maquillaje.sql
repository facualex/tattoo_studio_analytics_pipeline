-- Same scaffold-row pattern as arte (see stg_arte.sql): one placeholder
-- row per calendar month gets dropped, but real bookings with an
-- unusable name (blank, or a month) are kept under client_name =
-- 'unknown' rather than losing the revenue. See the data-quality Trello
-- card.

with source as (
    select *
    from read_parquet('{{ var("raw_data_dir") }}/maquillaje.parquet')
),

parsed as (
    select
        nullif(trim("Nombre"), '')                           as raw_client_name,
        try_strptime(nullif("Fecha", ''), '%d/%m/%Y')::date   as booking_date,
        nullif(replace("Precio ($)", ',', ''), '')::double    as price_clp,
        nullif("Lugar", '')                                   as location,
        "Estilo"                                              as style,
        "Notas"                                                as notes
    from source
),

flagged as (
    select
        *,
        raw_client_name is null or {{ is_calendar_month_name('raw_client_name') }} as has_unusable_name
    from parsed
)

select
    case when has_unusable_name then 'unknown' else raw_client_name end as client_name,
    booking_date,
    price_clp,
    location,
    style,
    notes
from flagged
where not has_unusable_name
   or coalesce(price_clp, 0) > 0
   or location is not null
