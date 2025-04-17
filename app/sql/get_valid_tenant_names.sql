Select tenantname FROM customer
WHERE tenantname IN (
    {% for tenant in tenant_names %}
        LOWER({{ tenant }}) {% if not loop.last %},{% endif %}
    {% endfor %}
) 
AND product = LOWER({{ product }})
{% if email %}
    AND email != {{ email }}
{% endif %}
;