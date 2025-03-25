# Refactoring Plan: Replace CONF_DC_CHARGER_SLAVE_ID

**Goal:** Replace the usage of `CONF_DC_CHARGER_SLAVE_ID` (a list of IDs) with `CONF_DC_CHARGER_CONNECTIONS` (a dictionary containing device details, including the slave ID).

**Plan:**

1.  **`custom_components/sigen/const.py`**
    *   Remove the definition: `CONF_DC_CHARGER_SLAVE_ID = "dc_charger_slave_ids"`.

2.  **`custom_components/sigen/config_flow.py`**
    *   **Initialization:** Remove `self._data[CONF_DC_CHARGER_SLAVE_ID] = []`.
    *   **Adding Charger:** Remove the line that adds the ID to `CONF_DC_CHARGER_SLAVE_ID`.
    *   **Retrieving IDs:** Replace direct access to `CONF_DC_CHARGER_SLAVE_ID` with logic to extract IDs from the values of the `CONF_DC_CHARGER_CONNECTIONS` dictionary (e.g., using a list comprehension like `[details[CONF_SLAVE_ID] for details in dc_charger_connections.values()]`). This needs to be done in multiple places where the list of IDs was previously read.
    *   **Removing Charger/Inverter:** Remove blocks of code that attempt to modify the `CONF_DC_CHARGER_SLAVE_ID` list during removal operations.

3.  **`custom_components/sigen/modbus.py`**
    *   **Initialization:** Remove the assignment of `self.dc_charger_slave_ids`.
    *   **Device Setup:** Modify the loop that sets up DC devices. Instead of iterating over `self.dc_charger_slave_ids`, iterate over the *values* of `self.dc_charger_connections` and extract the `CONF_SLAVE_ID` from each dictionary item within the loop.

**Conceptual Diagram:**

```mermaid
graph TD
    subgraph Refactoring Plan
        A[Remove CONF_DC_CHARGER_SLAVE_ID in const.py] --> B;
        B[Update config_flow.py] --> C;
        C[Update modbus.py] --> D{Done};

        subgraph config_flow.py Changes
            B1[Remove init];
            B2[Remove add logic];
            B3[Replace read logic: Get IDs from CONF_DC_CHARGER_CONNECTIONS];
            B4[Remove delete logic];
        end

        subgraph modbus.py Changes
            C1[Remove init];
            C2[Update loop: Iterate CONF_DC_CHARGER_CONNECTIONS];
        end

        B --> B1;
        B --> B2;
        B --> B3;
        B --> B4;
        C --> C1;
        C --> C2;
    end