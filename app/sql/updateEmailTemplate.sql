UPDATE email_templates
SET template = {{template}},
    subject = {{subject}}
WHERE product = (SELECT id FROM product WHERE name = {{product | lower}})
{% if template_id %}
    AND id = {{template_id}}
{% endif %}