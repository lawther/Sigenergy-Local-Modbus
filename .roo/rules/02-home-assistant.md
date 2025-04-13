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