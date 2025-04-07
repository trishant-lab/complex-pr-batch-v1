SELECT c.*, p.*
FROM customer c
JOIN provisioningstatus p ON c.id = p.customerid
WHERE c.id = {{tenant_id}};