WITH customer_insert AS (
    INSERT INTO customer (orgname, tenantname, email, data, product, schema, source, "approvedBy")
    VALUES (
        {{ orgname }}, 
        {{ tenantname }}, 
        {{ email }}, 
        {{ schema_ }}, 
        {{product}},
        {{product_schema}},
        {{source}},
        {{approvedBy}}
    )
    RETURNING id
),
operator_insert AS (
    INSERT INTO operatorstatus (customerid, status, errors)
    VALUES ( (select id from customer_insert) , {{ status }}, {{errors}})
    RETURNING customerid
)
SELECT customerid as id FROM operator_insert;