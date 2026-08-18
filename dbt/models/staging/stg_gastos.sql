with source as (
    select *
    from read_parquet('{{ var("raw_data_dir") }}/gastos.parquet')
)

select
    try_strptime(nullif("Fecha", ''), '%d/%m/%Y')::date as expense_date,
    "Negocio"                                   as business,
    "Descripción"                               as description,
    "Categoría"                                 as category,
    nullif(replace("Monto ($)", ',', ''), '')::double as amount_clp,
    "Método de Pago"                            as payment_method,
    "Notas"                                     as notes
from source
where "Fecha" is not null and "Fecha" != ''
