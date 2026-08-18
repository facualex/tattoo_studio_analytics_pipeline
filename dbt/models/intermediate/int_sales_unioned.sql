-- Unions the three revenue-generating sheets (tattoos, art, makeup) into
-- one transaction grain. They're the same business event — a client
-- paying for a service — just recorded in separate sheets, so this is
-- built once here instead of re-unioned in every downstream mart
-- (fct_revenue, dim_clients, etc.) that needs "all client transactions".

with tattoo_sales as (
    select
        'tattoo'             as business_line,
        client_name,
        tattoo_date          as transaction_date,
        tattoo_description   as description,
        style,
        location_type        as location,
        payment_method,
        price_clp,
        notes
    from {{ ref('stg_tatuajes') }}
),

art_sales as (
    select
        'art'                as business_line,
        client_name,
        sale_date            as transaction_date,
        artwork_description  as description,
        style,
        cast(null as varchar) as location,
        cast(null as varchar) as payment_method,
        price_clp,
        notes
    from {{ ref('stg_arte') }}
),

makeup_sales as (
    select
        'makeup'             as business_line,
        client_name,
        booking_date         as transaction_date,
        cast(null as varchar) as description,
        style,
        location,
        cast(null as varchar) as payment_method,
        price_clp,
        notes
    from {{ ref('stg_maquillaje') }}
)

select * from tattoo_sales
union all
select * from art_sales
union all
select * from makeup_sales
