INSERT INTO {{ table | sqlsafe }} (
    {% for col in payload.keys() %}
        {{ col | sqlsafe }} {% if not loop.last %}, {% endif %}
    {% endfor %}
)
VALUES (
    {% for column, val in payload.items() %}
    {% if val is iterable and (val is not string and val is not mapping) %}
        {% if val | length == 0 %}
            '{}' {% if not loop.last %}, {% endif %}
        {% else %}
            {{ val | inclause }} {% if not loop.last %}, {% endif %}
        {% endif %}
    {% else %}
        {{ val }} {% if not loop.last %}, {% endif %}
    {% endif %}
    {% endfor %}
)
{% if returning %}
RETURNING  {{ returning | default('*') | join (',') | sqlsafe }}
{% endif %};
