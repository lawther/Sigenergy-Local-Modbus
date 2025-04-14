"""Calculated sensor implementations for Sigenergy integration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
    RestoreSensor,
)
from homeassistant.const import (
    UnitOfEnergy,
    EntityCategory,
    UnitOfPower,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import callback, State
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event, async_call_later
from homeassistant.util import dt as dt_util

from .const import EMSWorkMode

from .common import (
    SigenergySensorEntityDescription,
)
from .sigen_entity import SigenergyEntity # Import the new base class

_LOGGER = logging.getLogger(__name__)


class SigenergyCalculations:
    """Static class for Sigenergy calculated sensor functions."""

    # Class variable to store last power readings and timestamps for energy calculation
    _power_history = {}

    @staticmethod
    def minutes_to_gmt(minutes: Any) -> Optional[str]:
        """Convert minutes offset to GMT format."""
        if minutes is None:
            return None
        try:
            hours = int(minutes) // 60
            return f"GMT{'+' if hours >= 0 else ''}{hours}"
        except (ValueError, TypeError):
            return None

    @staticmethod
    def epoch_to_datetime(
        epoch: Any, coordinator_data: Optional[dict] = None
    ) -> Optional[datetime]:
        """Convert epoch timestamp to datetime using system's configured timezone."""
        if epoch is None or epoch == 0:  # Also treat 0 as None for timestamps
            return None

        try:
            # Convert epoch to integer if it isn't already
            epoch_int = int(epoch)

            # Create timezone based on coordinator data if available
            if coordinator_data and "plant" in coordinator_data:
                try:
                    tz_offset = coordinator_data["plant"].get("plant_system_timezone")
                    if tz_offset is not None:
                        tz_minutes = int(tz_offset)
                        tz_hours = tz_minutes // 60
                        tz_remaining_minutes = tz_minutes % 60
                        tz = timezone(
                            timedelta(hours=tz_hours, minutes=tz_remaining_minutes)
                        )
                    else:
                        tz = timezone.utc
                except (ValueError, TypeError) as e:
                    _LOGGER.warning(
                        "[CS][Timestamp] Invalid timezone in coordinator data: %s", e
                    )
                    tz = timezone.utc
            else:
                tz = timezone.utc

            # Additional validation for timestamp range
            if epoch_int < 0 or epoch_int > 32503680000:  # Jan 1, 3000
                _LOGGER.warning(
                    "[CS][Timestamp] Value %s out of reasonable range [0, 32503680000]",
                    epoch_int,
                )
                return None

            try:
                # Convert timestamp using the determined timezone
                dt = datetime.fromtimestamp(epoch_int, tz=tz)
                return dt
            except (OSError, OverflowError) as ex:
                _LOGGER.warning(
                    "[CS][Timestamp] Invalid timestamp %s: %s", epoch_int, ex
                )
                return None

        except (ValueError, TypeError, OSError) as ex:
            _LOGGER.warning("[CS][Timestamp] Conversion error for %s: %s", epoch, ex)
            return None

    @staticmethod
    def calculate_pv_power(
        _,
        coordinator_data: Optional[Dict[str, Any]] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        """Calculate PV string power with proper error handling."""
        if not coordinator_data or not extra_params:
            _LOGGER.warning("Missing required data for PV power calculation")
            return None

        try:
            pv_idx = extra_params.get("pv_idx")
            # Expect device_name instead of device_id
            device_name = extra_params.get("device_name")

            if not pv_idx or not device_name:
                _LOGGER.warning(
                    "Missing PV string index or device name for power calculation from extra_params: %s",
                    extra_params,
                )
                return None

            # Use device_name to look up inverter data
            inverter_data = coordinator_data.get("inverters", {}).get(device_name, {})

            if not inverter_data:
                _LOGGER.warning(
                    "[CS][PV Power] No inverter data available for power calculation"
                )
                return None

            v_key = f"inverter_pv{pv_idx}_voltage"
            c_key = f"inverter_pv{pv_idx}_current"

            pv_voltage = inverter_data.get(v_key)
            pv_current = inverter_data.get(c_key)

            # Validate inputs
            if pv_voltage is None or pv_current is None:
                _LOGGER.warning(
                    "[CS][PV Power] Missing voltage or current data for PV string %d",
                    pv_idx,
                )
                return None

            if not isinstance(pv_voltage, (int, float)) or not isinstance(
                pv_current, (int, float)
            ):
                _LOGGER.warning(
                    "Invalid data types for PV string %d: voltage=%s, current=%s",
                    pv_idx,
                    type(pv_voltage),
                    type(pv_current),
                )
                return None

            # Calculate power with bounds checking
            # Convert to Decimal for precise calculation
            try:
                voltage_dec = Decimal(str(pv_voltage))
                current_dec = Decimal(str(pv_current))
                power = voltage_dec * current_dec  # Already in Watts
            except (ValueError, TypeError, InvalidOperation):
                _LOGGER.warning(
                    "[CS][PV Power] Error converting values to Decimal: V=%s, I=%s",
                    pv_voltage,
                    pv_current,
                )
                # Fallback to float calculation
                power = float(pv_voltage) * float(pv_current)

            # Apply some reasonable bounds
            MAX_REASONABLE_POWER = Decimal(
                "20000"
            )  # 20kW per string is very high already
            if isinstance(power, Decimal) and abs(power) > MAX_REASONABLE_POWER:
                _LOGGER.warning(
                    "[CS][PV Power] Calculated power for PV string %d seems excessive: %s W",
                    pv_idx,
                    power,
                )
            elif not isinstance(power, Decimal) and abs(power) > float(
                MAX_REASONABLE_POWER
            ):
                _LOGGER.warning(
                    "[CS][PV Power] Calculated power for PV string %d seems excessive: %s W",
                    pv_idx,
                    power,
                )

            # Convert to kW
            if isinstance(power, Decimal):
                final_power = power / Decimal("1000")
            else:
                final_power = power / 1000

            return (
                float(final_power) if isinstance(final_power, Decimal) else final_power
            )
        except Exception as ex:  # pylint: disable=broad-exception-caught
            _LOGGER.warning(
                "[CS]Error calculating power for PV string %d: %s",
                extra_params.get("pv_idx", "unknown"),
                ex,
            )
            return None

    @staticmethod
    def calculate_grid_import_power(
        value,
        coordinator_data: Optional[Dict[str, Any]] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        """Calculate grid import power (positive values only)."""
        if coordinator_data is None or "plant" not in coordinator_data:
            return None

        # Get the grid active power value from coordinator data
        grid_power = coordinator_data["plant"].get("plant_grid_sensor_active_power")

        if grid_power is None or not isinstance(grid_power, (int, float)):
            return None

        # Convert to Decimal for precise calculation
        try:
            power_dec = Decimal(str(grid_power))
            # Return value if positive, otherwise 0
            return float(power_dec) if power_dec > Decimal("0") else 0
        except (ValueError, TypeError, InvalidOperation):
            # Fallback to float calculation
            return grid_power if grid_power > 0 else 0

    @staticmethod
    def calculate_grid_export_power(
        value,
        coordinator_data: Optional[Dict[str, Any]] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        """Calculate grid export power (negative values converted to positive)."""
        if coordinator_data is None or "plant" not in coordinator_data:
            return None

        # Get the grid active power value from coordinator data
        grid_power = coordinator_data["plant"].get("plant_grid_sensor_active_power")

        if grid_power is None or not isinstance(grid_power, (int, float)):
            return None

        # Convert to Decimal for precise calculation
        try:
            power_dec = Decimal(str(grid_power))
            # Return absolute value if negative, otherwise 0
            return float(-power_dec) if power_dec < Decimal("0") else 0
        except (ValueError, TypeError, InvalidOperation):
            # Fallback to float calculation
            return -grid_power if grid_power < 0 else 0

    @staticmethod
    def calculate_plant_consumed_power(
        value,
        coordinator_data: Optional[Dict[str, Any]] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        """Calculate plant consumed power (household/building consumption).

        Formula: PV Power + Grid Import Power - Grid Export Power - Plant Battery Power
        """
        if coordinator_data is None or "plant" not in coordinator_data:
            return None

        # Get the required values from coordinator data
        plant_data = coordinator_data["plant"]

        # Get PV power
        pv_power = plant_data.get("plant_photovoltaic_power")

        # Get grid active power and calculate import/export
        grid_power = plant_data.get("plant_grid_sensor_active_power")

        # Get battery power
        battery_power = plant_data.get("plant_ess_power")

        # Validate inputs
        if pv_power is None or grid_power is None or battery_power is None:
            return None

        # Validate input types
        if not isinstance(pv_power, (int, float)):
            return None
        if not isinstance(grid_power, (int, float)):
            _LOGGER.warning(
                "[CS][Plant Consumed] Grid power is not a number: %s (type: %s)",
                grid_power,
                type(grid_power).__name__,
            )
            return None
        if not isinstance(battery_power, (int, float)):
            _LOGGER.warning(
                "[CS][Plant Consumed] Battery power is not a number: %s (type: %s)",
                battery_power,
                type(battery_power).__name__,
            )
            return None

        # Calculate grid import and export power
        # Grid power is positive when importing, negative when exporting
        grid_import = max(0, grid_power)
        grid_export = max(0, -grid_power)

        # Calculate plant consumed power
        # Note: battery_power is positive when charging, negative when discharging
        try:
            consumed_power = pv_power + grid_import - grid_export - battery_power

            # Sanity check
            if consumed_power < 0:
                _LOGGER.warning(
                    "[CS][Plant Consumed] Calculated power is negative: %s kW",
                    consumed_power,
                )
                # Keep the negative value as it might be valid in some scenarios

            if consumed_power > 50:  # Unlikely to have consumption over 50 kW
                _LOGGER.warning(
                    "[CS][Plant Consumed] Calculated power seems excessive: %s kW",
                    consumed_power,
                )
        except Exception as ex:  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "[CS][Plant Consumed] Error during calculation: %s", ex, exc_info=True
            )
            return None

        return consumed_power


class IntegrationTrigger(Enum):
    """Trigger type for integration calculations."""

    STATE_EVENT = "state_event"
    TIME_ELAPSED = "time_elapsed"


class SigenergyIntegrationSensor(SigenergyEntity, RestoreSensor):
    """Implementation of an Integration Sensor with identical behavior to HA core."""

    _attr_state_class = SensorStateClass.TOTAL
    _attr_should_poll = False

    def __init__(
        self,
        coordinator,
        description: SensorEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[str] = None,
        device_name: Optional[str] = "",
        device_info: Optional[DeviceInfo] = None,
        source_entity_id: Optional[str] = None,
        pv_string_idx: Optional[int] = None,
    ) -> None:
        """Initialize the integration sensor."""
        # Call SigenergyEntity's __init__ first
        super().__init__(
            coordinator=coordinator,
            description=description,
            name=name,
            device_type=device_type,
            device_id=device_id,
            device_name=device_name,
            device_info=device_info,
            pv_string_idx=pv_string_idx,
        )
        # Then initialize RestoreSensor
        RestoreSensor.__init__(self)

        # Sensor-specific initialization
        self._source_entity_id = source_entity_id
        # self._pv_string_idx = pv_string_idx # Already handled by SigenergyEntity
        self._round_digits = getattr(description, "round_digits", None)
        self._max_sub_interval = getattr(description, "max_sub_interval", None)

        # Initialize state variables
        self._state: Decimal | None = None
        self._last_valid_state: Decimal | None = None

        # Time tracking variables
        self._max_sub_interval = (
            None  # disable time based integration
            if self._max_sub_interval is None
            or self._max_sub_interval.total_seconds() == 0
            else self._max_sub_interval
        )

        self._max_sub_interval_exceeded_callback = lambda *args: None
        self._cancel_max_sub_interval_exceeded_callback = (
            self._max_sub_interval_exceeded_callback
        )
        self._last_integration_time = dt_util.utcnow()
        self._last_integration_trigger = IntegrationTrigger.STATE_EVENT

        # Device info is now handled by SigenergyEntity's __init__

    def _decimal_state(self, state: str) -> Optional[Decimal]:
        """Convert state to Decimal or return None if not possible."""
        try:
            decimal_value = Decimal(state)
            return decimal_value
        except (InvalidOperation, TypeError) as e:
            _LOGGER.warning("[CS][State] Failed to convert %s to Decimal: %s", state, e)
            return None

    def _validate_states(
        self, left: str, right: str
    ) -> Optional[tuple[Decimal, Decimal]]:
        """Validate states and convert to Decimal."""
        if (left_dec := self._decimal_state(left)) is None or (
            right_dec := self._decimal_state(right)
        ) is None:
            return None
        return (left_dec, right_dec)

    def _calculate_trapezoidal(
        self, elapsed_time: Decimal, left: Decimal, right: Decimal
    ) -> Decimal:
        """Calculate area using the trapezoidal method."""
        return elapsed_time * (left + right) / Decimal(2)

    def _calculate_area_with_one_state(
        self, elapsed_time: Decimal, constant_state: Decimal
    ) -> Decimal:
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

        self._last_valid_state = self._state

    def _setup_midnight_reset(self) -> None:
        """Schedule reset at midnight."""
        now = dt_util.now()
        midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        @callback
        def _handle_midnight(current_time):
            """Handle midnight reset."""
            self._state = Decimal(0)
            self._last_valid_state = self._state
            self.async_write_ha_state()
            self._setup_midnight_reset()  # Schedule next reset

        # Schedule the reset
        self.async_on_remove(
            async_track_point_in_time(self.hass, _handle_midnight, midnight)
        )

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        # Restore previous state if available
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (
            None,
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
        ):
            try:
                self._state = Decimal(last_state.state)
                self._last_valid_state = self._state
                self._last_integration_time = dt_util.utcnow()
            except (ValueError, TypeError, InvalidOperation):
                _LOGGER.warning("Could not restore last state for %s", self.entity_id)

        # Set up appropriate handlers based on max_sub_interval
        # Ensure source_entity_id is valid before proceeding
        if not isinstance(self._source_entity_id, str):
            _LOGGER.error(
                "Source entity ID is not a valid string for %s: %s",
                self.entity_id,
                self._source_entity_id,
            )
            return  # Cannot set up tracking without a valid source ID

        if self._max_sub_interval is not None:
            source_state = self.hass.states.get(self._source_entity_id)
            self._schedule_max_sub_interval_exceeded_if_state_is_numeric(source_state)
            self.async_on_remove(self._cancel_max_sub_interval_exceeded_callback)
            handle_state_change = self._integrate_on_state_change_with_max_sub_interval
        else:
            # _LOGGER.debug("No max_sub_interval set, using default state change handler for %s", self.name)
            handle_state_change = self._integrate_on_state_change_callback

        # Check source entity and log potential alternatives
        self._check_source_entity()

        # Set up midnight reset for daily sensors
        if "daily" in self.entity_description.key:
            self._setup_midnight_reset()

        # Register to track source sensor state changes
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_entity_id],
                handle_state_change,
                # Use the checked source_entity_id
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
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        self._cancel_max_sub_interval_exceeded_callback()

        now = dt_util.utcnow()
        # Compare coordinator update time and elapsed interval
        coordinatorTime = self.coordinator.last_update_success or now
        timeSinceLast = (now - self._last_integration_time).total_seconds()
        if coordinatorTime == getattr(self, "_lastCoordinatorUpdate", None) \
           and timeSinceLast < 2:
            _LOGGER.debug("Skipping integration: %s, interval too short: %s", self.name, timeSinceLast)
        else:
            self._lastCoordinatorUpdate = coordinatorTime
            try:
                self._integrate_on_state_change(old_state, new_state)
                self._last_integration_trigger = IntegrationTrigger.STATE_EVENT
                self._last_integration_time = now
                # _LOGGER.debug(f"[_integrate_on_state_change_with_max_sub_interval] Setting _last_integration_time: {self._last_integration_time.time()}")
            except Exception as ex:
                _LOGGER.warning("Integration error: %s", ex)
            finally:
                self._schedule_max_sub_interval_exceeded_if_state_is_numeric(new_state)

    def _integrate_on_state_change(
        self, old_state: State | None, new_state: State | None
    ) -> None:
        """Perform integration based on state change."""
        if new_state is None:
            return

        if old_state is None or old_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self.async_write_ha_state()
            return

        # Validate states
        if not (states := self._validate_states(old_state.state, new_state.state)):
            self.async_write_ha_state()
            return

        # Calculate elapsed time
        elapsed_seconds = Decimal(
            (new_state.last_reported - old_state.last_reported).total_seconds()
            if self._last_integration_trigger == IntegrationTrigger.STATE_EVENT
            else (new_state.last_reported - self._last_integration_time).total_seconds()
        )

        # Calculate area
        area = self._calculate_trapezoidal(elapsed_seconds, *states)

        # Update the integral
        self._update_integral(area)
        # _LOGGER.debug("[on_state_change][%s] Updated state to: %s", self.entity_id, self._state)
        self.async_write_ha_state()

    def _schedule_max_sub_interval_exceeded_if_state_is_numeric(
        self, source_state: State | None
    ) -> None:
        """Schedule integration based on max_sub_interval."""
        if (
            self._max_sub_interval is not None
            and source_state is not None
            and (source_state_dec := self._decimal_state(source_state.state))
            is not None
        ):

            @callback
            def _integrate_on_max_sub_interval_exceeded_callback(now: datetime) -> None:
                """Integrate based on time and reschedule."""
                if not self._source_entity_id:
                    _LOGGER.error("Source entity ID is not set for %s", self.entity_id)
                    return
                
                # Check if a state change happened very recently to avoid double updates
                time_since_last = now - self._last_integration_time
                # Use timedelta for comparison
                if self._last_integration_trigger == IntegrationTrigger.STATE_EVENT and time_since_last < timedelta(seconds=self.coordinator.largest_update_interval):
                    _LOGGER.debug(
                        "[%s] Skipping time-based integration; state change occurred %s ago",
                        self.entity_id,
                        time_since_last,
                    )
                    # Only reschedule the next integration
                    # Need the original source_state object here, which is captured by the closure
                    source_state_obj = self.hass.states.get(self._source_entity_id)
                    if source_state_obj: # Ensure state object exists before rescheduling
                         self._schedule_max_sub_interval_exceeded_if_state_is_numeric(source_state_obj)
                    return

                elapsed_seconds = Decimal(
                    (now - self._last_integration_time).total_seconds()
                )

                # Calculate area with constant state
                area = self._calculate_area_with_one_state(
                    elapsed_seconds, source_state_dec
                )

                # Update the integral
                self._update_integral(area)
                # Calculate seconds since last update
                self.async_write_ha_state()

                # Update tracking variables
                self._last_integration_time = dt_util.utcnow()
                self._last_integration_trigger = IntegrationTrigger.TIME_ELAPSED

                # Schedule the next integration
                self._schedule_max_sub_interval_exceeded_if_state_is_numeric(
                    source_state
                )

            # Schedule the callback
            self._max_sub_interval_exceeded_callback = async_call_later(
                self.hass,
                self._max_sub_interval,
                _integrate_on_max_sub_interval_exceeded_callback,
            )

    @property
    def native_value(self) -> Decimal | None:
        """Return the state of the sensor."""
        value = (
            round(self._state, self._round_digits)
            if isinstance(self._state, Decimal) and self._round_digits is not None
            else self._state
        )
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return {
            "source_entity": self._source_entity_id,
        }

    def _check_source_entity(self) -> None:
        """Check if the source entity exists and log potential alternatives."""
        source_entity = (
            self.hass.states.get(self._source_entity_id)
            if self._source_entity_id
            else None
        )  # Check for None
        # If source doesn't exist, look for similar entities
        if source_entity is None:
            # Extract key parts from the entity description
            source_key = getattr(self.entity_description, "source_key", "")
            device_type = self._device_type.lower().replace("_", "")

            # Look for entities with similar names
            similar_entities = []
            exact_match_entities = []
            pattern_match_entities = []

            for state in self.hass.states.async_all():
                entity_id = state.entity_id.lower()

                # Skip non-sensor entities
                if not entity_id.startswith("sensor."):
                    continue

                # Skip self
                if entity_id == self.entity_id.lower():
                    continue

                # Check for exact matches first
                if source_key and source_key in entity_id and device_type in entity_id:
                    exact_match_entities.append((state.entity_id, state.state))
                    continue

                # Check for pattern matches
                if entity_id.startswith("sensor.sigen"):
                    # For plant entities
                    if device_type == "plant" and "plant" in entity_id:
                        if source_key and source_key in entity_id:
                            pattern_match_entities.append(
                                (state.entity_id, state.state)
                            )
                        elif (
                            "pv" in source_key
                            and "pv" in entity_id
                            and "power" in entity_id
                        ):
                            pattern_match_entities.append(
                                (state.entity_id, state.state)
                            )
                        elif "grid" in source_key and "grid" in entity_id:
                            if "import" in source_key and "import" in entity_id:
                                pattern_match_entities.append(
                                    (state.entity_id, state.state)
                                )
                            elif "export" in source_key and "export" in entity_id:
                                pattern_match_entities.append(
                                    (state.entity_id, state.state)
                                )

                    # For inverter entities
                    elif device_type == "inverter" and "inverter" in entity_id:
                        if source_key and source_key in entity_id:
                            pattern_match_entities.append(
                                (state.entity_id, state.state)
                            )
                        elif (
                            "pv" in source_key
                            and "pv" in entity_id
                            and "power" in entity_id
                        ):
                            pattern_match_entities.append(
                                (state.entity_id, state.state)
                            )

                    # Add any other sigen entities as general matches
                    similar_entities.append((state.entity_id, state.state))

            # Suggest the best alternative
            if exact_match_entities:
                _LOGGER.warning(
                    "  - Suggested alternative: %s", exact_match_entities[0][0]
                )
            elif pattern_match_entities:
                _LOGGER.warning(
                    "  - Suggested alternative: %s", pattern_match_entities[0][0]
                )


class SigenergyCalculatedSensors:
    """Class for holding calculated sensor methods."""

    PV_STRING_SENSORS = [
        SigenergySensorEntityDescription(
            key="power",
            name="Power",
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=SigenergyCalculations.calculate_pv_power,
            extra_fn_data=True,
            suggested_display_precision=2,
            round_digits=6,
        ),
    ]

    PLANT_SENSORS = [
        # System time and timezone
        SigenergySensorEntityDescription(
            key="plant_system_time",
            name="System Time",
            icon="mdi:clock",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
            # Adapt function signature to match expected value_fn
            value_fn=lambda value, coord_data, _: SigenergyCalculations.epoch_to_datetime(
                value, coord_data
            ),
            extra_fn_data=True,  # Indicates that this sensor needs coordinator data
        ),
        SigenergySensorEntityDescription(
            key="plant_system_timezone",
            name="System Timezone",
            icon="mdi:earth",
            entity_category=EntityCategory.DIAGNOSTIC,
            # Adapt function signature
            value_fn=lambda value, _, __: SigenergyCalculations.minutes_to_gmt(value),
        ),
        # EMS Work Mode sensor with value mapping
        SigenergySensorEntityDescription(
            key="plant_ems_work_mode",
            name="EMS Work Mode",
            icon="mdi:home-battery",
            # Adapt function signature
            value_fn=lambda value, _, __: {
                EMSWorkMode.MAX_SELF_CONSUMPTION: "Maximum Self Consumption",
                EMSWorkMode.AI_MODE: "AI Mode",
                EMSWorkMode.TOU: "Time of Use",
                EMSWorkMode.REMOTE_EMS: "Remote EMS",
            }.get(value, "Unknown"),
        ),
        SigenergySensorEntityDescription(
            key="plant_grid_import_power",
            name="Grid Import Power",
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:power",
            value_fn=SigenergyCalculations.calculate_grid_import_power,
            extra_fn_data=True,  # Pass coordinator data to value_fn
            suggested_display_precision=2,
            round_digits=6,
        ),
        SigenergySensorEntityDescription(
            key="plant_grid_export_power",
            name="Grid Export Power",
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:power",
            value_fn=SigenergyCalculations.calculate_grid_export_power,
            extra_fn_data=True,  # Pass coordinator data to value_fn
            suggested_display_precision=2,
            round_digits=6,
        ),
        SigenergySensorEntityDescription(
            key="plant_consumed_power",
            name="Consumed Power",
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:home-lightning-bolt",
            value_fn=SigenergyCalculations.calculate_plant_consumed_power,
            extra_fn_data=True,  # Pass coordinator data to value_fn
            suggested_display_precision=2,
            round_digits=6,
        ),
    ]

    INVERTER_SENSORS = [
        SigenergySensorEntityDescription(
            key="inverter_startup_time",
            name="Startup Time",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
            # Adapt function signature
            value_fn=lambda value, coord_data, _: SigenergyCalculations.epoch_to_datetime(
                value, coord_data
            ),
            extra_fn_data=True,  # Indicates that this sensor needs coordinator data
        ),
        SigenergySensorEntityDescription(
            key="inverter_shutdown_time",
            name="Shutdown Time",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
            # Adapt function signature
            value_fn=lambda value, coord_data, _: SigenergyCalculations.epoch_to_datetime(
                value, coord_data
            ),
            extra_fn_data=True,  # Indicates that this sensor needs coordinator data
        ),
    ]

    AC_CHARGER_SENSORS = []

    DC_CHARGER_SENSORS = []

    # Add the plant integration sensors list
    PLANT_INTEGRATION_SENSORS = [
        SigenergySensorEntityDescription(
            key="plant_accumulated_pv_energy",
            name="Accumulated PV Energy",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            suggested_display_precision=2,
            state_class=SensorStateClass.TOTAL,
            source_key="plant_photovoltaic_power",  # Key of the source entity to use
            round_digits=6,
            max_sub_interval=timedelta(seconds=30),
        ),
        SigenergySensorEntityDescription(
            key="plant_accumulated_grid_export_energy",
            name="Accumulated Grid Export Energy",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            suggested_display_precision=2,
            state_class=SensorStateClass.TOTAL,
            source_key="plant_grid_export_power",  # Key matches the calculated sensor
            round_digits=6,
            max_sub_interval=timedelta(seconds=30),
        ),
        SigenergySensorEntityDescription(
            key="plant_accumulated_grid_import_energy",
            name="Accumulated Grid Import Energy",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            suggested_display_precision=2,
            state_class=SensorStateClass.TOTAL,
            source_key="plant_grid_import_power",  # Key matches the calculated sensor
            round_digits=6,
            max_sub_interval=timedelta(seconds=30),
        ),
        SigenergySensorEntityDescription(
            key="plant_daily_grid_export_energy",
            name="Daily Grid Export Energy",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            suggested_display_precision=2,
            state_class=SensorStateClass.TOTAL_INCREASING,
            source_key="plant_grid_export_power",  # Key matches the grid export power sensor
            round_digits=6,
            max_sub_interval=timedelta(seconds=30),
        ),
        SigenergySensorEntityDescription(
            key="plant_daily_grid_import_energy",
            name="Daily Grid Import Energy",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            suggested_display_precision=2,
            state_class=SensorStateClass.TOTAL_INCREASING,
            source_key="plant_grid_import_power",  # Key matches the grid import power sensor
            round_digits=6,
            max_sub_interval=timedelta(seconds=30),
        ),
        SigenergySensorEntityDescription(
            key="plant_daily_pv_energy",
            name="Daily PV Energy",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            suggested_display_precision=2,
            state_class=SensorStateClass.TOTAL_INCREASING,
            source_key="plant_photovoltaic_power",  # Key matches the PV power sensor
            round_digits=6,
            max_sub_interval=timedelta(seconds=30),
        ),
        SigenergySensorEntityDescription(
            key="plant_accumulated_consumed_energy",
            name="Accumulated Consumed Energy",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            suggested_display_precision=2,
            state_class=SensorStateClass.TOTAL,
            source_key="plant_consumed_power",  # Key of the source entity to use
            round_digits=6,
            max_sub_interval=timedelta(seconds=30),
        ),
        SigenergySensorEntityDescription(
            key="plant_daily_consumed_energy",
            name="Daily Consumed Energy",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            suggested_display_precision=2,
            state_class=SensorStateClass.TOTAL_INCREASING,
            source_key="plant_consumed_power",  # Key of the source entity to use
            round_digits=6,
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
            suggested_display_precision=2,
            state_class=SensorStateClass.TOTAL,
            source_key="inverter_pv_power",  # Key matches the sensor in static_sensor.py
            round_digits=6,
            max_sub_interval=timedelta(seconds=30),
        ),
    ]
