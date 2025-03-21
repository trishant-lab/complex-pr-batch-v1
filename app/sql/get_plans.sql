SELECT
    p.plancode,
    p.description,
    p.details AS features,
    jsonb_agg(DISTINCT pf.featurecode) AS "includedFeatures",
    p.status,
    p.marketingtype,
    p.sortorder
FROM
    plans p
JOIN
    planfeatures pf ON p.plancode = pf.plancode
JOIN
    features f ON pf.featurecode = f.featurecode
WHERE
    pf.isincluded IS true AND p.product = {{ product }}
GROUP BY
    p.plancode, p.status, p.marketingtype, p.sortorder, p.description, p.details
;
