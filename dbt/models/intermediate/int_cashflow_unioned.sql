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
)

select * from expenses
union all
select * from withdrawals
