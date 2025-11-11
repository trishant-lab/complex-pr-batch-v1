UPDATE spaces
SET status = {{ status }},
    errors = {{ errors }}::jsonb,
    lastupdated = NOW()
WHERE spacename = {{ spacename }}
  AND customerid = (
    SELECT c.id
    FROM customer c
    WHERE c.tenantname = {{ tenant_name }}
      AND c.product = LOWER({{ product }})
  );

