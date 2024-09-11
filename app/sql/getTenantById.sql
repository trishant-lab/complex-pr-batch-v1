SELECT
*
, (
    SELECT jsonb_build_object('id', id, 'username', username, 'email', email, 'organization', organization)
        FROM requestor where id = tenant.requestor
  ) as requestor_details
FROM tenant
where tenant.id = {{tenant_id}};