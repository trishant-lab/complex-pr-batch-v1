SELECT
*
, (SELECT name from product where id = product) as product_name
FROM
tenant
WHERE id = {{tenant_id}}