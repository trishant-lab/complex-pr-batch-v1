SELECT
    users,
    COUNT(*) AS count_
FROM
(
	SELECT
	    lva.idvisit,
	    lv.custom_dimension_3 As users

	FROM
	    matomo_log_link_visit_action_view lva
	INNER JOIN matomo_log_visit_view As lv ON lv.idvisit = lva.idvisit
	INNER JOIN
	    matomo_log_action_view la_category ON lva.idaction_event_category = la_category.idaction
	INNER JOIN
	    matomo_log_action_view la_action ON lva.idaction_event_action = la_action.idaction
	INNER JOIN
	    matomo_log_action_view la_name ON lva.idaction_name = la_name.idaction
	WHERE
	    lva.idsite = {{ site_id | sqlsafe }}
	    AND (la_category.name = {{event_category}} COLLATE "C")
	    AND( la_action.name = {{event_action}} COLLATE "C")
	    AND lv.custom_dimension_2 = '{{ tenant | sqlsafe }}'
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