## Sigenergy AC Charger Support Plan (Revised)

This document outlines the plan to modify the Sigenergy integration to support multiple AC Chargers with individual IP addresses and ports.

### Goal

The goal is to allow users to specify a unique host IP address and port for each AC Charger within a plant, similar to the existing functionality for inverters. AC Chargers *always* require unique host addresses.

### Plan

#### 1. Modify `config_flow.py`

*   **Add `host` and `port` to `STEP_AC_CHARGER_CONFIG_SCHEMA`:**

    ```python
    STEP_AC_CHARGER_CONFIG_SCHEMA = vol.Schema(
        {
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Required(CONF_SLAVE_ID): int,
        }
    )
    ```

*   **Modify `async_step_ac_charger_config`:**
    *   Always require user input for `host` and `port`. Remove any pre-population logic.
    *   Store the AC charger's `host`, `port`, and `slave_id` in a dictionary within the plant's configuration entry. Use the `CONF_AC_CHARGER_CONNECTIONS` constant for the dictionary key. The structure will be:

        ```
        {
          "AC Charger": {"host": "192.168.1.20", "port": 502, "slave_id": 5},
          "AC Charger 2": {"host": "192.168.1.21", "port": 502, "slave_id": 6}
        }
        ```
        The keys "AC Charger", "AC Charger 2" should be generated based on the number of AC chargers already configured for the plant, similar to how inverter names are generated.

    ```python
    async def async_step_ac_charger_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        # ... (Implementation as described in the plan above) ...
    ```

*   **Add `CONF_AC_CHARGER_CONNECTIONS` to `const.py`:**

    ```python
    CONF_AC_CHARGER_CONNECTIONS = "ac_charger_connections"
    ```

    and import it in `config_flow.py`.

#### 2. Modify `modbus.py`

*   **Update `SigenergyModbusHub.__init__`:**

    ```python
    # Get specific slave IDs and their connection details
    self.ac_charger_slave_ids = config_entry.data.get(
        CONF_AC_CHARGER_SLAVE_ID, list(range(self.inverter_count + 1, self.inverter_count + self.ac_charger_count + 1))
    )
    self.ac_charger_connections = config_entry.data.get(CONF_AC_CHARGER_CONNECTIONS, {})
    ```

* Modify `_get_connection_key` to check `ac_charger_connections`:
    ```python
        def _get_connection_key(self, slave_id: int) -> Tuple[str, int]:
            """Get the connection key (host, port) for a slave ID."""
            # For the plant, use the plant's connection details
            if slave_id == self.plant_id:
                return (self._plant_host, self._plant_port)

            # For inverters, look up their connection details
            for name, details in self.inverter_connections.items():
                if details.get(CONF_SLAVE_ID) == slave_id:
                    return (details[CONF_HOST], details[CONF_PORT])
            
            # For AC chargers, look up their connection details
            for name, details in self.ac_charger_connections.items():
                if details.get(CONF_SLAVE_ID) == slave_id:
                    return (details[CONF_HOST], details[CONF_PORT])

            # If no specific connection found, use the plant's connection details as default
            return (self._plant_host, self._plant_port)
    ```

    The existing `_get_client` method will handle the lookup of AC Charger connection details correctly, so no further changes are needed in `modbus.py`.

#### 3. Modify Translations

*   **`en.json` and `strings.json`:**

    ```json
    "ac_charger_config": {
        "title": "Configure Sigenergy AC Charger",
        "description": "Set up a Sigenergy AC Charger. Enter the unique host address and port for this AC Charger.",
        "data": {
            "host": "Host (IP address of this AC charger)",
            "port": "Port (default is 502)",
            "slave_id": "Device ID (between 1 and 246)"
        }
    },