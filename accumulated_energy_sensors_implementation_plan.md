# Implementation Plan: Move Energy Production Sensors to Calculated Sensors

## Current Implementation Analysis
- Energy production sensors are in sensor.py using SigenergyIntegrationSensor class
- Inherits from IntegrationSensor for power-to-energy calculations
- Two types per level (plant, inverter, PV string):
  - Daily energy (resets at midnight)
  - Accumulated energy (never resets)
- Uses power sensors as data source

## Migration Steps

### 1. Create Energy Sensors List in calculated_sensor.py
- Add ENERGY_SENSORS list to SigenergyCalculatedSensors class
- Define sensor descriptions with:
  - Key and name
  - Device class (ENERGY)
  - Unit (KILO_WATT_HOUR)
  - State class (TOTAL_INCREASING)
  - Value function reference
  - Extra function data flag
  - Extra parameters

### 2. Add Integration Function
- Create calculate_energy static method in SigenergyCalculations
- Handle power integration over time
- Support reset at midnight functionality
- Validate power values
- Handle unit conversions

### 3. Modify sensor.py
- Remove energy sensor creation sections
- Update imports and references
- Ensure proper coordination with power sensors

## Benefits
1. More organized code structure
2. Consistent with other calculated sensors
3. Easier maintenance and testing
4. Better separation of concerns

## Technical Details

### Energy Sensor Definition Structure
```python
ENERGY_SENSORS = [
    SigenergySensorEntityDescription(
        key="daily_energy",
        name="Daily PV Energy Production",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=calculate_energy,
        extra_fn_data=True,
        extra_params={"reset_at_midnight": True}
    ),
    SigenergySensorEntityDescription(
        key="accumulated_energy",
        name="Accumulated Energy Production",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=calculate_energy,
        extra_fn_data=True,
        extra_params={"reset_at_midnight": False}
    )
]
```

### Data Flow
1. Power sensor provides instantaneous power reading
2. Calculation function integrates power over time
3. Reset functionality checks time for daily sensors
4. Value stored and reported in kWh

## Testing Considerations
1. Verify energy calculations match original implementation
2. Test midnight reset functionality
3. Validate power source coordination
4. Check unit conversions
5. Verify sensor availability handling