SELECT * from emailtemplates
    WHERE product = LOWER({{product}})
{% if id %}
    AND id = {{id}}
{% endif %}
{% if name %}
    AND name = {{name}}
{% endif %}