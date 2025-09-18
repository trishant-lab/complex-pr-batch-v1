INSERT INTO subscription (customerid, name, plancode, product)
VALUES ({{ customer_id }}, {{ name }}, {{ plancode }}, {{ product }})
RETURNING id;
