UPDATE email_templates
SET template = {{template}}
WHERE product = (SELECT id FROM product WHERE name = {{product | lower}})
{% if template_id %}
    AND id = {{template_id}}
{% endif %}