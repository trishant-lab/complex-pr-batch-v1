SELECT
*
, (
    SELECT jsonb_build_object('id', id, 'username', username, 'email', email, 'organization', organization)
        FROM requestor where id = tenant.requestor
  ) as requestor_details
FROM tenant
where product = (SELECT id from product where lower(name) = {{product | lower}});