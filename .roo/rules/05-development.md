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