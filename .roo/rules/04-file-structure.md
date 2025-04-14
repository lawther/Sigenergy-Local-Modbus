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