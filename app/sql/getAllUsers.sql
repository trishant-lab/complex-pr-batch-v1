select max(first_name) as first_name,
 ue.id,
 max(last_name) as last_name,
  max(username) as username,
  max(email) as email,
  array_agg(json_build_object('id',kr.id, 'name',kr.name)) as roles
from user_entity ue
left join realm rm on rm.id = ue.realm_id
left join user_role_mapping urm on urm.user_id = ue.id
left join  keycloak_role kr on kr.id = urm.role_id
where rm.name = {{ realm_id }} and ue.service_account_client_link is null
group by ue.id
order by first_name asc;