UPDATE product
SET
    schema = {{product_schema}}
WHERE
    name = {{product_name}};