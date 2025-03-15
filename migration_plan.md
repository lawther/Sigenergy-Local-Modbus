# Migration Plan for Calculated Sensors

## Overview

This document outlines the plan for migrating two calculated sensors from YAML configuration to the new integration using `custom_components/sigen/calculated_sensor.py`.

The sensors to migrate are:
1. **Sigen Grid Sensor import power** - Shows grid active power when positive, otherwise 0
2. **Sigen Grid Sensor export power** - Shows grid active power multiplied by -1 when negative, otherwise 0

## Implementation Steps

### 1. Add Calculation Methods to SigenergyCalculations Class

Add two new static methods to the `SigenergyCalculations` class in `calculated_sensor.py`:

```python
@staticmethod
def calculate_grid_import_power(value, coordinator_data: Optional[Dict[str, Any]] = None, extra_params: Optional[Dict[str, Any]] = None) -> Optional[float]:
    """Calculate grid import power (positive values only)."""
    _LOGGER.debug("[CS][Grid Import] Starting calculation with value=%s", value)
    
    if value is None or not isinstance(value, (int, float)):
        _LOGGER.debug("[CS][Grid Import] Invalid value: %s", value)
        return None
        
    # Return value if positive, otherwise 0
    return value if value > 0 else 0

@staticmethod
def calculate_grid_export_power(value, coordinator_data: Optional[Dict[str, Any]] = None, extra_params: Optional[Dict[str, Any]] = None) -> Optional[float]:
    """Calculate grid export power (negative values converted to positive)."""
    _LOGGER.debug("[CS][Grid Export] Starting calculation with value=%s", value)
    
    if value is None or not isinstance(value, (int, float)):
        _LOGGER.debug("[CS][Grid Export] Invalid value: %s", value)
        return None
        
    # Return absolute value if negative, otherwise 0
    return -value if value < 0 else 0
```

These methods should be added after the existing static methods in the `SigenergyCalculations` class, around line 230 (after the `calculate_pv_power` method).

### 2. Add Sensor Descriptions to SigenergyCalculatedSensors Class

Add two new sensor descriptions to the `PLANT_SENSORS` list in the `SigenergyCalculatedSensors` class:

```python
SigenergyCalculations.SigenergySensorEntityDescription(
    key="plant_grid_import_power",
    name="Grid Import Power",
    device_class=SensorDeviceClass.POWER,
    native_unit_of_measurement=UnitOfPower.KILO_WATT,
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:power",
    value_fn=SigenergyCalculations.calculate_grid_import_power,
),
SigenergyCalculations.SigenergySensorEntityDescription(
    key="plant_grid_export_power",
    name="Grid Export Power",
    device_class=SensorDeviceClass.POWER,
    native_unit_of_measurement=UnitOfPower.KILO_WATT,
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:power",
    value_fn=SigenergyCalculations.calculate_grid_export_power,
),
```

These sensor descriptions should be added to the `PLANT_SENSORS` list in the `SigenergyCalculatedSensors` class, around line 630.

## Expected Results

After implementing these changes:

1. The integration will create two new sensors:
   - `sensor.sigen_plant_grid_import_power`
   - `sensor.sigen_plant_grid_export_power`

2. These sensors will have the same functionality as the original YAML sensors:
   - Import power shows grid active power when positive, otherwise 0
   - Export power shows grid active power multiplied by -1 when negative, otherwise 0

3. The sensors will be associated with the plant device and have the correct properties (device class, unit, state class, icon).

## Verification

After implementation, verify:
- The sensors appear in Home Assistant with the correct properties
- The values are calculated correctly based on the grid active power
- The sensors update when the grid active power changes