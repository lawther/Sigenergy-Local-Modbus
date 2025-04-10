# Roo Custom Instructions for Sigenergy Home Assistant Integration

This project is a **Home Assistant custom integration** for Sigenergy ESS using **Modbus TCP**. Follow these strict guidelines:

---

## General

- Use **async/await** throughout; avoid blocking calls and synchronous I/O inside coroutines.
- Prioritize **concise responses under 1000 characters**.
- Use **tabs** for indentation.
- Use **double quotes** in YAML and JSON.
- Never expose sensitive data in logs or diagnostics.

---

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

---

## Modbus TCP

- Assume **TCP protocol** with slave IDs **1-246**.
- Use **non-blocking** Modbus communication.
- Support multiple devices via config flow or YAML.

---

## File Structure & Naming

- Follow [HA integration structure](https://developers.home-assistant.io/docs/creating_integration_file_structure):
	- `custom_components/<domain>/`
	- Include: `manifest.json`, `__init__.py`, `config_flow.py`, `diagnostics.py`, `system_health.py`, `services.yaml`, platform files, `coordinator.py`.
- Tests in `tests/components/<domain>/` with `__init__.py`, `conftest.py`, `test_*.py`.
- Use **HA naming conventions** for entities, sensors, services.

---

## Manifest.json

- Must include: `domain`, `name`, `version` (custom only), `codeowners`.
- Optional: `dependencies`, `after_dependencies`, `requirements`, `iot_class`, `quality_scale`, `ssdp`, `zeroconf`, `bluetooth`, `usb`, `dhcp`.
- Add `"config_flow": true` if UI config supported.

---

## Config Flow & UI

- Subclass `ConfigFlow`, define async steps, handle reauth, migration, subentries.
- Scaffold config flows, translations, tests from [example repo](https://github.com/home-assistant/example-custom-config).
- Use `async_redact_data` to redact sensitive info in diagnostics.
- Register system health via `async_register` in `system_health.py`.

---

## Services

- Define service schemas in `services.yaml`.
- Register entity services with `async_register_entity_service`.

---

## Development Workflow

- Use the **integration scaffold script** (`python3 -m script.scaffold integration`) to generate new components.
- Start with the **minimum integration**: `DOMAIN` constant and `async_setup` returning `True` if init succeeds.
- Keep code modular, readable, and maintainable.
- When adding examples, prefer **HA YAML snippets** or **Python code** compatible with HA.

---

## Summary

- Write **async, non-blocking, modular** code.
- Follow **HA architecture, naming, and file structure**.
- Use **voluptuous** for validation.
- Prefer **scaffolded** components.
- Support **dynamic multi-device setups**.
- Never leak sensitive data.
- Keep instructions **concise and precise**.