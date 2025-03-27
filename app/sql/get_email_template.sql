SELECT * from emailtemplates
    WHERE product = LOWER({{product}})
{% if template_id %}
    AND id = {{template_id}}
{% endif %}