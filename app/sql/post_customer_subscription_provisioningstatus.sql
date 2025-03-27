WITH customer_insert AS (
    INSERT INTO customer (tenantname, setupintent, email, orgname, data, product, schema)
    VALUES (
        {{customer['tenantname']}}, 
        {{customer['setupintent']}}, 
        {{customer['email']}}, 
        {{customer['orgname']}}, 
        {{customer['data']}}, 
        LOWER({{customer['product']}}),
        (SELECT schema FROM product WHERE name = LOWER({{customer['product']}}))
    )
    RETURNING id
),
subscription_insert AS (
    INSERT INTO subscription (customerid, name, plancode, product)
    VALUES ( (select id from customer_insert) , {{subscription['name']}}, {{subscription['plancode']}}, LOWER({{customer['product']}}))
    RETURNING id
)
INSERT INTO provisioningstatus (customerid, status, errors)
VALUES ( (select id from customer_insert) , {{provisioningstatus['status']}}, {{provisioningstatus['errors']}})
RETURNING customerid;
