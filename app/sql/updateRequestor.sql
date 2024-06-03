UPDATE requestor
SET username = {{username}},
    email = {{email}},
    organization = {{organization}}
WHERE requestor.id = (SELECT requestor from tenant where id = {{tenant_id}})