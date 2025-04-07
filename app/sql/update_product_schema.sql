UPDATE product
SET
    schema = {{product_schema}}
WHERE
    name = LOWER({{product_name}});