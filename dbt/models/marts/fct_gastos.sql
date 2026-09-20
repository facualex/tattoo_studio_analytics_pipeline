-- Grain: one row per business expense. FKs to dim_negocio (business_line)
-- and dim_fecha (transaction_date). amount_clp stays positive (as
-- recorded) — netting against revenue for a margin view is a
-- downstream/BI-layer decision, not this model's job.

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
where cashflow_type = 'expense'
