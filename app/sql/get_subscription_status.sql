SELECT 
    c.*,
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
    c.product = {{ product }}
;