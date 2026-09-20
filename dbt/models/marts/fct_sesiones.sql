-- Grain: one row per revenue-generating transaction (tattoo session, art
-- sale, or makeup booking). FKs to dim_cliente (client_name),
-- dim_negocio (business_line) and dim_fecha (transaction_date);
-- description/style/location/payment_method stay inline as degenerate
-- dimensions since none of them warrant their own dimension table yet.
--
-- is_zero_price surfaces the ~40% of rows recorded at $0 (mostly missing
-- price input, a smaller share genuine trades — see the data quality
-- card) so consumers can filter them out of revenue/ticket metrics with
-- one flag instead of remembering to check price_clp = 0.
--
-- transaction_date is null on 10 rows (real revenue, missing date input
-- in Sheets) — see the not_null test on this column in _marts.yml for
-- why it's a warning, not a build failure.

select
    business_line,
    client_name,
    transaction_date,
    description,
    style,
    location,
    payment_method,
    price_clp,
    price_clp = 0 as is_zero_price,
    notes
from {{ ref('int_sales_unioned') }}
