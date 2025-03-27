SELECT schema as product_schema
FROM product
WHERE name = LOWER({{product}});