## Project Context & Environment

- **Integration Code:** The core Python code for this Sigenergy integration resides in `q:/HACS-Sigenergy-Local-Modbus/custom_components/sigen/`.
- **Home Assistant Instance:** The target Home Assistant instance is running at `http://192.168.1.47:8123/`.
- **Log File:** The Home Assistant log file can be found at `q:/home-assistant.log`.
- **Database:** The Home Assistant database is located at `Q:/home-assistant_v2.db`.

## Available MCP Tools

You have access to specific tools for interacting with the Home Assistant environment:

- **`Home Assistant` MCP Server:** Provides tools (like `HassTurnOn`, `HassTurnOff`, `get_home_state`, etc.) to directly interact with entities and services on the HA instance at `http://192.168.1.47:8123/`. Use this for controlling devices or retrieving state information.
- **`homeassistant_sigen_sql` MCP Server:** Provides tools (`read_query`, `write_query`, etc.) to query or modify the Home Assistant database located at `Q:/home-assistant_v2.db`. Use this for direct database access when needed.