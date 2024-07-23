select
    count(distinct(idvisit)) as total_sessions,
    TO_CHAR(
        INTERVAL '1 second' * (SUM(EXTRACT(EPOCH FROM (visit_last_action_time - visit_first_action_time))) / COUNT(distinct(idvisit))),
        'HH24:MI:SS'
    ) AS average_session_duration
from
  matomo_log_visit
where
  idsite = {{ site_id | sqlsafe }}
  and custom_dimension_2 = '{{ tenant | sqlsafe }}'
  {% if startdate and enddate %}
  and CAST(visit_first_action_time AT TIME ZONE 'UTC' AS DATE) between '{{ startdate | sqlsafe }}' and '{{ enddate | sqlsafe }}'
  {% elif startdate %}
  and CAST(visit_first_action_time AT TIME ZONE 'UTC' AS DATE) >= '{{ startdate | sqlsafe }}'
  {% elif enddate %}
  and CAST(visit_first_action_time AT TIME ZONE 'UTC' AS DATE) <= '{{ enddate | sqlsafe }}'
  {% endif %}