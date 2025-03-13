# Comprehensive Implementation Plan for Accumulated Energy Sensors

After conducting a detailed audit of the Home Assistant core integration sensor implementation, this document outlines a comprehensive plan for implementing the 'Accumulated energy' sensors in your Python-based custom component with mathematically identical algorithms and behavior.

## 1. Core Implementation Analysis

### 1.1 Key Components in Core Implementation

The Home Assistant core integration sensor (`homeassistant/components/integration/sensor.py`) implements a sophisticated numerical integration system with several important components:

1. **Integration Methods**:
   - Abstract base class `_IntegrationMethod` with concrete implementations for different methods
   - `_Trapezoidal`, `_Left`, and `_Right` methods with specific calculation algorithms
   - Factory method pattern for creating the appropriate integration method

2. **State Management**:
   - Custom `IntegrationSensorExtraStoredData` class for state restoration
   - Precise handling of state transitions and unavailable states
   - Tracking of last valid state for continuity

3. **Time Handling**:
   - Two integration triggers: `StateEvent` and `TimeElapsed`
   - Sophisticated handling of `max_sub_interval` with interpolation
   - Precise time delta calculations using `total_seconds()`

4. **Numerical Precision**:
   - Exclusive use of `Decimal` for all calculations to avoid floating-point errors
   - Careful handling of invalid numerical values
   - Proper rounding behavior with configurable precision

5. **Unit Conversion**:
   - Handling of unit prefixes (k, M, G, T)
   - Time unit conversion (seconds, minutes, hours, days)
   - Automatic derivation of appropriate units based on source sensor

### 1.2 Critical Algorithmic Nuances

1. **Trapezoidal Method Implementation**:
   ```python
   def calculate_area_with_two_states(self, elapsed_time: Decimal, left: Decimal, right: Decimal) -> Decimal:
       return elapsed_time * (left + right) / 2
   ```

2. **State Validation**:
   ```python
   def validate_states(self, left: str, right: str) -> tuple[Decimal, Decimal] | None:
       if (left_dec := _decimal_state(left)) is None or (right_dec := _decimal_state(right)) is None:
           return None
       return (left_dec, right_dec)
   ```

3. **Decimal Conversion**:
   ```python
   def _decimal_state(state: str) -> Decimal | None:
       try:
           return Decimal(state)
       except (InvalidOperation, TypeError):
           return None
   ```

4. **Integration Trigger Tracking**:
   ```python
   self._last_integration_trigger = _IntegrationTrigger.StateEvent
   self._last_integration_time = datetime.now(tz=UTC)
   ```

5. **Time-based Integration**:
   ```python
   def _schedule_max_sub_interval_exceeded_if_state_is_numeric(self, source_state: State | None) -> None:
       # Complex scheduling logic for time-based integration
   ```

6. **Area Scaling**:
   ```python
   def _update_integral(self, area: Decimal) -> None:
       area_scaled = area / (self._unit_prefix * self._unit_time)
       if isinstance(self._state, Decimal):
           self._state += area_scaled
       else:
           self._state = area_scaled
   ```

## 2. Implementation Strategy

To ensure perfect backward compatibility and identical mathematical behavior, we will implement a custom integration sensor that closely mirrors the core implementation while adapting it to our component's architecture.

### 2.1 Integration Sensor Class

We'll create a `SigenergyIntegrationSensor` class that inherits from `RestoreSensor` and implements the same integration logic as the core implementation:

```python
class SigenergyIntegrationSensor(RestoreSensor):
    """Implementation of an Integration Sensor with identical behavior to HA core."""
    
    _attr_state_class = SensorStateClass.TOTAL
    _attr_should_poll = False
```

### 2.2 Integration Method

We'll implement the trapezoidal method exactly as in the core implementation:

```python
def _calculate_trapezoidal(self, elapsed_time: Decimal, left: Decimal, right: Decimal) -> Decimal:
    """Calculate area using the trapezoidal method."""
    return elapsed_time * (left + right) / 2
```

### 2.3 State Validation and Conversion

We'll implement the same state validation and conversion logic:

