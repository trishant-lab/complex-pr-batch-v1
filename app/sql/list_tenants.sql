SELECT
*,
c."approvedBy"
FROM customer c JOIN provisioningstatus p ON c.id = p.customerid
where product = LOWER({{ product }})
{% if tenant_id %}
    and c.id = {{tenant_id}};
{% endif %}
;