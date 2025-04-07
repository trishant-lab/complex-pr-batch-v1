UPDATE emailtemplates
SET template = {{template}},
    subject = {{subject}}
WHERE product = LOWER({{product}})
{% if id %}
    AND id = {{id}}
{% endif %}
;