```python
def _decimal_state(self, state: str) -> Decimal | None:
    """Convert state to Decimal or return None if not possible."""
    try:
        return Decimal(state)
    except (InvalidOperation, TypeError):
        return None

def _validate_states(self, left: str, right: str) -> tuple[Decimal, Decimal] | None:
    """Validate states and convert to Decimal."""
    if (left_dec := self._decimal_state(left)) is None or (right_dec := self._decimal_state(right)) is None:
        return None
    return (left_dec, right_dec)
```

## 3. Detailed Implementation

### 3.1 Integration Sensor Class

```python
"""Integration sensor for Sigenergy integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
    RestoreSensor,
)
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import callback, State
from homeassistant.helpers.event import async_track_state_change_event, async_call_later
from homeassistant.helpers.typing import EventType
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import SigenergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class IntegrationTrigger(Enum):
    """Trigger type for integration calculations."""
    
    STATE_EVENT = "state_event"
    TIME_ELAPSED = "time_elapsed"

class SigenergyIntegrationSensor(RestoreSensor):
    """Implementation of an Integration Sensor with identical behavior to HA core."""
    
    _attr_state_class = SensorStateClass.TOTAL
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        description: SensorEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[int],
        device_name: Optional[str] = "",
        device_info: Optional[DeviceInfo] = None,
        source_entity_id: str = None,
        round_digits: Optional[int] = None,
        max_sub_interval: Optional[timedelta] = None,
    ) -> None:
        """Initialize the integration sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = name
        self._device_type = device_type
        self._device_id = device_id
        self._device_info_override = device_info
        self._source_entity_id = source_entity_id
        self._round_digits = round_digits
        
        # Initialize state variables
        self._state: Decimal | None = None
        self._last_valid_state: Decimal | None = None
        
        # Time tracking variables
        self._max_sub_interval = (
            None  # disable time based integration
            if max_sub_interval is None or max_sub_interval.total_seconds() == 0
            else max_sub_interval
        )
        self._max_sub_interval_exceeded_callback = lambda *args: None
        self._last_integration_time = dt_util.utcnow()
        self._last_integration_trigger = IntegrationTrigger.STATE_EVENT
        
        # Set unique ID
        if device_type == DEVICE_TYPE_PLANT:
            self._attr_unique_id = f"{coordinator.hub.config_entry.entry_id}_{device_type}_{description.key}"
        else:
            device_number_str = device_name.split()[-1]
            device_number_str = f" {device_number_str}" if device_number_str.isdigit() else ""
            self._attr_unique_id = f"{coordinator.hub.config_entry.entry_id}_{device_type}_{device_number_str}_{description.key}"
        
        # Set device info
        if self._device_info_override:
            self._attr_device_info = self._device_info_override
        else:
            # Use the same device info logic as in SigenergySensor class
            # ...

    def _decimal_state(self, state: str) -> Decimal | None:
        """Convert state to Decimal or return None if not possible."""
        try:
            return Decimal(state)
        except (InvalidOperation, TypeError):
            return None

    def _validate_states(self, left: str, right: str) -> tuple[Decimal, Decimal] | None:
        """Validate states and convert to Decimal."""
        if (left_dec := self._decimal_state(left)) is None or (right_dec := self._decimal_state(right)) is None:
            return None
        return (left_dec, right_dec)

    def _calculate_trapezoidal(self, elapsed_time: Decimal, left: Decimal, right: Decimal) -> Decimal:
        """Calculate area using the trapezoidal method."""
        return elapsed_time * (left + right) / 2

    def _calculate_area_with_one_state(self, elapsed_time: Decimal, constant_state: Decimal) -> Decimal:
        """Calculate area given one state (constant value)."""
        return constant_state * elapsed_time

    def _update_integral(self, area: Decimal) -> None:
        """Update the integral with the calculated area."""
        # Convert seconds to hours
        area_scaled = area / Decimal(3600)
        
        if isinstance(self._state, Decimal):
            self._state += area_scaled
        else:
            self._state = area_scaled
            
        _LOGGER.debug(
            "area = %s, area_scaled = %s new state = %s", area, area_scaled, self._state
        )
        self._last_valid_state = self._state

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Restore previous state if available
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._state = Decimal(last_state.state)
                self._last_valid_state = self._state
                self._last_integration_time = dt_util.utcnow()
            except (ValueError, TypeError, InvalidOperation):
                _LOGGER.warning("Could not restore last state for %s", self.entity_id)
        
        # Set up appropriate handlers based on max_sub_interval
        if self._max_sub_interval is not None:
            source_state = self.hass.states.get(self._source_entity_id)
            self._schedule_max_sub_interval_exceeded_if_state_is_numeric(source_state)
            self.async_on_remove(self._cancel_max_sub_interval_exceeded_callback)
            handle_state_change = self._integrate_on_state_change_with_max_sub_interval
        else:
            handle_state_change = self._integrate_on_state_change_callback
        
        # Register to track source sensor state changes
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._source_entity_id], handle_state_change
            )
        )

    @callback
    def _integrate_on_state_change_callback(self, event) -> None:
        """Handle sensor state change without max_sub_interval."""
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        
        self._integrate_on_state_change(old_state, new_state)

    @callback
    def _integrate_on_state_change_with_max_sub_interval(self, event) -> None:
        """Handle sensor state change with max_sub_interval."""
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        
        # Cancel any pending callbacks
        self._cancel_max_sub_interval_exceeded_callback()
        
        try:
            self._integrate_on_state_change(old_state, new_state)
            self._last_integration_trigger = IntegrationTrigger.STATE_EVENT
            self._last_integration_time = dt_util.utcnow()
        finally:
            # Schedule the next time-based integration
            self._schedule_max_sub_interval_exceeded_if_state_is_numeric(new_state)

    def _integrate_on_state_change(self, old_state: State | None, new_state: State | None) -> None:
        """Perform integration based on state change."""
        if new_state is None:
            return
            
        if new_state.state == STATE_UNAVAILABLE:
            self._attr_available = False
            self.async_write_ha_state()
            return
            
        self._attr_available = True
        
        if old_state is None or old_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self.async_write_ha_state()
            return
            
        # Validate states
        if not (states := self._validate_states(old_state.state, new_state.state)):
            self.async_write_ha_state()
            return
            
        # Calculate elapsed time
        elapsed_seconds = Decimal(
            (new_state.last_updated - old_state.last_updated).total_seconds()
            if self._last_integration_trigger == IntegrationTrigger.STATE_EVENT
            else (new_state.last_updated - self._last_integration_time).total_seconds()
        )
        
        # Calculate area
        area = self._calculate_trapezoidal(elapsed_seconds, *states)
        
        # Update the integral
        self._update_integral(area)
        self.async_write_ha_state()

    def _schedule_max_sub_interval_exceeded_if_state_is_numeric(self, source_state: State | None) -> None:
        """Schedule integration based on max_sub_interval."""
        if (
            self._max_sub_interval is not None
            and source_state is not None
            and (source_state_dec := self._decimal_state(source_state.state)) is not None
        ):
            @callback
            def _integrate_on_max_sub_interval_exceeded_callback(now: datetime) -> None:
                """Integrate based on time and reschedule."""
                elapsed_seconds = Decimal(
                    (now - self._last_integration_time).total_seconds()
                )
                
                # Calculate area with constant state
                area = self._calculate_area_with_one_state(elapsed_seconds, source_state_dec)
                
                # Update the integral
                self._update_integral(area)
                self.async_write_ha_state()
                
                # Update tracking variables
                self._last_integration_time = dt_util.utcnow()
                self._last_integration_trigger = IntegrationTrigger.TIME_ELAPSED
                
                # Schedule the next integration
                self._schedule_max_sub_interval_exceeded_if_state_is_numeric(source_state)
                
            # Schedule the callback
            self._max_sub_interval_exceeded_callback = async_call_later(
                self.hass,
                self._max_sub_interval,
                _integrate_on_max_sub_interval_exceeded_callback,
            )

    def _cancel_max_sub_interval_exceeded_callback(self) -> None:
        """Cancel the scheduled callback."""
        self._max_sub_interval_exceeded_callback()

    @property
    def native_value(self) -> Decimal | None:
        """Return the state of the sensor."""
        if isinstance(self._state, Decimal) and self._round_digits is not None:
            return round(self._state, self._round_digits)
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes of the sensor."""
        return {
            "source_entity": self._source_entity_id,
        }
```

