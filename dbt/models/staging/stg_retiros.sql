with source as (
    select *
    from read_parquet('{{ var("raw_data_dir") }}/retiros.parquet')
)

select
    try_strptime(nullif("Fecha", ''), '%d/%m/%Y')::date as withdrawal_date,
    "Negocio"                                   as business,
    "Concepto"                                  as concept,
    nullif(replace("Monto ($)", ',', ''), '')::double as amount_clp,
    "Motivo"                                    as reason,
    "Método"                                    as payment_method,
    "Notas"                                     as notes
from source
where "Fecha" is not null and "Fecha" != ''
