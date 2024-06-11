UPDATE tenant
SET status = {{status}}
<<<<<<< Updated upstream
    , errors = {{error_message}}
    , provisioneddatetime =
=======
    {% if error_message %} , errors = {{error_message}} {% endif %}
>>>>>>> Stashed changes
    {% if status == 'Completed' %} , provisioneddatetime = NOW() {% endif %}
WHERE name = {{tenant_name}} and product = (SELECT id from product where name = {{product}});