SELECT id
FROM subscription
WHERE customerid = {{ customer_id }}
    AND product = LOWER({{ product }})
    AND name = {{ name }}
ORDER BY created
LIMIT 1;
