Update tenant
set status = 'APPROVED'
set approvedBy = {{user_id}}
where id = {{tenant_id}};