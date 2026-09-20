-- One row per client (by client_name — there's no unified client_id
-- across the three sheets, see the data-quality card), aggregated across
-- all three business lines via int_sales_unioned. Feeds dim_cliente.
--
-- Thresholds below aren't round-number guesses: they're read off the
-- actual gap-between-visits distribution for repeat tattoo clients in
-- this dataset (median ~28 days, p75 ~140 days, p90 ~359 days). Rounding
-- p75 up to 180 days and p90 up to 365 days gives three bands with a
-- real client in each, rather than thresholds tuned for a business with
-- a different visit cadence (e.g. a subscription or retail cadence).

with client_activity as (
    select
        client_name,
        count(*)                                            as total_visits,
        count(*) filter (where price_clp > 0)               as paid_visits,
        sum(price_clp)                                       as total_revenue_clp,
        avg(price_clp) filter (where price_clp > 0)           as avg_ticket_clp,
        min(transaction_date)                                as first_transaction_date,
        max(transaction_date)                                as last_transaction_date
    from {{ ref('int_sales_unioned') }}
    group by client_name
)

select
    client_name,
    total_visits,
    paid_visits,
    total_revenue_clp,
    avg_ticket_clp,
    first_transaction_date,
    last_transaction_date,
    date_diff('day', last_transaction_date, current_date) as days_since_last_transaction,
    case
        when total_visits >= 5 then 'loyal'
        when total_visits >= 2 then 'returning'
        else 'new'
    end as visit_tier,
    case
        when date_diff('day', last_transaction_date, current_date) <= 180 then 'active'
        when date_diff('day', last_transaction_date, current_date) <= 365 then 'at_risk'
        else 'lapsed'
    end as recency_status
from client_activity
