UPDATE tenant
SET status = {{status}},
    errors = {{error_message}}
WHERE name = {{tenant_name}} and product = (SELECT id from product where name = {{product}});