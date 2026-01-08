select concat({{env_prefix}}::text, tenantname, '.', {{ env_suffix }}::text) as tenantlinks
from customer c
join provisioningstatus ps on c.id = ps.customerid
where id in (select customerid from userevent where email=LOWER({{ email }}) and status) or email=LOWER({{ email }})
and c.product = LOWER({{ product }})
and ps.status = {{ TenantStatusEnum.Provisioned }}
;
