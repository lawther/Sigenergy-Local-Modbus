# Refactoring Plan: Inverter ID to Inverter Name

**Goal:** Refactor the Sigenergy integration code within `custom_components/sigen/` to use `inverter_name` (string) instead of `inverter_id` (integer/slave ID) for iterating over inverters and as keys in data structures.

**Key Findings:**

*   `config_flow.py` already creates and stores `CONF_INVERTER_CONNECTIONS` (dict: `inverter_name` -> connection details) in the config entry.
*   `config_flow.py` also stores a redundant `CONF_INVERTER_SLAVE_ID` (list: `inverter_id`).
*   `modbus.py` currently reads `CONF_INVERTER_SLAVE_ID` to populate `hub.inverter_slave_ids`.
*   `coordinator.py` currently iterates using `hub.inverter_slave_ids` and keys data by `inverter_id`.
*   Entity files likely access data using `inverter_id`.

**Refactoring Steps:**

1.  **Modify `SigenModbusHub` in `modbus.py`:**
    *   Read `CONF_INVERTER_CONNECTIONS` into `self.inverter_connections`.
    *   Remove usage of `CONF_INVERTER_SLAVE_ID` and `self.inverter_slave_ids`.
    *   Update methods like `async_read_inverter_data` to accept `inverter_name` and use `self.inverter_connections[inverter_name][CONF_SLAVE_ID]` internally to get the `slave_id`.

2.  **Modify `SigenDataUpdateCoordinator` in `coordinator.py`:**
    *   Change iteration from `for inverter_id in self.hub.inverter_slave_ids:` to `for inverter_name in self.hub.inverter_connections.keys():`.
    *   Update data fetching/storage to use `inverter_name` as the key (e.g., `inverter_data[inverter_name] = await self.hub.async_read_inverter_data(inverter_name)`).

3.  **Update Data Access in Entity Files (`sensor.py`, `switch.py`, etc.):**
    *   Search for and replace data access patterns using `inverter_id` keys with `inverter_name` keys.
    *   Ensure entity unique IDs are updated if they relied on `inverter_id`.

4.  **Update `diagnostics.py`:**
    *   Ensure diagnostics data generation uses `inverter_name`.

5.  **Review and Verify:**
    *   Review all changes for consistency.

**Diagrammatic Representation (Simplified Flow):**

```mermaid
graph LR
    A[Config Entry Data] -- Contains --> B(CONF_INVERTER_CONNECTIONS<br>{'Inverter 1': {...slave_id: 1}, ...});
    A -- Contains --> C(CONF_INVERTER_SLAVE_ID<br>[1, ...]);

    subgraph Refactoring Changes
        B -- Read by --> D(modbus.py<br>SigenModbusHub);
        D -- Stores --> E(self.inverter_connections);
        E -- Used by --> F(coordinator.py<br>_async_update_data);
        F -- Iterates over --> G(inverter_name in self.hub.inverter_connections.keys());
        F -- Calls --> H(hub.async_read_inverter_data(inverter_name));
        H -- Uses --> I(self.inverter_connections[inverter_name][CONF_SLAVE_ID]);
        F -- Stores data keyed by --> J(inverter_name);
        J -- Accessed by --> K(Entity Files<br>sensor.py, switch.py, ...);
        K -- Uses key --> L(inverter_name);
    end

    subgraph Old/Removed Logic
        C -- Was read by --> M(modbus.py);
        M -- Stored --> N(self.inverter_slave_ids);
        N -- Was used by --> O(coordinator.py);
        O -- Iterated over --> P(inverter_id in self.hub.inverter_slave_ids);
        O -- Stored data keyed by --> Q(inverter_id);
        Q -- Was accessed by --> R(Entity Files);
        R -- Used key --> S(inverter_id);
    end

    style C fill:#f9f,stroke:#333,stroke-width:2px;
    style M fill:#f9f,stroke:#333,stroke-width:2px;
    style N fill:#f9f,stroke:#333,stroke-width:2px;
    style O fill:#f9f,stroke:#333,stroke-width:2px;
    style P fill:#f9f,stroke:#333,stroke-width:2px;
    style Q fill:#f9f,stroke:#333,stroke-width:2px;
    style R fill:#f9f,stroke:#333,stroke-width:2px;
    style S fill:#f9f,stroke:#333,stroke-width:2px;