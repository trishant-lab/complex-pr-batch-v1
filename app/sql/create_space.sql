INSERT INTO spaces (spacename, customerid, email, status, errors, lastupdated)
SELECT
    {{ spacename }},
    c.id,
    COALESCE(c.email, ''),
    {{ status }},
    {{ errors }}::jsonb,
    NOW()
FROM
    customer c
WHERE
    c.tenantname = {{ tenant_name }} AND c.product = LOWER({{ product }});