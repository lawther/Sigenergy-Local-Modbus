# Implementation Plan: Sigenergy Device Configuration Interface

## 1. Current System Analysis

The current Sigenergy HACS component implements a simple configuration flow where:
- Users specify host, port, plant ID, and the number of inverters and AC chargers
- Slave IDs are automatically generated for components
- There's no explicit support for DC Chargers
- Modbus TCP is used for communication with devices
- The configuration is handled in a single step without connection relationship management

## 2. New Requirements

When adding a new device to an existing configuration, we need to:

1. Display a selection interface with device types:
   - New Plant
   - Inverter
   - AC Charger
   - DC Charger

2. Process each selection according to these connection rules:
   - **New Plant**: Create plant entity and automatically provision one default Inverter connected to this plant.
   - **Inverter**: 
     - If multiple Plants exist: Prompt user to select desired Plant connection
     - If exactly one Plant exists: Automatically establish connection between Inverter and Plant
   - **DC Charger**:
     - If multiple Inverters exist: Prompt user to select target Inverter connection
     - If exactly one Inverter exists: Automatically establish connection between DC Charger and Inverter
   - **AC Charger**:
     - If multiple Plants exist: Prompt user to select desired Plant connection
     - If exactly one Plant exists: Automatically establish connection between AC Charger and Plant

3. Override logic:
   - If system has no configured Plants, override the selected action
   - Default to adding a New Plant first
   - Then continue with the original device addition sequence

## 3. Implementation Plan

### 3.1 Update Constants in `const.py`

Add or update the following constants:
- `CONF_DC_CHARGER_COUNT` and `CONF_DC_CHARGER_SLAVE_IDS` if not already present
- `DEFAULT_DC_CHARGER_COUNT` (already exists as 0)
- Configuration step identifiers:
  - `STEP_DEVICE_TYPE` - For device type selection
  - `STEP_PLANT_CONFIG` - For plant configuration
  - `STEP_INVERTER_CONFIG` - For inverter configuration
  - `STEP_AC_CHARGER_CONFIG` - For AC charger configuration
  - `STEP_DC_CHARGER_CONFIG` - For DC charger configuration
  - `STEP_SELECT_PLANT` - For selecting a plant when needed
  - `STEP_SELECT_INVERTER` - For selecting an inverter when needed
- Device type options:
  - `DEVICE_TYPE_NEW_PLANT`
  - `DEVICE_TYPE_INVERTER`
  - `DEVICE_TYPE_AC_CHARGER`
  - `DEVICE_TYPE_DC_CHARGER`
- Relationship constants:
  - `CONF_PARENT_DEVICE_ID` - To store the parent device ID
  - `CONF_DEVICE_TYPE` - To store the device type

### 3.2 Update `config_flow.py`

1. **Modify the `SigenergyConfigFlow` class**:
   - Replace single-step flow with multi-step wizard
   - Add a method to check if any Plants exist in the system
   - Implement device type selection step
   - Add conditional logic for different device types

2. **Implement `async_step_device_type`**:
   - Present device type options
   - Check if any Plants exist
   - Override selection if no Plants exist
   - Route to appropriate next step

3. **Implement `async_step_plant_config`**:
   - Collect plant configuration data
   - Generate configuration for default inverter
   - Establish relationship between plant and inverter

4. **Implement `async_step_inverter_config`**:
   - Collect inverter-specific configuration
   - Check existing Plants
   - Auto-connect or route to plant selection

5. **Implement `async_step_ac_charger_config`**:
   - Collect AC charger configuration
   - Check existing Plants
   - Auto-connect or route to plant selection

6. **Implement `async_step_dc_charger_config`**:
   - Collect DC charger configuration
   - Check existing Inverters
   - Auto-connect or route to inverter selection

7. **Implement `async_step_select_plant`**:
   - Display list of existing Plants
   - Handle plant selection
   - Route back to appropriate device configuration

8. **Implement `async_step_select_inverter`**:
   - Display list of existing Inverters
   - Handle inverter selection
   - Route back to DC charger configuration

