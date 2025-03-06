"""Calculated sensor platform for Sigenergy ESS integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    EntityCategory,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import slugify
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DEVICE_TYPE_AC_CHARGER,
    DEVICE_TYPE_DC_CHARGER,
    DEVICE_TYPE_INVERTER,
    DEVICE_TYPE_PLANT,
    DOMAIN,
)
from .coordinator import SigenergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class SigenCalculatedSensorEntityDescription(SensorEntityDescription):
    """Class describing Sigenergy calculated sensor entities."""

    calculate_value_fn: Callable[[dict, Optional[int]], Any] = None
    entity_registry_enabled_default: bool = True


INVERTER_CALCULATED_SENSORS = [
    SigenCalculatedSensorEntityDescription(
        key="pv1_power",
        name="PV1 Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        calculate_value_fn=lambda data, inverter_id: round(
            data["inverters"].get(inverter_id, {}).get("pv1_voltage", 0) * 
            data["inverters"].get(inverter_id, {}).get("pv1_current", 0)
        ),
    ),
    SigenCalculatedSensorEntityDescription(
        key="pv2_power",
        name="PV2 Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        calculate_value_fn=lambda data, inverter_id: round(
            data["inverters"].get(inverter_id, {}).get("pv2_voltage", 0) * 
            data["inverters"].get(inverter_id, {}).get("pv2_current", 0)
        ),
    ),
    SigenCalculatedSensorEntityDescription(
        key="phase_a_power",
        name="Phase A Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        calculate_value_fn=lambda data, inverter_id: round(
            data["inverters"].get(inverter_id, {}).get("phase_a_voltage", 0) * 
            data["inverters"].get(inverter_id, {}).get("phase_a_current", 0)
        ),
    ),
    SigenCalculatedSensorEntityDescription(
        key="phase_b_power",
        name="Phase B Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        calculate_value_fn=lambda data, inverter_id: round(
            data["inverters"].get(inverter_id, {}).get("phase_b_voltage", 0) * 
            data["inverters"].get(inverter_id, {}).get("phase_b_current", 0)
        ),
    ),
    SigenCalculatedSensorEntityDescription(
        key="phase_c_power",
        name="Phase C Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        calculate_value_fn=lambda data, inverter_id: round(
            data["inverters"].get(inverter_id, {}).get("phase_c_voltage", 0) * 
            data["inverters"].get(inverter_id, {}).get("phase_c_current", 0)
        ),
    ),
    SigenCalculatedSensorEntityDescription(
        key="battery_charge_discharge_rate",
        name="Battery Charge/Discharge Rate",
        native_unit_of_measurement="W/kWh",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        calculate_value_fn=lambda data, inverter_id: round(
            abs(data["inverters"].get(inverter_id, {}).get("ess_charge_discharge_power", 0) * 1000) / 
            max(data["inverters"].get(inverter_id, {}).get("ess_battery_capacity", 1), 1), 
            2
        ),
    ),
]

PLANT_CALCULATED_SENSORS = [
    SigenCalculatedSensorEntityDescription(
        key="battery_remaining_time",
        name="Battery Remaining Time",
        icon="mdi:clock-outline",
        state_class=SensorStateClass.MEASUREMENT,
        calculate_value_fn=lambda data, _: _calculate_battery_remaining_time(data),
    ),
    SigenCalculatedSensorEntityDescription(
        key="self_consumption_rate",
        name="Self Consumption Rate",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        calculate_value_fn=lambda data, _: _calculate_self_consumption_rate(data),
    ),
]


def _calculate_battery_remaining_time(data):
    """Calculate estimated battery remaining time based on current discharge rate."""
    if not data or "plant" not in data:
        return None
    
    # Get battery discharge power (kW) and state of charge
    battery_power = data["plant"].get("ess_power", 0)
    battery_soc = data["plant"].get("ess_soc", 0)
    
    # If battery is charging or not discharging, return None
    if battery_power <= 0:
        return None
    
    # Get battery capacity (rough estimate based on available data)
    max_discharge_capacity = data["plant"].get("ess_available_max_discharging_capacity", 0)
    
    # If no capacity data, we can't calculate
    if max_discharge_capacity <= 0 or battery_soc <= 0:
        return None
    
    # Calculate estimated remaining time in hours
    remaining_capacity = max_discharge_capacity * (battery_soc / 100)
    if battery_power > 0:
        remaining_hours = remaining_capacity / battery_power
        # Convert to HH:MM format
        hours = int(remaining_hours)
        minutes = int((remaining_hours - hours) * 60)
        return f"{hours}:{minutes:02d}"
    
    return None


def _calculate_self_consumption_rate(data):
    """Calculate self-consumption rate as percentage of PV power used locally."""
    if not data or "plant" not in data:
        return None
    
    pv_power = data["plant"].get("photovoltaic_power", 0)
    grid_power = data["plant"].get("grid_sensor_active_power", 0)
    
    # If no PV production or grid export, return None
    if pv_power <= 0:
        return None
    
    # If grid power is negative, we're exporting
    if grid_power < 0:
        # Self-consumption = (PV production - grid export) / PV production
        self_consumption = (pv_power + grid_power) / pv_power * 100
        return round(max(0, min(self_consumption, 100)), 1)
    else:
        # If grid power is positive (importing), we're using all PV production
        return 100.0
    

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sigenergy calculated sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    entities = []

    # Set plant name
    plant_name = config_entry.data[CONF_NAME]

    # Add plant calculated sensors
    for description in PLANT_CALCULATED_SENSORS:
        entities.append(
            SigenergyCalculatedSensor(
                coordinator=coordinator,
                description=description,
                name=f"{plant_name} {description.name}",
                device_type=DEVICE_TYPE_PLANT,
                device_id=None,
                device_name=plant_name,
            )
        )

    # Add inverter calculated sensors
    inverter_no = 0
    for inverter_id in coordinator.hub.inverter_slave_ids:
        inverter_name = f"Sigen { f'{plant_name.split()[-1] } ' if plant_name.split()[-1].isdigit() else ''}Inverter{'' if inverter_no == 0 else f' {inverter_no}'}"
        _LOGGER.debug("Adding calculated sensors for inverter %s with inverter_no %s as %s", inverter_id, inverter_no, inverter_name)
        for description in INVERTER_CALCULATED_SENSORS:
            entities.append(
                SigenergyCalculatedSensor(
                    coordinator=coordinator,
                    description=description,
                    name=f"{inverter_name} {description.name}",
                    device_type=DEVICE_TYPE_INVERTER,
                    device_id=inverter_id,
                    device_name=inverter_name,
                )
            )
        inverter_no += 1

    async_add_entities(entities)


class SigenergyCalculatedSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sigenergy calculated sensor."""

    entity_description: SigenCalculatedSensorEntityDescription

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        description: SigenCalculatedSensorEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[int],
        device_name: Optional[str] = "",
    ) -> None:
        """Initialize the calculated sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = name
        self._device_type = device_type
        self._device_id = device_id

        # Get the device number if any as a string for use in names
        device_number_str = device_name.split()[-1]
        device_number_str = f" {device_number_str}" if device_number_str.isdigit() else ""

        # Set unique ID with "calculated_" prefix to avoid conflicts with regular sensors
        if device_type == DEVICE_TYPE_PLANT:
            self._attr_unique_id = f"{coordinator.hub.config_entry.entry_id}_{device_type}_calculated_{description.key}"
        else:
            self._attr_unique_id = f"{coordinator.hub.config_entry.entry_id}_{device_type}_{device_number_str}_calculated_{description.key}"

        # Set device info
        if device_type == DEVICE_TYPE_PLANT:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_plant")},
                name=device_name,
                manufacturer="Sigenergy",
                model="Energy Storage System",
                via_device=(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_plant"),
            )
        elif device_type == DEVICE_TYPE_INVERTER:
            # Get model and serial number if available
            model = None
            serial_number = None
            if coordinator.data and "inverters" in coordinator.data:
                inverter_data = coordinator.data["inverters"].get(device_id, {})
                model = inverter_data.get("model_type")
                serial_number = inverter_data.get("serial_number")

            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_{str(device_name).lower().replace(' ', '_')}")},
                name=device_name,
                manufacturer="Sigenergy",
                model=model,
                serial_number=serial_number,
                via_device=(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_plant"),
            )

    @property
    def native_value(self) -> Any:
        """Return the calculated value of the sensor."""
        if self.coordinator.data is None:
            return STATE_UNKNOWN
            
        try:
            value = self.entity_description.calculate_value_fn(self.coordinator.data, self._device_id)
            if value is None:
                return None
            return value
        except Exception as ex:
            _LOGGER.error("Error calculating value for %s: %s", self.name, ex)
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        if self._device_type == DEVICE_TYPE_PLANT:
            return self.coordinator.data is not None and "plant" in self.coordinator.data
        elif self._device_type == DEVICE_TYPE_INVERTER:
            return (
                self.coordinator.data is not None
                and "inverters" in self.coordinator.data
                and self._device_id in self.coordinator.data["inverters"]
            )
            
        return False