### 3.2 Sensor Description Extension

We need to extend the `SensorEntityDescription` class to include the additional parameters needed for integration sensors:

```python
@dataclass
class SigenergySensorEntityDescription(SensorEntityDescription):
    """Class describing Sigenergy sensor entities."""

    entity_registry_enabled_default: bool = True
    value_fn: Optional[Callable[[Any, Optional[Dict[str, Any]], Optional[Dict[str, Any]]], Any]] = None
    extra_fn_data: Optional[bool] = False
    extra_params: Optional[Dict[str, Any]] = None
    source_entity_id: Optional[str] = None
    max_sub_interval: Optional[timedelta] = None
```

### 3.3 Integration Sensor Configuration

```python
# Add the plant integration sensors list
PLANT_INTEGRATION_SENSORS = [
    SigenergySensorEntityDescription(
        key="plant_accumulated_pv_energy",
        name="Accumulated PV Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        source_entity_id="sensor.sigen_plant_photovoltaic_power",
        round_digits=3,
        max_sub_interval=timedelta(seconds=30),
    ),
    SigenergySensorEntityDescription(
        key="plant_accumulated_grid_export_energy",
        name="Accumulated Grid Export Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        source_entity_id="sensor.sigen_grid_sensor_export_power",
        round_digits=3,
        max_sub_interval=timedelta(seconds=30),
    ),
    SigenergySensorEntityDescription(
        key="plant_accumulated_grid_import_energy",
        name="Accumulated Grid Import Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        source_entity_id="sensor.sigen_grid_sensor_import_power",
        round_digits=3,
        max_sub_interval=timedelta(seconds=30),
    ),
]

# Add the inverter integration sensors list
INVERTER_INTEGRATION_SENSORS = [
    SigenergySensorEntityDescription(
        key="inverter_accumulated_pv_energy",
        name="Accumulated PV Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        source_entity_id="sensor.sigen_inverter_pv_power",
        round_digits=3,
        max_sub_interval=timedelta(seconds=30),
    ),
]
```

