# Implementation Plan: Sigenergy ESS Registers

## 1. Grid Code Implementation Fix

### Current Issue
The `inverter_grid_code` parameter is implemented incorrectly:
- The system currently uses country names as options
- The actual register stores a numeric value (e.g., 11 for Sweden)
- The current implementation won't correctly display or set the grid code

### Solution Approach
1. Create a mapping dictionary between numeric grid codes and country names
2. Update the SigenergySelectEntityDescription for inverter_grid_code to:
   - Convert numeric values to country names for display
   - Convert country names back to numeric values when setting
3. Use the existing country names for the UI but store/retrieve numeric values

### Implementation Steps
1. Create a `GRID_CODE_MAP` dictionary with mappings like:
   ```python
   GRID_CODE_MAP = {
       1: "Germany",
       2: "UK",
       ...
       11: "Sweden",
       ...
   }
   ```

2. Create a reverse mapping function or dictionary for converting back

3. Update the `current_option_fn` to:
   ```python
   lambda data, inverter_id: GRID_CODE_MAP.get(
       data["inverters"].get(inverter_id, {}).get("inverter_grid_code"), 
       f"Unknown ({data['inverters'].get(inverter_id, {}).get('inverter_grid_code', 'N/A')})"
   )
   ```

4. Update the `select_option_fn` to:
   ```python
   lambda hub, inverter_id, option: hub.async_write_inverter_parameter(
       inverter_id,
       "inverter_grid_code",
       next((code for code, name in GRID_CODE_MAP.items() if name == option), 0),
   )
   ```

5. Adjust the options list to use the values from the mapping

## 2. Additional Registers Implementation

All required registers from unused_registers.md have been implemented, except:
- The 16 PV string voltage/current pairs (explicitly excluded per requirements)

The implementation covers:
- Plant running info registers (system time, timezone, power metrics, alarms)
- Plant parameter registers (power targets, limits, phase-specific controls)
- Inverter running info registers (power metrics, alarms, grid values)
- Inverter parameter registers (grid code)
- AC Charger registers (alarms, rated values)

## 3. Testing Considerations

1. Verify the grid code displays correctly based on the numeric value
2. Verify setting a new grid code works correctly
3. Test with various grid code values, including edge cases
4. Ensure all other implemented registers work as expected