SELECT
    status
FROM
    plans
WHERE
    plancode = {{ code }} AND
    product = {{ product }}
;
