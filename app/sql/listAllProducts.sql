SELECT * FROM product
{% if product_name %}
where name = {{product_name}}
{% endif %}