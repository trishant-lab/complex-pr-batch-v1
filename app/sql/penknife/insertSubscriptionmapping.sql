INSERT INTO {{schema | sqlsafe}}.subscriptionmapping (keycloakuserid, subscriberid, attributes) 
VALUES ({{user_id}}, {{subscriber_id}}, {{attributes}});