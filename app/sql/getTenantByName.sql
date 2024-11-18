SELECT
*
, (SELECT name from product where id = product) as product_name
FROM
tenant
WHERE name = {{tenant_name}} and product = (SELECT id from product where lower(name) = {{product | lower}})
