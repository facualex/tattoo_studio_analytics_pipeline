-- Local dev source: reads the Parquet file written by
-- ingest/sheets_extractor.py. Swap for a source() against raw/ once
-- querying through Athena instead of DuckDB.
with source as (
    select *
    from read_parquet('{{ var("raw_data_dir") }}/tatuajes.parquet')
)

select
    "Nombre"                                       as client_name,
    "RUT"                                          as client_rut,
    "Comuna"                                       as client_comuna,
    "Teléfono"                                     as client_phone,
    "IG"                                           as client_instagram,
    "Mail"                                         as client_email,
    "Tatuaje"                                      as tattoo_description,
    "Zona"                                         as body_zone,
    try_strptime(nullif("Fecha tattoo", ''), '%d/%m/%Y')::date as tattoo_date,
    nullif(replace("Precio ($)", ',', ''), '')::double as price_clp,
    "Método de Pago"                               as payment_method,
    "Lugar / Modalidad"                            as location_type,
    "Estilo"                                       as style,
    "Tipo Cliente"                                 as client_type,
    "Canal Adquisición"                            as acquisition_channel,
    "Notas"                                        as notes
from source
where "Nombre" is not null and "Nombre" != ''
