# Sigenergy AC Charger Support Plan

This document outlines the plan to modify the Sigenergy integration to support multiple AC Chargers with individual IP addresses and ports.

## Goal

The goal is to allow users to specify a unique host IP address and port for each AC Charger within a plant, similar to the existing functionality for inverters. AC Chargers *always* require unique host addresses.

## Plan

### 1. Modify `config_flow.py`

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
    *   Store the AC charger's `host`, `port`, and `slave_id` in a dictionary within the plant's configuration entry.  Use the `CONF_AC_CHARGER_CONNECTIONS` constant for the dictionary key.  The structure will be:

        ```
        {
          "AC Charger": {"host": "192.168.1.20", "port": 502, "slave_id": 5},
          "AC Charger 2": {"host": "192.168.1.21", "port": 502, "slave_id": 6}
        }
        ```

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

### 2. Modify `modbus.py`

*   **Update `SigenergyModbusHub.__init__`:**

    ```python
    # Get specific slave IDs and their connection details
    self.ac_charger_slave_ids = config_entry.data.get(
        CONF_AC_CHARGER_SLAVE_ID, list(range(self.inverter_count + 1, self.inverter_count + self.ac_charger_count + 1))
    )
    self.ac_charger_connections = config_entry.data.get(CONF_AC_CHARGER_CONNECTIONS, {})
    ```

    The existing `_get_client` and `_get_connection_key` methods will handle the lookup of AC Charger connection details correctly, so no further changes are needed in `modbus.py`.

### 3. Modify Translations

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