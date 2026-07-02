{% test positive_value(model, column_name) %}

-- Custom generic test: fails on any non-positive value.
select *
from {{ model }}
where {{ column_name }} <= 0

{% endtest %}
