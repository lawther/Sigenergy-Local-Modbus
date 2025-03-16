# Refactoring Plan for Sigenergy Config Flow

## Requirements
- Remove the need to specify plant_id. It should always be 247 (DEFAULT_PLANT_SLAVE_ID).
- The current configuration schema should only be used if this is the first integration of this type being added or "New Plant" is chosen.
- Otherwise, a schema where the user is asked to choose the type of device they want to add should be used.
- Different schemas should be used for each device type.

## Current Status
After reviewing the code, I can see that most of the required changes are already implemented:

1. The config_flow.py file has:
   - Device type selection (New Plant, Inverter, AC Charger, DC Charger)
   - Plant configuration without plant_id (it's set to DEFAULT_PLANT_SLAVE_ID)
   - Plant selection for devices
   - Inverter selection for DC Chargers
   - Device-specific configuration steps

2. The strings.json and translations/en.json files have the necessary translations for all the steps.

## Changes Needed

1. Remove the STEP_USER_DATA_SCHEMA from config_flow.py as it's no longer needed. The user step should now either:
   - Show device type selection if plants exist
   - Go directly to plant configuration if no plants exist

2. Ensure the plant_id is always set to DEFAULT_PLANT_SLAVE_ID in the plant configuration step (this is already done)

3. Update the strings.json and translations/en.json files to remove any references to plant_id (if any)

## Implementation Steps

1. Remove the STEP_USER_DATA_SCHEMA from config_flow.py
2. Verify that the async_step_user method correctly handles the flow based on whether plants exist
3. Verify that the plant_id is always set to DEFAULT_PLANT_SLAVE_ID in the plant configuration step
4. Update the strings.json and translations/en.json files if needed