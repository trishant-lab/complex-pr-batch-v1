SELECT users, COUNT(*) AS views
FROM (
    SELECT
        m.idvisit,
        v.custom_dimension_3 AS users
    FROM
        matomo_log_media AS m
    INNER JOIN matomo_log_visit AS v ON v.idvisit = m.idvisit
    WHERE
        m.idsite = {{ site_id | sqlsafe }}
        AND v.custom_dimension_2 = '{{ tenant | sqlsafe }}'
        AND m.media_type = 1
        {% if startdate and enddate %}
        AND CAST(m.server_time AT TIME ZONE 'UTC' AS DATE) BETWEEN '{{ startdate | sqlsafe }}' AND '{{ enddate | sqlsafe }}'
        {% elif startdate %}
        AND CAST(m.server_time AT TIME ZONE 'UTC' AS DATE) >= '{{ startdate | sqlsafe }}'
        {% elif enddate %}
        AND CAST(m.server_time AT TIME ZONE 'UTC' AS DATE) <= '{{ enddate | sqlsafe }}'
        {% endif %}

    UNION ALL

    SELECT
        v.idvisit,
        v.custom_dimension_3 AS users
    FROM
        matomo_log_link_visit_action AS va
    INNER JOIN matomo_log_visit AS v ON v.idvisit = va.idvisit
    INNER JOIN matomo_log_action AS a ON a.idaction = va.idaction_event_action
    WHERE
        v.idsite = {{ site_id | sqlsafe }}
        AND v.custom_dimension_2 = '{{ tenant | sqlsafe }}'
        AND (a.name = 'Asset View' COLLATE "C")
        AND va.custom_dimension_3 LIKE '%%assetType%%'
        {% if startdate and enddate %}
        AND CAST(va.server_time AT TIME ZONE 'UTC' AS DATE) BETWEEN '{{ startdate | sqlsafe }}' AND '{{ enddate | sqlsafe }}'
        {% elif startdate %}
        AND CAST(va.server_time AT TIME ZONE 'UTC' AS DATE) >= '{{ startdate | sqlsafe }}'
        {% elif enddate %}
        AND CAST(va.server_time AT TIME ZONE 'UTC' AS DATE) <= '{{ enddate | sqlsafe }}'
        {% endif %}
) AS combined_data
WHERE users <> ''
GROUP BY users