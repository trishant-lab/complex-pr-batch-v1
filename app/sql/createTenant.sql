INSERT INTO tenant
        (name, product, created, status, source)
VALUES  ({{name}}, {{product}}, NOW(), {{status}}, {{source}});