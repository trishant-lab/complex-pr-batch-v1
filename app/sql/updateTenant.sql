UPDATE tenant
SET status = {{status}}
    , errors = {{error_message}}
    , provisioneddatetime =
    {% if status == 'Completed' %} , provisioneddatetime = NOW() {% endif %}
WHERE name = {{tenant_name}} and product = (SELECT id from product where name = {{product}});