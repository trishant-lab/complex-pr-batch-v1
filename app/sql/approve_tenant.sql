WITH updates AS (
    UPDATE customer
    SET "approvedBy" = {{user_id}}
    WHERE id = {{tenant_id}}
    RETURNING id
)
UPDATE operatorstatus
SET status = {{status}}
WHERE cutomerid = (SELECT id FROM updates);