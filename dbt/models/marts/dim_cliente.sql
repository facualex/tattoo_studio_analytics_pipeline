-- One row per client, ready for the dashboard's loyalty/churn views.
-- Thin pass-through over int_segmentacion_clientes — see that model for
-- how visit_tier and recency_status are derived.

select
    client_name,
    total_visits,
    paid_visits,
    total_revenue_clp,
    avg_ticket_clp,
    first_transaction_date,
    last_transaction_date,
    days_since_last_transaction,
    visit_tier,
    recency_status
from {{ ref('int_segmentacion_clientes') }}
