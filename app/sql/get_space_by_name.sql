SELECT s.spacename, s.status
FROM spaces s
JOIN customer c ON s.customerid = c.id
WHERE s.spacename = {{ spacename }}
  AND c.tenantname = {{ tenant_name }}
  AND c.product = LOWER({{ product }});
