DELETE FROM {{ table | sqlsafe }}
WHERE {{ where | sqlsafe }}
{% if returning %}
RETURNING  {{ returning | default('*') | join (',') | sqlsafe }}
{% endif %};