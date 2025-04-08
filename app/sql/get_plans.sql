WITH PlanFeaturesView AS (
    SELECT
        plancode,
        product,
        jsonb_agg(DISTINCT featurecode) AS "includedFeatures"
    FROM
        planfeatures
    WHERE
        isincluded IS true AND product = LOWER({{ product }})
    GROUP BY
        plancode, product
)

SELECT
    p.product,
    p.plancode,
    p.description,
    p.details AS features,
    pf."includedFeatures",
    p.status,
    p.marketingtype,
    p.sortorder
FROM
    plans p
JOIN
    PlanFeaturesView pf ON p.plancode = pf.plancode AND p.product = pf.product
WHERE
    p.product = LOWER({{ product }})
;