{#
    Both the arte and maquillaje sheets carry one scaffold row per
    calendar month (e.g. "Nombre" = "Enero") as a template/reminder row
    rather than a real client. Shared here so the month list isn't
    duplicated across stg_arte and stg_maquillaje.
#}
{% macro is_calendar_month_name(column) %}
    lower({{ column }}) in (
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
    )
{% endmacro %}
