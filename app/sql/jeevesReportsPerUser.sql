SELECT users, COUNT(*) AS count_
FROM
    (
        SELECT
            lva.idvisit,
            lv.custom_dimension_3 As users
        FROM
            matomo_log_link_visit_action lva
        JOIN matomo_log_visit As lv ON lv.idvisit = lva.idvisit
        JOIN
            matomo_log_action la_category ON lva.idaction_event_category = la_category.idaction
        JOIN
            matomo_log_action la_action ON lva.idaction_event_action = la_action.idaction
        JOIN
            matomo_log_action la_name ON lva.idaction_name = la_name.idaction
        WHERE
            lva.idsite = {{ site_id | sqlsafe }}
            AND lv.custom_dimension_2 = {{ tenant | sqlsafe }}
            AND (la_category.name = {{ event_category | sqlsafe }} COLLATE "C")
            AND (la_action.name = {{ event_action | sqlsafe }} COLLATE "C")

            {% if startdate and enddate %}
            AND CAST(lva.server_time AT TIME ZONE 'UTC' AS DATE) BETWEEN '{{ startdate | sqlsafe }}' AND '{{ enddate | sqlsafe }}'
            {% elif startdate %}
            AND CAST(lva.server_time AT TIME ZONE 'UTC' AS DATE) >= '{{ startdate | sqlsafe }}'
            {% elif enddate %}
            AND CAST(lva.server_time AT TIME ZONE 'UTC' AS DATE) <= '{{ enddate | sqlsafe }}'
            {% endif %}


    ) As sub_query
WHERE users <> ''
GROUP BY users