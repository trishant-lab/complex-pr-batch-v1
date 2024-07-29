SELECT
    v.custom_dimension_3 as user_name,
    count(*) as searches
FROM
    matomo_log_visit_view as v
    LEFT JOIN matomo_log_link_visit_action_view as va on va.idvisit = v.idvisit
    LEFT JOIN matomo_log_action_view as ea on va.idaction_event_action = ea.idaction
WHERE
    v.idsite = {{ site_id | sqlsafe }}
    AND v.custom_dimension_2 = '{{ tenant | sqlsafe }}'
    AND (
        va.idaction_event_action=(select idaction from matomo_log_action where name = 'Asset Search' COLLATE "C" and type in (11))
        OR
        va.idaction_event_action=(select idaction from matomo_log_action where name = 'Asset search' COLLATE "C" and type in (11))
    )
{% if startdate and enddate %}
    AND CAST(visit_first_action_time AT TIME ZONE 'UTC' AS DATE) between '{{ startdate | sqlsafe }}' and '{{ enddate | sqlsafe }}'
{% elif startdate %}
    AND CAST(visit_first_action_time AT TIME ZONE 'UTC' AS DATE) >= '{{ startdate | sqlsafe }}'
{% elif enddate %}
    AND CAST(visit_first_action_time AT TIME ZONE 'UTC' AS DATE) <= '{{ enddate | sqlsafe }}'
{% endif %}
and v.user_id <> ''
and v.custom_dimension_3 <> ''
group by v.custom_dimension_3