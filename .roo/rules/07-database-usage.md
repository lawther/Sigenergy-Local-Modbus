# Rules for Interacting with the Home Assistant Database

This document outlines the structure of the Home Assistant database and provides guidance on using the `homeassistant_sigen_sql` MCP tool for querying it. The database stores historical data about events, states, statistics, and system runs.

## MCP Tool: `homeassistant_sigen_sql`

-   **Location:** `Q:/home-assistant_v2.db`
-   **Tools:**
    -   `read_query`: Execute `SELECT` statements.
    -   `write_query`: Execute `INSERT`, `UPDATE`, `DELETE` statements (use with caution).
    -   `list_tables`: List all tables in the database.
    -   `describe_table`: Get the schema for a specific table.

## Key Database Tables

The database normalizes data across several tables to save space. Key tables include:

-   **`events`**: Records events fired within Home Assistant (excluding `state_changed`). Links to `event_data` and `event_types`.
    -   `event_type_id`: Foreign key to `event_types.event_type_id`.
    -   `time_fired_ts`: Timestamp (Unix float) when the event occurred.
    -   `data_id`: Foreign key to `event_data.data_id`.
    -   `context_id_bin`: Binary identifier linking related events/states.
-   **`event_data`**: Stores the JSON payload (`shared_data`) for events. Referenced by `events.data_id`.
-   **`event_types`**: Stores unique event type strings (`event_type`). Referenced by `events.event_type_id`.
-   **`states`**: Records entity state changes. Links to `states_meta` and `state_attributes`.
    -   `metadata_id`: Foreign key to `states_meta.metadata_id` (identifies the entity).
    -   `state`: The actual state value (e.g., 'on', 'off', temperature).
    -   `attributes_id`: Foreign key to `state_attributes.attributes_id`.
    -   `last_updated_ts`: Timestamp (Unix float) of the last update (state or attributes).
    -   `last_changed_ts`: Timestamp (Unix float) of the last state *value* change. **NULL** if only attributes changed. Use `COALESCE(last_changed_ts, last_updated_ts)` or equivalent for the actual last change time.
    -   `old_state_id`: Foreign key linking to the previous state record in the `states` table.
    -   `context_id_bin`: Binary identifier linking related events/states.
-   **`state_attributes`**: Stores the JSON attribute payload (`shared_attrs`) for states. Referenced by `states.attributes_id`.
-   **`states_meta`**: Stores unique entity IDs (`entity_id`). Referenced by `states.metadata_id`.
-   **`statistics`**: Long-term (hourly) aggregated statistics for sensors.
    -   `metadata_id`: Foreign key to `statistics_meta.id`.
    -   `start_ts`: Timestamp (Unix float) for the beginning of the hour.
    -   `mean`, `min`, `max`: For measurement sensors.
    -   `state`, `sum`, `last_reset_ts`: For metered sensors (e.g., energy).
-   **`statistics_short_term`**: Short-term (5-minute) statistics snapshots. Similar structure to `statistics`. Purged periodically.
-   **`statistics_meta`**: Metadata for statistics (`statistic_id`, `unit_of_measurement`, etc.). Referenced by `statistics.metadata_id` and `statistics_short_term.metadata_id`.
-   **`recorder_runs`**: Tracks Home Assistant start/stop times.
    -   `start`, `end`: Timestamps of the run.
    -   `closed_incorrect`: Boolean indicating if HA did not shut down gracefully. If `true`, the `end` time might not be accurate.

## Context

-   `context_id_bin`, `context_user_id_bin`, `context_parent_id_bin` are present in `events` and `states` tables.
-   These binary fields link events and state changes that result from a single trigger (e.g., an automation run, a user action).
-   Use `hex()` (SQLite/MariaDB) or similar functions to view these IDs in a readable format.

## Querying Best Practices

-   **Joins:** Always join related tables (e.g., `states` with `states_meta` and `state_attributes`) to get complete information.
-   **Timestamps:** Fields ending in `_ts` are Unix timestamps (float). Use database functions like `DATETIME(..., 'unixepoch', 'localtime')` (SQLite), `from_unixtime()` (MariaDB), or `to_timestamp()` (PostgreSQL) for human-readable times.
-   **`last_changed_ts`:** Remember to handle `NULL` values when querying `states.last_changed_ts`.
-   **`state_changed` Events:** These are not directly in the `events` table. Query the `states` table for this information. You can `UNION ALL` `events` and `states` queries if needed.
-   **Normalization:** Be aware that `event_data`, `event_types`, `state_attributes`, and `states_meta` store unique values referenced by IDs in the main `events` and `states` tables.

## Example Query (SQLite - Get recent state changes for a specific entity)

```sql
SELECT
    DATETIME(s.last_updated_ts, 'unixepoch', 'localtime') as last_updated,
    sm.entity_id,
    s.state,
    sa.shared_attrs as attributes,
    hex(s.context_id_bin) as context_id
FROM states s
JOIN states_meta sm ON s.metadata_id = sm.metadata_id
LEFT JOIN state_attributes sa ON s.attributes_id = sa.attributes_id
WHERE sm.entity_id = 'sensor.your_entity_id_here'
ORDER BY s.last_updated_ts DESC
LIMIT 10;
```

Adapt table and function names if using MariaDB or PostgreSQL.