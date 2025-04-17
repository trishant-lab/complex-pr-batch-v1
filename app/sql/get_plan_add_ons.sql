SELECT
    f.featurecode AS "code",
    f.description,
    f.details,
    f.sortorder,
    f.marketingtype AS "marketingType",
    f.product,
    pf.plancode
FROM 
    planfeatures pf
JOIN
    features f ON pf.featurecode = f.featurecode AND f.product = pf.product
WHERE
    pf.isincluded = FALSE AND
    pf.cansubscribe = TRUE AND
    f.status = {{ status }} AND
    f.product = LOWER({{ product }})
;