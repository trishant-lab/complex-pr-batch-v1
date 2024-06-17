SELECT {{ columns | default ('*') | join (',') | sqlsafe }}

FROM {{ table | sqlsafe }}

{% if join_table and join_on %}
JOIN {{ join_table | sqlsafe }} ON {{ join_on | sqlsafe }}
{% endif %}

{% if where %}
WHERE {{ where | sqlsafe }}
{% endif %}

{% if groupby %}
group by {{ groupby | join (',') | sqlsafe }}
{% endif %}

{% if orderby %}
order by {{ orderby | join (',') | sqlsafe }}
{% endif %}

{% if desc %}
DESC
{% endif %}

{% if offset %}
OFFSET {{ offset |sqlsafe }}
{% endif %}

{% if limit %}
LIMIT  {{ limit |sqlsafe }}
{% endif %}
;
