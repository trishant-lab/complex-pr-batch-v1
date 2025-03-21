UPDATE operatorstatus
SET status = {{status}}
    {% if error_message %} , errors = {{error_message}} {% endif %}
    {% if status == 2 %} , "provisionedDateTime" = NOW() {% endif %}
WHERE customerid = (
    SELECT id from customer where tenantname = {{tenant_name}} AND
    product = {{product}}
);