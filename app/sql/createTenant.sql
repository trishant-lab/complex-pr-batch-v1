INSERT INTO tenant
        (name, product, created, status, source, requestor, schema)
VALUES  ({{name}}, {{product}}, NOW(), {{status}}, {{source}}, {{requestor_id}}, {{schema_}});