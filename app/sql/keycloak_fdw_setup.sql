CREATE SCHEMA IF NOT EXISTS keycloak_fdw;

CREATE EXTENSION IF NOT EXISTS postgres_fdw schema public;

CREATE SERVER keycloak_server FOREIGN DATA WRAPPER postgres_fdw OPTIONS (
    dbname 'keycloak',
    host <postgres_host>,
    port '5432'
);

CREATE USER MAPPING IF NOT EXISTS FOR <postgres_user> SERVER keycloak_server 
OPTIONS (user 'keyclock_fdw', password '<keycloak_db_password>'); -- username is not typo!

IMPORT FOREIGN SCHEMA public
    LIMIT TO (realm, client, keycloak_role, user_role_mapping, user_entity)
    FROM SERVER keycloak_server
    INTO keycloak_fdw;