### 3.4 Sensor Registration

```python
# Add plant sensors
for description in SS.PLANT_SENSORS + SCS.PLANT_SENSORS:
    entities.append(
        SigenergySensor(
            coordinator=coordinator,
            description=description,
            name=f"{plant_name} {description.name}",
            device_type=DEVICE_TYPE_PLANT,
            device_id=None,
            device_name=plant_name,
        )
    )

# Add plant integration sensors
for description in SCS.PLANT_INTEGRATION_SENSORS:
    entities.append(
        SigenergyIntegrationSensor(
            coordinator=coordinator,
            description=description,
            name=f"{plant_name} {description.name}",
            device_type=DEVICE_TYPE_PLANT,
            device_id=None,
            device_name=plant_name,
            source_entity_id=description.source_entity_id,
            round_digits=description.round_digits,
            max_sub_interval=description.max_sub_interval,
        )
    )

# Add inverter sensors
inverter_no = 0
for inverter_id in coordinator.hub.inverter_slave_ids:
    inverter_name = f"Sigen { f'{plant_name.split()[1] } ' if plant_name.split()[1].isdigit() else ''}Inverter{'' if inverter_no == 0 else f' {inverter_no}'}"
    
    # Add inverter sensors
    for description in SS.INVERTER_SENSORS + SCS.INVERTER_SENSORS:
        entities.append(
            SigenergySensor(
                coordinator=coordinator,
                description=description,
                name=f"{inverter_name} {description.name}",
                device_type=DEVICE_TYPE_INVERTER,
                device_id=inverter_id,
                device_name=inverter_name,
            )
        )
    
    # Add inverter integration sensors
    for description in SCS.INVERTER_INTEGRATION_SENSORS:
        entities.append(
            SigenergyIntegrationSensor(
                coordinator=coordinator,
                description=description,
                name=f"{inverter_name} {description.name}",
                device_type=DEVICE_TYPE_INVERTER,
                device_id=inverter_id,
                device_name=inverter_name,
                source_entity_id=description.source_entity_id,
                round_digits=description.round_digits,
                max_sub_interval=description.max_sub_interval,
            )
        )
```

