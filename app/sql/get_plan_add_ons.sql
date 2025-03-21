SELECT
    f.featurecode AS "code",
    f.description,
    f.details,
    f.sortorder,
    f.marketingtype AS "marketingType",
    pf.plancode
FROM 
    planfeatures pf
JOIN
    features f ON pf.featurecode = f.featurecode
WHERE
    pf.plancode = {{ plancode }} AND
    pf.isincluded = FALSE AND
    pf.cansubscribe = TRUE AND
    f.status = {{ status }} AND
    f.product = {{ product }}
;