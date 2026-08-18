with source as (
    select *
    from read_parquet('{{ var("raw_data_dir") }}/arte.parquet')
)

select
    "Nombre"                                    as client_name,
    try_strptime(nullif("Fecha", ''), '%d/%m/%Y')::date as sale_date,
    "Cuadro"                                    as artwork_description,
    nullif(replace("Precio ($)", ',', ''), '')::double as price_clp,
    "Estilo"                                    as style,
    "Notas"                                     as notes
from source
where "Nombre" is not null and "Nombre" != ''
