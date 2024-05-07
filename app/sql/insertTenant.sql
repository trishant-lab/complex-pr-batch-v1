INSERT INTO tenant (name, product, status)
VALUES ({{tenant}}, (SELECT id from product where name = {{product}}), {{status}});