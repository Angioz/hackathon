/* @bruin
name: hack.story_quality_checks
type: duckdb.sql
description: FR-4. Snapshot of the current run's decision log, gated by Bruin quality checks. If any check fails, export is held back.
depends:
  - writers_room_sim
materialization:
  type: table

columns:
  - name: run_id
    type: varchar
    checks:
      - name: not_null
  - name: decision_id
    type: varchar
    checks:
      - name: not_null
      - name: unique
  - name: agent_id
    type: varchar
    checks:
      - name: not_null
      - name: accepted_values
        value: ["Dev", "Growth", "Critic", "Director"]
  - name: action_type
    type: varchar
    checks:
      - name: not_null
  - name: decision_summary
    type: varchar
    checks:
      - name: not_null
  - name: reasoning_why
    type: varchar
    checks:
      - name: not_null

custom_checks:
  - name: at_least_3_distinct_agents_decided
    query: SELECT CASE WHEN COUNT(DISTINCT agent_id) >= 3 THEN 1 ELSE 0 END FROM hack.story_quality_checks
    value: 1
  - name: plot_twist_present
    query: SELECT CASE WHEN COUNT(*) >= 1 THEN 1 ELSE 0 END FROM hack.story_quality_checks WHERE plot_twist_flag
    value: 1
  - name: why_is_substantive
    query: SELECT COUNT(*) FROM hack.story_quality_checks WHERE length(trim(reasoning_why)) < 15
    value: 0
  - name: ending_was_decided
    query: SELECT COUNT(*) FROM hack.story_quality_checks WHERE action_type = 'arbitrate'
    value: 1
  - name: film_length_between_60_and_180_sec
    query: SELECT CASE WHEN total_target_duration_sec BETWEEN 60 AND 180 THEN 1 ELSE 0 END FROM main.story_bibles WHERE run_id = (SELECT run_id FROM main.run_state ORDER BY started_at DESC LIMIT 1)
    value: 1
@bruin */

SELECT d.*
FROM main.decision_log AS d
WHERE d.run_id = (SELECT run_id FROM main.run_state ORDER BY started_at DESC LIMIT 1)
