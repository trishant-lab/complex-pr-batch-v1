INSERT INTO tenant (
    name,
    product,
    status
)
VALUES (
    {{tenant_name}},
    (SELECT id from product where name = {{product}}),
    {{status}}
);