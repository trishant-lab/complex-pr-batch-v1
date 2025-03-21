UPDATE customer
SET tenantname = {{tenant_name}}
, schema = {{product_schema}}
where id = {{tenant_id}};