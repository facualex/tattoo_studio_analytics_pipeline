-- Calendar date spine. Bounds are derived from the data itself (not
-- hardcoded) so it always covers every fact row, plus a year of runway
-- past the latest known date or today (whichever is later) so upcoming
-- dashboard periods don't fall outside the dimension.

with bounds as (
    select
        least(
            (select min(transaction_date) from {{ ref('int_sales_unioned') }}),
            (select min(transaction_date) from {{ ref('int_cashflow_unioned') }})
        ) as min_date,
        greatest(
            (select max(transaction_date) from {{ ref('int_sales_unioned') }}),
            (select max(transaction_date) from {{ ref('int_cashflow_unioned') }}),
            current_date
        ) + interval 365 day as max_date
),

date_spine as (
    select unnest(generate_series(
        (select min_date from bounds),
        (select max_date from bounds)::date,
        interval 1 day
    ))::date as date_day
)

select
    date_day,
    extract(year from date_day)                          as year,
    extract(quarter from date_day)                        as quarter,
    extract(month from date_day)                          as month,
    strftime(date_day, '%B')                              as month_name,
    strftime(date_day, '%Y-%m')                            as year_month,
    extract(day from date_day)                            as day_of_month,
    extract(dow from date_day)                             as day_of_week,
    strftime(date_day, '%A')                              as day_name,
    extract(dow from date_day) in (0, 6)                   as is_weekend
from date_spine
