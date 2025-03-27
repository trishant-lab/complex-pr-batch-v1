SELECT *
FROM customer
WHERE tenantname = {{tenant_name}} and product = LOWER({{ product }});