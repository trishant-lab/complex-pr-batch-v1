SELECT s.spacename, s.status, s.created, s.lastupdated, c.tenantname, 
COALESCE(c.orgname, '') as orgname, COALESCE(c.email, '') as email
FROM spaces s
JOIN customer c ON s.customerid = c.id
WHERE c.product = LOWER({{ product }}) 
{% if tenant_id %}
    AND c.id = {{tenant_id}}
{% endif %}
;