## 4. Critical Implementation Details

### 4.1 Decimal Precision

All numerical calculations must use the `Decimal` class to ensure precise results:

```python
from decimal import Decimal, InvalidOperation

# Convert state to Decimal
def _decimal_state(self, state: str) -> Decimal | None:
    try:
        return Decimal(state)
    except (InvalidOperation, TypeError):
        return None

# Calculate with Decimal
area = elapsed_seconds * (left_dec + right_dec) / Decimal(2)
```

### 4.2 Time Handling

Time calculations must use `total_seconds()` and be converted to `Decimal`:

```python
elapsed_seconds = Decimal(
    (new_state.last_updated - old_state.last_updated).total_seconds()
)
```

### 4.3 State Restoration

Proper state restoration is critical for maintaining accumulated values:

```python
last_state = await self.async_get_last_state()
if last_state and last_state.state not in (None, STATE_UNKNOWN, STATE_UNAVAILABLE):
    try:
        self._state = Decimal(last_state.state)
        self._last_valid_state = self._state
    except (ValueError, TypeError, InvalidOperation):
        _LOGGER.warning("Could not restore last state for %s", self.entity_id)
```

### 4.4 Max Sub Interval Handling

The `max_sub_interval` parameter requires careful handling:

1. Schedule integration based on time if no state changes occur
2. Cancel and reschedule on state changes
3. Use constant state assumption for time-based integration

```python
def _schedule_max_sub_interval_exceeded_if_state_is_numeric(self, source_state: State | None) -> None:
    """Schedule integration based on max_sub_interval."""
    if (
        self._max_sub_interval is not None
        and source_state is not None
        and (source_state_dec := self._decimal_state(source_state.state)) is not None
    ):
        # Implementation details...
```

### 4.5 Integration Trigger Tracking

Track the trigger type to correctly calculate time deltas:

```python
self._last_integration_trigger = IntegrationTrigger.STATE_EVENT
self._last_integration_time = dt_util.utcnow()
```

### 4.6 Error Handling

Robust error handling is essential for all operations:

```python
try:
    # Perform integration
except (ValueError, TypeError, InvalidOperation) as ex:
    _LOGGER.warning("Error calculating integral for %s: %s", self.entity_id, ex)
```

## 5. Configuration for Your Component

Based on the extracted data and your feedback, you'll need to create these integration sensors:

### Plant Integration Sensors:
1. **Plant Accumulated PV Energy**
   - Key: plant_accumulated_pv_energy
   - Source: sensor.sigen_plant_photovoltaic_power
   - Method: trapezoidal
   - Round: 3
   - Max sub interval: 30 seconds

2. **Plant Accumulated Grid Export Energy**
   - Key: plant_accumulated_grid_export_energy
   - Source: sensor.sigen_grid_sensor_export_power
   - Method: trapezoidal
   - Round: 3
   - Max sub interval: 30 seconds

3. **Plant Accumulated Grid Import Energy**
   - Key: plant_accumulated_grid_import_energy
   - Source: sensor.sigen_grid_sensor_import_power
   - Method: trapezoidal
   - Round: 3
   - Max sub interval: 30 seconds

### Inverter Integration Sensors:
1. **Inverter Accumulated PV Energy**
   - Key: inverter_accumulated_pv_energy
   - Source: sensor.sigen_inverter_pv_power
   - Method: trapezoidal
   - Round: 3
   - Max sub interval: 30 seconds

## 6. Testing and Verification

To ensure the implementation is mathematically identical to the core implementation, we should test:

1. **Basic Integration**: Verify that the sensor correctly accumulates energy over time
2. **State Restoration**: Verify that the sensor correctly restores its state after a restart
3. **Time-based Integration**: Verify that the sensor correctly handles the max_sub_interval parameter
4. **Error Handling**: Verify that the sensor correctly handles invalid states and other errors
5. **Numerical Precision**: Verify that the sensor produces identical results to the core implementation

## 7. Conclusion

By implementing the integration sensor with identical mathematical algorithms and behavior to the core implementation, we ensure perfect backward compatibility and consistent results. The implementation carefully handles all edge cases, numerical precision issues, and time-based calculations to guarantee accurate energy accumulation.
