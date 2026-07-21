SELECT s.id,
       s.plancode
FROM subscription s
JOIN customer c
    ON c.id = s.customerid
WHERE c.tenantname = {{ tenant_name }}
    AND c.product = LOWER({{ product }})
    AND s.name = 'Active Subscription';
