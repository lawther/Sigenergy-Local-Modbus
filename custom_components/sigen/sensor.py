"""Sensor platform for Sigenergy ESS integration."""

from __future__ import annotations
import logging
from typing import Any, Optional
from decimal import Decimal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import (  # pylint: disable=no-name-in-module, syntax-error
    ConfigEntry,
)
from homeassistant.const import (
    CONF_NAME,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (   # pylint: disable=no-name-in-module, syntax-error
    CoordinatorEntity,
)

from .const import (
    CONF_SLAVE_ID,  # Added CONF_SLAVE_ID
    DEVICE_TYPE_AC_CHARGER,
    DEVICE_TYPE_DC_CHARGER,
    DEVICE_TYPE_INVERTER,
    DEVICE_TYPE_PLANT,
    DOMAIN,
    RunningState,
)
from .coordinator import SigenergyDataUpdateCoordinator
from .calculated_sensor import (
    SigenergyCalculations as SC,
    SigenergyCalculatedSensors as SCS,
    SigenergyIntegrationSensor,
)
from .static_sensor import StaticSensors as SS
from .common import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sigenergy sensor platform."""
    coordinator: SigenergyDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id]["coordinator"]
    plant_name = config_entry.data[CONF_NAME]
    _LOGGER.debug("Starting to add %s", SigenergySensor)

    entities: list[SigenergySensor] = []

    _LOGGER.debug("Setting up sensors for %s", config_entry.data[CONF_NAME])
    _LOGGER.debug("Inverters: %s", coordinator.hub.inverter_connections)

    # Add plant sensors
    _LOGGER.debug(
        "[CS][Setup] Adding plant sensors from SS.PLANT_SENSORS + SCS.PLANT_SENSORS"
    )
    # Static Sensors:
    async_add_entities(
        generate_sigen_entity(
            plant_name,
            None,
            None,
            coordinator,
            SigenergySensor,
            SS.PLANT_SENSORS,
            DEVICE_TYPE_PLANT,
        )
    )
    # Calculated Sensors:
    async_add_entities(
        generate_sigen_entity(
            plant_name,
            None,
            None,
            coordinator,
            SigenergySensor,
            SCS.PLANT_SENSORS,
            DEVICE_TYPE_PLANT,
        )
    )

    # Calculated Integration Sensors:
    async_add_entities(
        generate_sigen_entity(
            plant_name,
            None,
            None,
            coordinator,
            SigenergyIntegrationSensor,
            SCS.PLANT_INTEGRATION_SENSORS,
            DEVICE_TYPE_PLANT,
            hass,
        )
    )

    # Add inverter sensors
    for device_name, device_conn in coordinator.hub.inverter_connections.items():
        # Static Sensors:
        async_add_entities(
            generate_sigen_entity(
                plant_name,
                device_name,
                device_conn,
                coordinator,
                SigenergySensor,
                SS.INVERTER_SENSORS,
                DEVICE_TYPE_INVERTER,
            )
        )
        # Calculated Sensors:
        async_add_entities(
            generate_sigen_entity(
                plant_name,
                device_name,
                device_conn,
                coordinator,
                SigenergySensor,
                SCS.INVERTER_SENSORS,
                DEVICE_TYPE_INVERTER,
            )
        )

        # Calculated Integration Sensors:
        async_add_entities(
            generate_sigen_entity(
                plant_name,
                device_name,
                device_conn,
                coordinator,
                SigenergyIntegrationSensor,
                SCS.INVERTER_INTEGRATION_SENSORS,
                DEVICE_TYPE_INVERTER,
                hass,
            )
        )

        # PV strings
        inverter_data = coordinator.data["inverters"][device_name]
        pv_string_count = inverter_data.get("inverter_pv_string_count", 0)

        if (
            pv_string_count
            and isinstance(pv_string_count, (int, float))
            and pv_string_count > 0
        ):

            # Create sensors for each PV string
            for pv_idx in range(1, int(pv_string_count) + 1):
                try:
                    pv_string_name = f"{device_name} PV{pv_idx}"
                    parent_inverter_id = f"{coordinator.hub.config_entry.entry_id}_{generate_device_id(device_name)}"
                    pv_string_id = f"{parent_inverter_id}_pv{pv_idx}"

                    # Create device info
                    pv_device_info = DeviceInfo(
                        identifiers={(DOMAIN, pv_string_id)},
                        name=pv_string_name,
                        manufacturer="Sigenergy",
                        model="PV String",
                        via_device=(DOMAIN, parent_inverter_id),
                    )

                    # Add sensors for this PV string first the static and then the calculated sensors
                    async_add_entities(
                        generate_sigen_entity(
                            plant_name,
                            device_name,
                            device_conn,
                            coordinator,
                            PVStringSensor,
                            SS.PV_STRING_SENSORS,
                            DEVICE_TYPE_INVERTER,
                            hass=hass,
                            device_info=pv_device_info,
                            pv_string_idx=pv_idx,
                        )
                    )

                    async_add_entities(
                        generate_sigen_entity(
                            plant_name,
                            device_name,
                            device_conn,
                            coordinator,
                            PVStringSensor,
                            SCS.PV_STRING_SENSORS,
                            DEVICE_TYPE_INVERTER,
                            hass=hass,
                            device_info=pv_device_info,
                            pv_string_idx=pv_idx,
                        )
                    )

                except Exception as ex:
                    _LOGGER.exception(
                        "Error creating device/sensors for PV string %d: %s", pv_idx, ex
                    )  # Use .exception to include traceback

    # Add AC charger sensors
    # Iterate through the AC charger connection details dictionary
    for ac_charger_name, ac_details in coordinator.hub.ac_charger_connections.items():
        slave_id = ac_details.get(CONF_SLAVE_ID)
        if slave_id is None:
            _LOGGER.warning(
                "Missing slave ID for AC charger '%s' in configuration, skipping sensor setup.",
                ac_charger_name,
            )
            continue  # Skip this charger if slave_id is missing

        _LOGGER.debug(
            "Adding sensors for AC charger '%s' (ID: %s)", ac_charger_name, slave_id
        )
        for description in SS.AC_CHARGER_SENSORS + SCS.AC_CHARGER_SENSORS:
            # Use the ac_charger_name directly from the dictionary key
            sensor_name = f"{ac_charger_name} {description.name}"
            # entity_id = f"sensor.{sensor_name.lower().replace(' ', '_')}" # entity_id is usually handled by HA core based on unique_id

            entities.append(
                SigenergySensor(
                    coordinator=coordinator,
                    description=description,
                    name=sensor_name,
                    device_type=DEVICE_TYPE_AC_CHARGER,
                    device_id=str(slave_id),  # Use the retrieved slave_id
                    device_name=ac_charger_name,  # Use the name from the dictionary key
                )
            )

    # Add DC charger sensors
    dc_charger_no = 0  # Keep counter for potential future naming needs, though name comes from dict key now
    # Iterate through the connection details dictionary
    for (
        dc_charger_name,
        connection_details,
    ) in coordinator.hub.dc_charger_connections.items():
        # Extract the slave ID from the details
        dc_charger_id = connection_details.get(CONF_SLAVE_ID)
        if dc_charger_id is None:
            _LOGGER.warning(
                "Missing slave ID for DC charger '%s' in configuration, skipping sensor setup",
                dc_charger_name,
            )
            continue

        # Check if coordinator actually has data for this DC charger ID
        if (
            not coordinator.data
            or "dc_chargers" not in coordinator.data
            or dc_charger_id not in coordinator.data
            or not coordinator.data["dc_chargers"][dc_charger_id]
        ):
            _LOGGER.warning(
                "No data found for DC charger %s (ID: %s) after coordinator refresh, skipping sensor setup.",
                dc_charger_name,
                dc_charger_id,
            )
            continue

        _LOGGER.debug(
            "Adding sensors for DC charger %s (ID: %s)", dc_charger_name, dc_charger_id
        )
        for description in SS.DC_CHARGER_SENSORS + SCS.DC_CHARGER_SENSORS:
            sensor_name = f"{dc_charger_name} {description.name}"
            entity_id = f"sensor.{sensor_name.lower().replace(' ', '_')}"

            entities.append(
                SigenergySensor(
                    coordinator=coordinator,
                    description=description,
                    name=sensor_name,
                    device_type=DEVICE_TYPE_DC_CHARGER,
                    device_id=dc_charger_id,
                    device_name=dc_charger_name,  # Use name from dict key
                )
            )
        dc_charger_no += 1

    _LOGGER.debug("[Setup Entry] Final entity list count before add: %d", len(entities))
    # Log first 5 entities to see if they look valid
    _LOGGER.debug("[Setup Entry] Sample entities before add: %s", entities[:5])
    if entities:  # Only call if list is not empty
        try:
            async_add_entities(entities)
            _LOGGER.debug(
                "[Setup Entry] Successfully called async_add_entities for all %d entities.",
                len(entities),
            )
        except Exception as ex:
            _LOGGER.exception(
                "[Setup Entry] Error during final async_add_entities call: %s", ex
            )
    else:
        _LOGGER.debug("[Setup Entry] No entities collected to add.")
    _LOGGER.debug("[Setup Entry] Finished async_setup_entry for %s", config_entry.title)


class SigenergySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sigenergy sensor."""

    entity_description: SigenergySensorEntityDescription

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        description: SensorEntityDescription | SigenergySensorEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[str] = None,
        device_name: Optional[str] = "",
        device_info: Optional[DeviceInfo] = None,
        pv_string_idx: Optional[int] = None,
    ) -> None:
        """Initialize the sensor."""
        try:

            super().__init__(coordinator)
            self.entity_description = description  # type: ignore[assignment]
            self._attr_name = name
            self._device_type = device_type
            self._device_id = device_id
            self._device_name = device_name  # Store device name
            self._pv_string_idx = pv_string_idx
            self._device_info_override = device_info
            self._round_digits = None

            if hasattr(description, "round_digits") and description.round_digits is not None:  # type: ignore
                self._round_digits = description.round_digits  # type: ignore

            _LOGGER.debug("Initializing SigenergySensor: %s", name)
            _LOGGER.debug(
                "Device type: %s, Device ID: %s, Device name: %s",
                device_type,
                device_id,
                device_name,
            )
            _LOGGER.debug("Sensor description: %s", description)
            _LOGGER.debug("Sensor key: %s", description.key)
            _LOGGER.debug(
                "Sensor unit of measurement: %s", description.native_unit_of_measurement
            )
            _LOGGER.debug("Sensor state class: %s", description.state_class)
            _LOGGER.debug("Sensor device class: %s", description.device_class)
            _LOGGER.debug("Sensor round digits: %s", self._round_digits)

            # Get the device number if any as a string for use in names
            device_number_str = ""
            if device_name:
                parts = device_name.split()
                if parts and parts[-1].isdigit():
                    device_number_str = f" {parts[-1]}".strip()
            _LOGGER.debug(
                "Device number string for %s: %s", device_name, device_number_str
            )

            # Set unique ID
            self._attr_unique_id = generate_unique_entity_id(
                device_type, device_name, coordinator, description.key, pv_string_idx
            )

            # Set device info (use provided device_info if available)
            if self._device_info_override:
                self._attr_device_info = self._device_info_override
                return

            # Pland device info
            if device_type == DEVICE_TYPE_PLANT:
                self._attr_device_info = DeviceInfo(
                    identifiers={
                        (DOMAIN, f"{coordinator.hub.config_entry.entry_id}_plant")
                    },
                    name=device_name,
                    manufacturer="Sigenergy",
                    model="Energy Storage System",
                )
            # Inverter Device info
            elif device_type == DEVICE_TYPE_INVERTER:
                _LOGGER.debug(
                    "[Sensor Init] Setting up INVERTER device info for name: '%s', ID: '%s'",
                    device_name,
                    self._device_id,
                )
                # Get model and serial number if available
                model = None
                serial_number = None
                sw_version = None
                if coordinator.data and "inverters" in coordinator.data:
                    # Data should be keyed by device_name (inverter_name) now
                    inverter_data = coordinator.data["inverters"].get(device_name, {})
                    model = inverter_data.get("inverter_model_type")
                    serial_number = inverter_data.get("inverter_serial_number")
                    sw_version = inverter_data.get("inverter_machine_firmware_version")

                self._attr_device_info = DeviceInfo(
                    identifiers={
                        (
                            DOMAIN,
                            f"{coordinator.hub.config_entry.entry_id}_{str(device_name).lower().replace(' ', '_')}",
                        )
                    },
                    name=device_name,
                    manufacturer="Sigenergy",
                    model=model,
                    serial_number=serial_number,
                    sw_version=sw_version,
                    via_device=(
                        DOMAIN,
                        f"{coordinator.hub.config_entry.entry_id}_plant",
                    ),
                )
            # AC Charger device info
            elif device_type == DEVICE_TYPE_AC_CHARGER:
                self._attr_device_info = DeviceInfo(
                    identifiers={
                        (
                            DOMAIN,
                            f"{coordinator.hub.config_entry.entry_id}_{str(device_name).lower().replace(' ', '_')}",
                        )
                    },
                    name=device_name,
                    manufacturer="Sigenergy",
                    model="AC Charger",
                    via_device=(
                        DOMAIN,
                        f"{coordinator.hub.config_entry.entry_id}_plant",
                    ),
                )
            # DC Charger device info
            elif device_type == DEVICE_TYPE_DC_CHARGER:
                self._attr_device_info = DeviceInfo(
                    identifiers={
                        (
                            DOMAIN,
                            f"{coordinator.hub.config_entry.entry_id}_{str(device_name).lower().replace(' ', '_')}",
                        )
                    },
                    name=device_name,
                    manufacturer="Sigenergy",
                    model="DC Charger",
                    via_device=(
                        DOMAIN,
                        f"{coordinator.hub.config_entry.entry_id}_plant",
                    ),
                )
            else:
                _LOGGER.error("Unknown device type for sensor: %s", device_type)
        except Exception as ex:
            _LOGGER.exception(
                "[Sensor Init] Error initializing SigenergySensor '%s': %s", name, ex
            )  # Use exception
        _LOGGER.debug(
            "[Sensor Init] Completed initialization for SigenergySensor: %s (Unique ID: %s)",
            self._attr_name,
            self._attr_unique_id,
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        # _LOGGER.debug("[CS][native_value] Getting value for %s (key: %s)", self.entity_id, self.entity_description.key)
        # Special handling for calculated power sensors
        # _LOGGER.debug("[CS][native_value] Checking if %s needs special handling", self.entity_description.key)
        if self.entity_description.key in [
            "plant_grid_import_power",
            "plant_grid_export_power",
            "plant_consumed_power",
        ]:
            if self.coordinator.data is None or "plant" not in self.coordinator.data:
                _LOGGER.warning(
                    "[CS][GridSensor] No coordinator data available for %s",
                    self.entity_id,
                )
                return None

            # Call the value_fn directly with the coordinator data
            if (
                hasattr(self.entity_description, "value_fn")
                and self.entity_description.value_fn is not None
            ):
                # _LOGGER.debug("[CS][native_value] Found value_fn for %s: %s", self.entity_id, self.entity_description.value_fn)
                try:
                    # _LOGGER.debug("[CS][native_value] Calling value_fn for %s", self.entity_id)
                    # Always pass coordinator data to the value_fn
                    # _LOGGER.debug("[CS][native_value] Calling value_fn %s for %s with coordinator data", self.entity_description.value_fn.__name__, self.entity_description.key)
                    transformed_value = self.entity_description.value_fn(
                        None, self.coordinator.data, None
                    )
                    # _LOGGER.debug("[CS][GridSensor] Calculated value for %s: %s",
                    #              self.entity_id, transformed_value)
                    return transformed_value
                except Exception as ex:
                    _LOGGER.error(
                        "Error applying value_fn for %s: %s",
                        self.entity_id,
                        ex,
                    )
                    return None

        # Standard handling for other sensors
        # if self.entity_description.key == "plant_consumed_power":
        #     _LOGGER.debug("[CS][Plant Consumed] Native value called for plant_consumed_power sensor")
        #     _LOGGER.debug("[CS][Plant Consumed] Coordinator data available: %s", bool(self.coordinator.data))
        #     if self.coordinator.data and "plant" in self.coordinator.data:
        #         _LOGGER.debug("[CS][Plant Consumed] Available plant data keys: %s", list(self.coordinator.data["plant"].keys()))

        if self.coordinator.data is None:
            _LOGGER.error(
                "[CS][native_value] No coordinator data available for %s",
                self.entity_id,
            )
            return STATE_UNKNOWN

        if self._device_type == DEVICE_TYPE_PLANT:
            # Use the key directly with plant_ prefix already included
            value = self.coordinator.data["plant"].get(self.entity_description.key)
        elif self._device_type == DEVICE_TYPE_INVERTER:
            # Use the key directly with inverter_ prefix already included
            # Access inverter data using device_name (inverter_name)
            value = (
                self.coordinator.data["inverters"]
                .get(self._device_name, {})
                .get(self.entity_description.key)
            )
        elif self._device_type == DEVICE_TYPE_AC_CHARGER:
            # Use the key directly with ac_charger_ prefix already included
            value = (
                self.coordinator.data["ac_chargers"]
                .get(self._device_id, {})
                .get(self.entity_description.key)
            )
        elif self._device_type == DEVICE_TYPE_DC_CHARGER:
            # Use the key directly with dc_charger_ prefix already included
            value = (
                self.coordinator.data["dc_chargers"]
                .get(self._device_id, {})
                .get(self.entity_description.key)
            )
        else:
            value = None

        if value is None or str(value).lower() == "unknown":
            # Always return None for numeric sensors (ones with measurements or units)
            if (
                self.entity_description.native_unit_of_measurement is not None
                or self.entity_description.state_class
                in [SensorStateClass.MEASUREMENT, SensorStateClass.TOTAL_INCREASING]
            ):
                return None
            return STATE_UNKNOWN

        # Special handling for timestamp sensors
        if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
            try:
                if not isinstance(value, (int, float)):
                    _LOGGER.warning(
                        "Invalid timestamp value type for %s: %s",
                        self.entity_id,
                        type(value),
                    )
                    return None

                # Use epoch_to_datetime for timestamp conversion
                converted_timestamp = SC.epoch_to_datetime(value, self.coordinator.data)
                # _LOGGER.debug("Timestamp conversion for %s: %s -> %s",
                #             self.entity_id, value, converted_timestamp)
                return converted_timestamp
            except Exception as ex:
                _LOGGER.error(
                    "Error converting timestamp for %s: %s", self.entity_id, ex
                )
                return None

        # Apply value_fn if available
        if (
            hasattr(self.entity_description, "value_fn")
            and self.entity_description.value_fn is not None
        ):
            try:
                # Pass coordinator data if needed by the value_fn
                if (
                    hasattr(self.entity_description, "extra_fn_data")
                    and self.entity_description.extra_fn_data
                ):
                    # Pass extra parameters if available
                    extra_params = getattr(
                        self.entity_description, "extra_params", None
                    )
                    # _LOGGER.debug("[CS][native_value] Calling value_fn %s for %s with coordinator data", self.entity_description.value_fn.__name__, self.entity_description.key)
                    transformed_value = self.entity_description.value_fn(
                        value, self.coordinator.data, extra_params
                    )
                else:
                    # _LOGGER.debug("[CS][native_value] Calling value_fn %s for %s with coordinator data", self.entity_description.value_fn.__name__, self.entity_description.key)
                    # Pass coordinator data and None for extra_params for consistency
                    transformed_value = self.entity_description.value_fn(
                        value, self.coordinator.data, None
                    )

                if transformed_value is not None:
                    return transformed_value
            except Exception as ex:
                _LOGGER.error(
                    "Error applying value_fn for %s (value: %s, type: %s): %s",
                    self.entity_id,
                    value,
                    type(value),
                    ex,
                )
                return None

        # Special handling for specific keys
        if self.entity_description.key == "plant_on_off_grid_status":
            return {
                0: "On Grid",
                1: "Off Grid (Auto)",
                2: "Off Grid (Manual)",
            }.get(value, STATE_UNKNOWN)
        if self.entity_description.key == "plant_running_state":
            return {
                RunningState.STANDBY: "Standby",
                RunningState.RUNNING: "Running",
                RunningState.FAULT: "Fault",
                RunningState.SHUTDOWN: "Shutdown",
            }.get(value, STATE_UNKNOWN)
        if self.entity_description.key == "inverter_running_state":
            # _LOGGER.debug("inverter_running_state value: %s", value)
            return {
                RunningState.STANDBY: "Standby",
                RunningState.RUNNING: "Running",
                RunningState.FAULT: "Fault",
                RunningState.SHUTDOWN: "Shutdown",
            }.get(value, STATE_UNKNOWN)
        if self.entity_description.key == "ac_charger_system_state":
            return {
                0: "System Init",
                1: "A1/A2",
                2: "B1",
                3: "B2",
                4: "C1",
                5: "C2",
                6: "F",
                7: "E",
            }.get(value, STATE_UNKNOWN)
        if self.entity_description.key == "inverter_output_type":
            return {
                0: "L/N",
                1: "L1/L2/L3",
                2: "L1/L2/L3/N",
                3: "L1/L2/N",
            }.get(value, STATE_UNKNOWN)
        if self.entity_description.key == "plant_grid_sensor_status":
            return "Connected" if value == 1 else "Not Connected"

        value = (
            round(value, self._round_digits)
            if isinstance(value, Decimal) and self._round_digits is not None
            else value
        )

        return value

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False

        if self._device_type == DEVICE_TYPE_PLANT:
            # _LOGGER.debug("Checking availability for plant %s", self._device_name)
            # _LOGGER.debug("Plant data: %s", self.coordinator.data["plant"])
            return (
                self.coordinator.data is not None and "plant" in self.coordinator.data
            )
        elif self._device_type == DEVICE_TYPE_INVERTER:
            # _LOGGER.debug("Checking availability for inverter '%s' (ID: '%s')", self._device_name, self._device_id)
            if not self.coordinator.data or "inverters" not in self.coordinator.data:
                _LOGGER.warning(
                    "Inverter availability check: No coordinator data or 'inverters' key missing."
                )
                return False

            # Log the keys available in coordinator data for comparison
            # available_inverter_keys = list(self.coordinator.data["inverters"].keys())
            # _LOGGER.debug("Inverter availability check: Available inverter keys in coordinator data: %s", available_inverter_keys)

            # Recommended check using device_name
            final_availability = self._device_name in self.coordinator.data["inverters"]
            if not final_availability:
                _LOGGER.debug(
                    "Inverter availability check: Device name '%s' not found in inverter keys.",
                    self._device_name,
                )

            return final_availability
        elif self._device_type == DEVICE_TYPE_AC_CHARGER:
            return (
                self.coordinator.data is not None
                and "ac_chargers" in self.coordinator.data
                and self._device_id in self.coordinator.data["ac_chargers"]
            )
        elif self._device_type == DEVICE_TYPE_DC_CHARGER:
            return (
                self.coordinator.data is not None
                and "dc_chargers" in self.coordinator.data
                and self._device_id in self.coordinator.data["dc_chargers"]
            )
        else:
            _LOGGER.warning(
                "Unknown device type for availability check: %s", self._device_type
            )

        return False


class PVStringSensor(SigenergySensor):
    """Representation of a PV String sensor."""

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        description: SigenergySensorEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[str] = None,
        device_name: Optional[str] = "",
        device_info: Optional[DeviceInfo] = None,
        pv_string_idx: Optional[int] = None,
    ) -> None:

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

    # Add this property to PVStringSensor to check its availability based on parent inverter
    @property
    def available(self) -> bool:
        """Return if entity is available based on parent inverter."""
        # Check coordinator status first
        if not self.coordinator.last_update_success:
            _LOGGER.warning(
                "PVStringSensor %s unavailable: Coordinator last update failed.",
                self.entity_id,
            )
            return False
        if not self.coordinator.data or "inverters" not in self.coordinator.data:
            _LOGGER.warning(
                "PVStringSensor %s unavailable: No coordinator data or 'inverters' key.",
                self.entity_id,
            )
            return False

        # Check if the parent inverter data exists using _device_name
        parent_inverter_available = (
            self._device_name in self.coordinator.data["inverters"]
        )
        # _LOGGER.debug("PVStringSensor %s availability check: Parent inverter '%s' data exists: %s", self.entity_id, self._device_name, parent_inverter_available)

        return parent_inverter_available  # Base availability on parent inverter for now

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            _LOGGER.warning("No coordinator data available for %s", self.entity_id)
            return STATE_UNKNOWN

        # _LOGGER.debug("PVStringSensor %s native_value: Getting value for PV %d on inverter '%s'", self.entity_id, self._pv_string_idx, self._device_name)
        try:
            # Access inverter data using device_name (inverter_name)
            inverter_data = self.coordinator.data["inverters"].get(
                self._device_name, {}
            )
            if not inverter_data:
                _LOGGER.warning(
                    "PVStringSensor %s native_value: No inverter data found for '%s'",
                    self.entity_id,
                    self._device_name,
                )
                return STATE_UNKNOWN  # Or None if preferred for numeric sensors

            value = None
            # First check if we have a value_fn (for calculated sensors)
            if (
                hasattr(self.entity_description, "value_fn")
                and self.entity_description.value_fn is not None
            ):
                try:
                    value = self.entity_description.value_fn(
                        None,  # value is not used directly by these functions
                        self.coordinator.data,
                        getattr(self.entity_description, "extra_params", {}),
                    )
                except Exception as fn_ex:
                    _LOGGER.error(
                        "PVStringSensor %s native_value: Error executing value_fn %s: %s",
                        self.entity_id,
                        self.entity_description.value_fn.__name__,
                        fn_ex,
                    )
                    value = None  # Or STATE_UNKNOWN

            else:
                data_key = (
                    f"inverter_pv{self._pv_string_idx}_{self.entity_description.key}"
                )
                value = inverter_data.get(data_key)

            # Final check and return
            if value is None:
                _LOGGER.warning(
                    "PVStringSensor %s native_value: Final value is None, returning None",
                    self.entity_id,
                )
                return None  # Return None for numeric sensors if value is missing

            # Attempt to convert to float if it's numeric, otherwise return as is
            try:
                # Check if it's already a number (int, float, Decimal)
                if isinstance(value, (int, float, Decimal)):
                    return float(value)  # Convert to float for HA consistency
                else:
                    return value  # Return non-numeric values directly
            except (ValueError, TypeError) as conv_ex:
                _LOGGER.warning(
                    "PVStringSensor %s native_value: Could not convert final value '%s' to float: %s",
                    self.entity_id,
                    value,
                    conv_ex,
                )
                return STATE_UNKNOWN  # Or None

        except KeyError as ke:
            _LOGGER.error(
                "PVStringSensor %s native_value: KeyError accessing data: %s",
                self.entity_id,
                ke,
            )
            return STATE_UNKNOWN  # Or None
        except Exception as ex:
            _LOGGER.exception(
                "PVStringSensor %s native_value: Unexpected error getting value: %s",
                self.entity_id,
                ex,
            )
            return STATE_UNKNOWN  # Or None
