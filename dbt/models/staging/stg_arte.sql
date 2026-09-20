-- Arte carries one scaffold row per calendar month (e.g. "Nombre" =
-- "Enero", $0, no artwork) as a sheet template, not a real sale — those
-- get dropped. But 2 real sales ($200k "Junio", $150k "Julio") were
-- recorded under the placeholder's month name instead of a client, and 2
-- more have a real artwork/price with no name at all. Losing that
-- revenue would be worse than losing name accuracy, so real rows with an
-- unusable name are kept under client_name = 'unknown' rather than
-- dropped. See the data-quality Trello card.

with source as (
    select *
    from read_parquet('{{ var("raw_data_dir") }}/arte.parquet')
),

parsed as (
    select
        nullif(trim("Nombre"), '')                          as raw_client_name,
        try_strptime(nullif("Fecha", ''), '%d/%m/%Y')::date  as sale_date,
        nullif("Cuadro", '')                                 as artwork_description,
        nullif(replace("Precio ($)", ',', ''), '')::double   as price_clp,
        "Estilo"                                              as style,
        "Notas"                                               as notes
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
    sale_date,
    artwork_description,
    price_clp,
    style,
    notes
from flagged
where not has_unusable_name
   or coalesce(price_clp, 0) > 0
   or artwork_description is not null
