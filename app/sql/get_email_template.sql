SELECT * from emailtemplates
    WHERE product = {{product}}
{% if template_id %}
    AND id = {{template_id}}
{% endif %}