UPDATE tenant
SET name = {{tenant_name}}
, schema = {{product_schema}}
where id = {{tenant_id}};