SELECT
*,
c."approvedBy"
FROM customer c JOIN operatorstatus os ON c.id = os.customerid
where product = LOWER({{ product }})
{% if tenant_id %}
    and c.id = {{tenant_id}};
{% endif %}
;