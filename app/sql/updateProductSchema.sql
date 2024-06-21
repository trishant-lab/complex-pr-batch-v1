UPDATE product
SET
    schema = {{product_schema}}
WHERE
    id = {{product_id}};