### 3.3 Update Modbus Implementation in `modbus.py`

1. **Add DC Charger Register Definitions**:
   - Add `DC_CHARGER_RUNNING_INFO_REGISTERS` if not already present
   - Add `DC_CHARGER_PARAMETER_REGISTERS` if not already present

2. **Update `SigenergyModbusHub` class**:
   - Add DC charger slave IDs handling
   - Add methods for reading/writing DC charger data:
     - `async_read_dc_charger_data(self, dc_charger_id)`
     - `async_write_dc_charger_parameter(self, dc_charger_id, register_name, value)`

### 3.4 Update Coordinator in `coordinator.py`

1. **Modify `_async_update_data` method**:
   - Add DC charger data collection if DC chargers are configured
   - Include DC charger data in the combined data dictionary

### 3.5 Update Integration Discovery & Entity Creation

1. **Modify `__init__.py`**:
   - Update entity creation logic to handle new device relationships
   - Ensure proper parent-child relationships between devices

## 4. Data Model

### 4.1 Configuration Entry Data Structure

The updated configuration entry will have the following structure:

```python
{
    CONF_HOST: str,                   # Modbus host address
    CONF_PORT: int,                   # Modbus port
    CONF_NAME: str,                   # Friendly name
    CONF_DEVICE_TYPE: str,            # Device type (plant, inverter, ac_charger, dc_charger)
    CONF_PLANT_ID: int,               # For plant devices
    CONF_INVERTER_COUNT: int,         # Number of inverters (for plants)
    CONF_AC_CHARGER_COUNT: int,       # Number of AC chargers
    CONF_DC_CHARGER_COUNT: int,       # Number of DC chargers
    CONF_INVERTER_SLAVE_IDS: list,    # List of inverter slave IDs
    CONF_AC_CHARGER_SLAVE_IDS: list,  # List of AC charger slave IDs
    CONF_DC_CHARGER_SLAVE_IDS: list,  # List of DC charger slave IDs
    CONF_PARENT_DEVICE_ID: str        # Parent device unique_id (if applicable)
}
```

### 4.2 Device Hierarchy

The device hierarchy will be managed as follows:

1. **Plant**:
   - Top-level device
   - Parent to Inverters and AC Chargers

2. **Inverter**:
   - Child of a Plant
   - Parent to DC Chargers

3. **AC Charger**:
   - Child of a Plant

4. **DC Charger**:
   - Child of an Inverter

## 5. User Interface Flow

1. **Initial Selection**:
   - User selects device type (New Plant, Inverter, AC Charger, DC Charger)
   - If no Plants exist, automatically redirect to Plant creation

2. **New Plant Flow**:
   - User enters plant configuration
   - System automatically creates a default inverter

3. **Inverter Flow**:
   - If multiple Plants exist: User selects parent plant
   - If one Plant exists: Automatic connection
   - User enters inverter configuration

4. **AC Charger Flow**:
   - If multiple Plants exist: User selects parent plant
   - If one Plant exists: Automatic connection
   - User enters AC charger configuration

5. **DC Charger Flow**:
   - If multiple Inverters exist: User selects parent inverter
   - If one Inverter exists: Automatic connection
   - User enters DC charger configuration

## 6. Testing Strategy

1. **Unit Tests**:
   - Test device type selection logic
   - Test override logic when no Plants exist
   - Test connection logic for different scenarios

2. **Integration Tests**:
   - Test complete configuration workflows for each device type
   - Test with various system states (no devices, single plant, multiple plants)

3. **Edge Cases**:
   - Test handling of unavailable devices
   - Test with maximum number of devices
   - Test reconfiguration scenarios

## 7. Implementation Timeline

1. **Phase 1**: Update constants and data structures
2. **Phase 2**: Implement multi-step configuration flow
3. **Phase 3**: Update Modbus and coordinator implementations
4. **Phase 4**: Testing and bug fixes
5. **Phase 5**: Documentation and finalization