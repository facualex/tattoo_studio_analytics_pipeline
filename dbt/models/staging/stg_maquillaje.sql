with source as (
    select *
    from read_parquet('{{ var("raw_data_dir") }}/maquillaje.parquet')
)

select
    "Nombre"                                    as client_name,
    try_strptime(nullif("Fecha", ''), '%d/%m/%Y')::date as booking_date,
    nullif(replace("Precio ($)", ',', ''), '')::double as price_clp,
    "Lugar"                                     as location,
    "Estilo"                                    as style,
    "Notas"                                     as notes
from source
where "Nombre" is not null and "Nombre" != ''
