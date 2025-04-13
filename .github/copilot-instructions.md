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
