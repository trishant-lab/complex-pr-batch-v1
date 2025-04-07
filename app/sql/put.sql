UPDATE {{ table | sqlsafe }}
SET
{% for col, val in payload.items() %}
{% if val is iterable and (val is not string and val is not mapping) %}
    {% if val|length == 0 %}
        {{col | sqlsafe}} = '{}' {% if not loop.last %}, {% endif %}
    {% else %}
        {{col | sqlsafe}} = {{ val | inclause }} {% if not loop.last %}, {% endif %}
    {% endif %}
{% else %}
    {{ col | sqlsafe}} = {{ val }} {% if not loop.last %}, {% endif %}
{% endif %}
{% endfor %}
WHERE {{ where | sqlsafe}}
{% if returning %}
RETURNING  {{ returning | default('*') | join (',') | sqlsafe }}
{% endif %};
