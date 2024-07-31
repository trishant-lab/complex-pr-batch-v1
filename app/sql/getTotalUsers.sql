select
  count(distinct(idvisitor)) as total_users,
  COUNT(DISTINCT idvisit) / NULLIF(COUNT(DISTINCT idvisitor), 0) AS session_per_user
from
  matomo_log_visit_view
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
