SELECT 
    c.*,
    c.schema as form_schema,
    c.data as form_data,
    s.plancode
FROM
    customer c
JOIN
    subscription s
ON
    c.id = s.customerid
WHERE
    c.email = {{ email }} AND
    s.name = 'Active Subscription' AND
    c.product = LOWER({{ product }})
;