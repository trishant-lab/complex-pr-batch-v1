select concat({{env_prefix}}::text, tenantname, {{ env_suffix }}::text) as tenantlinks
from customer c
where id in (select customerid from userevent where email=LOWER({{ email }}) and status) or email=LOWER({{ email }})
and c.product = LOWER({{ product }})
;