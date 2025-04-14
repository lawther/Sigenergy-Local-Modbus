## General

- Use **async/await** throughout; avoid blocking calls and synchronous I/O inside coroutines.
- Prioritize **concise responses under 1000 characters**.
- Use **spaces** for indentation, with a width of **4 spaces**.
- Use **double quotes** in YAML and JSON.
- Never expose sensitive data in logs or diagnostics.
- Use **camelCase** for variable names.
- Explain your reasoning before providing code.
- Focus on code **readability** and **maintainability**.
- Prioritize using the **most common library** in the community.

## Home Assistant Best Practices

- Follow HA's **entity model**, **async APIs**, and **config flow** patterns.
- Use **voluptuous** schemas for YAML configs (`CONFIG_SCHEMA`, `PLATFORM_SCHEMA`).
- Prefer **DataUpdateCoordinator** for async data fetching.
- Raise `ConfigEntryNotReady` or `PlatformNotReady` on setup failures to enable retries.
- Fire events with `hass.bus.async_fire("<domain>_event", {...})`, include `device_id`.
- Listen for events via `async_track_state_change`, `async_track_template_result`, or `hass.bus.async_listen`.
- Use **platform files** (`sensor.py`, `switch.py`, etc.), avoid monolithic modules.
- Support **multiple plants, inverters, AC/DC chargers** dynamically.
- Avoid MQTT or REST polling; use **Modbus TCP** and **DataUpdateCoordinator**.

## Modbus TCP

- Assume **TCP protocol** with slave IDs **1-246**.
- Use **non-blocking** Modbus communication.
- Support multiple devices via config flow or YAML.

## File Structure & Naming

- Follow [HA integration structure](https://developers.home-assistant.io/docs/creating_integration_file_structure):
	- `custom_components/<domain>/`
	- Include: `manifest.json`, `__init__.py`, `config_flow.py`, `diagnostics.py`, `system_health.py`, `services.yaml`, platform files, `coordinator.py`.
- Tests in `tests/components/<domain>/` with `__init__.py`, `conftest.py`, `test_*.py`.
- Use **HA naming conventions** for entities, sensors, services.

## Manifest.json

- Must include: `domain`, `name`, `version` (custom only), `codeowners`.
- Optional: `dependencies`, `after_dependencies`, `requirements`, `iot_class`, `quality_scale`, `ssdp`, `zeroconf`, `bluetooth`, `usb`, `dhcp`.
- Add `"config_flow": true` if UI config supported.

## Config Flow & UI

- Subclass `ConfigFlow`, define async steps, handle reauth, migration, subentries.
- Scaffold config flows, translations, tests from [example repo](https://github.com/home-assistant/example-custom-config).
- Use `async_redact_data` to redact sensitive info in diagnostics.
- Register system health via `async_register` in `system_health.py`.

## Services

- Define service schemas in `services.yaml`.
- Register entity services with `async_register_entity_service`.

## Development Workflow

- Use the **integration scaffold script** (`python3 -m script.scaffold integration`) to generate new components.
- Start with the **minimum integration**: `DOMAIN` constant and `async_setup` returning `True` if init succeeds.
- Keep code modular, readable, and maintainable.
- When adding examples, prefer **HA YAML snippets** or **Python code** compatible with HA.

## Summary

- Write **async, non-blocking, modular** code.
- Follow **HA architecture, naming, and file structure**.
- Use **voluptuous** for validation.
- Prefer **scaffolded** components.
- Support **dynamic multi-device setups**.
- Never leak sensitive data.
- Keep instructions **concise and precise**.

## Project Context & Environment

- **Integration Code:** The core Python code for this Sigenergy integration resides in `q:/HACS-Sigenergy-Local-Modbus/custom_components/sigen/`.
- **Home Assistant Instance:** The target Home Assistant instance is running at `http://192.168.1.47:8123/`.
- **Log File:** The Home Assistant log file can be found at `q:/home-assistant.log`.
- **Database:** The Home Assistant database is located at `Q:/home-assistant_v2.db`.

## Available MCP Tools

You have access to specific tools for interacting with the Home Assistant environment:

- **`Home Assistant` MCP Server:** Provides tools (like `HassTurnOn`, `HassTurnOff`, `get_home_state`, etc.) to directly interact with entities and services on the HA instance at `http://192.168.1.47:8123/`. Use this for controlling devices or retrieving state information.
- **`homeassistant_sigen_sql` MCP Server:** Provides tools (`read_query`, `write_query`, etc.) to query or modify the Home Assistant database located at `Q:/home-assistant_v2.db`. Use this for direct database access when needed.

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
