-- Get tenant links for a user by checking if they have any product-specific client role in Keycloak
-- Client name = Product name (e.g., 'jeeves', 'veritable', etc.)
-- Realm naming varies by product:
--   - Jeeves: realm = <tenant>
--   - Veritable: realm = veritable_<tenant>
--   - Other products may have different patterns
--
-- Email matching handles plus-addressing (e.g., abc+g@gmail.com):
--   - First matches exact email
--   - Also matches base email with '+...' stripped (abc@gmail.com)
--
-- Role filtering: Only matches roles passed in the `roles` parameter
-- Pass product-specific roles (e.g., ['VT_CUSTOMER_ADMIN', 'VT_CUSTOMER_USER'] for Veritable)

SELECT DISTINCT concat({{ env_prefix }}::text, c.tenantname, '.', {{ env_suffix }}::text) as tenantlinks
FROM keycloak_fdw.user_entity u
JOIN keycloak_fdw.user_role_mapping urm ON u.id = urm.user_id
JOIN keycloak_fdw.keycloak_role kr ON urm.role_id = kr.id
JOIN keycloak_fdw.client cl ON kr.client = cl.id
JOIN keycloak_fdw.realm r ON u.realm_id = r.id AND cl.realm_id = r.id
JOIN customer c ON r.name IN (
    c.tenantname,  -- realm = tenant (e.g., Jeeves)
    CONCAT(LOWER({{ product }}), '_', c.tenantname)  -- realm = <product>_<tenant> (e.g., Veritable)
)
JOIN provisioningstatus ps ON c.id = ps.customerid
WHERE (
    -- Exact email match
    LOWER(u.email) = LOWER({{ email }})
    OR
    -- Match base email (strip +suffix before @)
    -- e.g., abc+g@gmail.com in Keycloak matches abc@gmail.com input
    LOWER(REGEXP_REPLACE(u.email, '\+[^@]*', '')) = LOWER(REGEXP_REPLACE({{ email }}, '\+[^@]*', ''))
)
  AND u.enabled = true  -- exclude disabled Keycloak users
  AND LOWER(cl.client_id) = LOWER({{ product }})  -- client name = product
  AND c.product = LOWER({{ product }})
  AND ps.status = {{ TenantStatusEnum.Provisioned }}
  AND kr.name IN (
    {% for role in roles %}
      {{ role }} {% if not loop.last %},{% endif %}
    {% endfor %}
  )  -- only match product-specific roles
;
