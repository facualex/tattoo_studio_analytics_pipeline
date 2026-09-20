-- Unions expenses and owner withdrawals into one cash-outflow grain, the
-- same way int_sales_unioned does for revenue. A margin/P&L mart needs
-- both sides of cashflow (money in vs. money out) unioned once rather
-- than joining gastos + retiros separately in each mart that needs it.
-- Amounts stay positive here (as recorded) — sign convention for netting
-- against revenue is a mart-layer decision, not this layer's job.

with expenses as (
    select
        'expense'      as cashflow_type,
        business,
        expense_date   as transaction_date,
        description,
        category,
        payment_method,
        amount_clp,
        notes
    from {{ ref('stg_gastos') }}
),

withdrawals as (
    select
        'withdrawal'   as cashflow_type,
        business,
        withdrawal_date as transaction_date,
        concept        as description,
        reason         as category,
        payment_method,
        amount_clp,
        notes
    from {{ ref('stg_retiros') }}
),

unioned as (
    select * from expenses
    union all
    select * from withdrawals
)

-- business_line normalizes the free-text "Negocio" column (as entered in
-- Sheets, e.g. "Tatuajes") into the same tattoo/art/makeup keys
-- int_sales_unioned hardcodes for business_line, so marts can join both
-- fact families to one dim_negocio without duplicating this mapping.
select
    *,
    case lower(trim(business))
        when 'tatuajes'   then 'tattoo'
        when 'arte'       then 'art'
        when 'maquillaje' then 'makeup'
        else lower(trim(business))
    end as business_line
from unioned
