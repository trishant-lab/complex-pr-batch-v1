UPDATE tenant
SET status = {{status}}
    {% if error_message %} , errors = {{error_message}} {% endif %}
    {% if status == 'Completed' %} , provisioneddatetime = NOW() {% endif %}
WHERE name = {{tenant_name}} and product = (SELECT id from product where name = {{product}});