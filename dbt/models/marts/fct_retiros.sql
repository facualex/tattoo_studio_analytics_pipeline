-- Grain: one row per owner withdrawal. Same shape and FKs as fct_gastos
-- (business_line, transaction_date) — kept as a separate mart from
-- fct_gastos because withdrawals aren't a business expense: mixing them
-- into one table would silently overstate the P&L expense line.

select
    business_line,
    business as business_raw,
    transaction_date,
    description,
    category,
    payment_method,
    amount_clp,
    notes
from {{ ref('int_cashflow_unioned') }}
where cashflow_type = 'withdrawal'
