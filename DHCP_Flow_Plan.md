# Plan for Sigenergy DHCP Configuration Flow

This document outlines the plan to implement the Home Assistant configuration flow triggered by DHCP discovery for Sigenergy devices.

## Goals

1.  Handle device discovery via DHCP based on MAC address prefixes defined in `manifest.json`.
2.  Prevent adding the same physical device multiple times using the MAC address as the unique ID.
3.  Provide a user-friendly flow to integrate the discovered device:
    *   If no plants exist, configure the device as a new plant automatically.
    *   If plants exist, allow the user to choose between configuring it as a new plant or adding it as an inverter to an existing plant.
4.  Pre-fill the discovered IP address in the configuration forms.
5.  Handle the "Device is already added" scenario gracefully.

## Implementation Steps

1.  **Implement `async_step_dhcp`:**
    *   Triggered by HA on DHCP discovery.
    *   Receives `discovery_info` (IP, MAC).
    *   Store discovered IP in `self._data[CONF_HOST]`.
    *   Set unique ID using `await self.async_set_unique_id(discovery_info.macaddress)`.
    *   Abort if unique ID already configured using `self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.ip})`.
    *   Load existing plants (`await self._async_load_plants()`).
    *   **If no plants:**
        *   Set `self._data[CONF_DEVICE_TYPE] = DEVICE_TYPE_NEW_PLANT`.
        *   Proceed to `async_step_plant_config`.
    *   **If plants exist:**
        *   Proceed to `async_step_dhcp_select_plant`.

2.  **Implement `async_step_dhcp_select_plant`:**
    *   New step to handle user choice when plants exist.
    *   Present options: "Configure as New Plant", "Add as Inverter to Existing Plant".
    *   **If "New Plant":**
        *   Set `self._data[CONF_DEVICE_TYPE] = DEVICE_TYPE_NEW_PLANT`.
        *   Proceed to `async_step_plant_config`.
    *   **If "Add Inverter":**
        *   Set `self._data[CONF_DEVICE_TYPE] = DEVICE_TYPE_INVERTER`.
        *   Proceed to `async_step_select_plant`.

3.  **Modify Existing Steps (`async_step_plant_config`, `async_step_inverter_config`):**
    *   Update `voluptuous` schemas to dynamically pre-fill `CONF_HOST` if present in `self._data`. Use a helper function for schema generation.

4.  **Add Constants and Translations:**
    *   Define `STEP_DHCP_SELECT_PLANT` constant in `const.py`.
    *   (Recommended) Add translation strings for the new step and options in `strings.json`.

## Diagram

```mermaid
graph TD
    A[DHCP Discovery] --> B{async_step_dhcp};
    B --> C{Set unique_id (MAC)};
    C --> D{Already Configured?};
    D -- Yes --> E[Abort Flow];
    D -- No --> F{Load Plants};
    F --> G{Plants Exist?};
    G -- No --> H[Set type: New Plant];
    H --> I[async_step_plant_config (pre-fill IP)];
    G -- Yes --> J[async_step_dhcp_select_plant];
    J --> K{User Choice};
    K -- New Plant --> H;
    K -- Add Inverter --> L[Set type: Inverter];
    L --> M[async_step_select_plant];
    M --> N[async_step_inverter_config (pre-fill IP)];
    I --> O[Create/Update Entry];
    N --> O;
```

## Summary

This plan adds the `async_step_dhcp` entry point, uses the MAC address for unique identification, handles the "already configured" scenario, and guides the user through adding the discovered device either as a new plant or as an inverter to an existing plant, pre-filling the IP address discovered via DHCP.