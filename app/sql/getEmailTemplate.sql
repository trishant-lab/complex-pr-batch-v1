SELECT * from email_templates
    WHERE product = (SELECT id FROM product WHERE name = {{product | lower}})
{% if template_id %}
    AND id = {{template_id}}
{% endif %}