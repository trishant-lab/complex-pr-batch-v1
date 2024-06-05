Update tenant
set status = {{status}}
, approvedby = {{user_id}}
where id = {{tenant_id}};