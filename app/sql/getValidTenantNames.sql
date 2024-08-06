Select name FROM tenant
WHERE name in ({tenant_name_clause})
AND product = (SELECT id from product where lower(name) = {{product | lower}});