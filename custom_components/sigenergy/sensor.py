"""Sensor platform for Sigenergy Energy Storage System integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

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
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEVICE_TYPE_AC_CHARGER,
    DEVICE_TYPE_INVERTER,
    DEVICE_TYPE_PLANT,
    DOMAIN,
    RunningState,
)
from .coordinator import SigenergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class SigenergySensorEntityDescription(SensorEntityDescription):
    """Class describing Sigenergy sensor entities."""

    entity_registry_enabled_default: bool = True


PLANT_SENSORS = [
    SensorEntityDescription(
        key="ems_work_mode",
        name="EMS Work Mode",
        icon="mdi:cog",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: data["plant"].get("ems_work_mode"),
    ),
    SensorEntityDescription(
        key="grid_sensor_status",
        name="Grid Sensor Status",
        icon="mdi:power-plug",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: "Connected" if data["plant"].get("grid_sensor_status") == 1 else "Not Connected",
    ),
    SensorEntityDescription(
        key="grid_sensor_active_power",
        name="Grid Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, _: data["plant"].get("grid_sensor_active_power"),
    ),
    SensorEntityDescription(
        key="grid_sensor_reactive_power",
        name="Grid Reactive Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, _: data["plant"].get("grid_sensor_reactive_power"),
    ),
    SensorEntityDescription(
        key="on_off_grid_status",
        name="Grid Connection Status",
        icon="mdi:transmission-tower",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: {
            0: "On Grid",
            1: "Off Grid (Auto)",
            2: "Off Grid (Manual)",
        }.get(data["plant"].get("on_off_grid_status"), STATE_UNKNOWN),
    ),
    SensorEntityDescription(
        key="ess_soc",
        name="Battery State of Charge",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, _: data["plant"].get("ess_soc"),
    ),
    SensorEntityDescription(
        key="ess_soh",
        name="Battery State of Health",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: data["plant"].get("ess_soh"),
    ),
    SensorEntityDescription(
        key="plant_active_power",
        name="Plant Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, _: data["plant"].get("plant_active_power"),
    ),
    SensorEntityDescription(
        key="plant_reactive_power",
        name="Plant Reactive Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, _: data["plant"].get("plant_reactive_power"),
    ),
    SensorEntityDescription(
        key="photovoltaic_power",
        name="PV Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, _: data["plant"].get("photovoltaic_power"),
    ),
    SensorEntityDescription(
        key="ess_power",
        name="Battery Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, _: data["plant"].get("ess_power"),
    ),
    SensorEntityDescription(
        key="ess_available_max_charging_power",
        name="Available Max Charging Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: data["plant"].get("ess_available_max_charging_power"),
    ),
    SensorEntityDescription(
        key="ess_available_max_discharging_power",
        name="Available Max Discharging Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: data["plant"].get("ess_available_max_discharging_power"),
    ),
    SensorEntityDescription(
        key="plant_running_state",
        name="Plant Running State",
        icon="mdi:power",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: {
            RunningState.STANDBY: "Standby",
            RunningState.RUNNING: "Running",
            RunningState.FAULT: "Fault",
            RunningState.SHUTDOWN: "Shutdown",
        }.get(data["plant"].get("plant_running_state"), STATE_UNKNOWN),
    ),
    SensorEntityDescription(
        key="ess_available_max_charging_capacity",
        name="Available Max Charging Capacity",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: data["plant"].get("ess_available_max_charging_capacity"),
    ),
    SensorEntityDescription(
        key="ess_available_max_discharging_capacity",
        name="Available Max Discharging Capacity",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: data["plant"].get("ess_available_max_discharging_capacity"),
    ),
    SensorEntityDescription(
        key="ess_rated_energy_capacity",
        name="Rated Energy Capacity",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: data["plant"].get("ess_rated_energy_capacity"),
    ),
    SensorEntityDescription(
        key="ess_charge_cut_off_soc",
        name="Charge Cut-Off SOC",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: data["plant"].get("ess_charge_cut_off_soc"),
    ),
    SensorEntityDescription(
        key="ess_discharge_cut_off_soc",
        name="Discharge Cut-Off SOC",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, _: data["plant"].get("ess_discharge_cut_off_soc"),
    ),
]

INVERTER_SENSORS = [
    SensorEntityDescription(
        key="model_type",
        name="Model Type",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("model_type"),
    ),
    SensorEntityDescription(
        key="serial_number",
        name="Serial Number",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("serial_number"),
    ),
    SensorEntityDescription(
        key="machine_firmware_version",
        name="Firmware Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("machine_firmware_version"),
    ),
    SensorEntityDescription(
        key="rated_active_power",
        name="Rated Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("rated_active_power"),
    ),
    SensorEntityDescription(
        key="ess_daily_charge_energy",
        name="Daily Charge Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_daily_charge_energy"),
    ),
    SensorEntityDescription(
        key="ess_accumulated_charge_energy",
        name="Total Charge Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_accumulated_charge_energy"),
    ),
    SensorEntityDescription(
        key="ess_daily_discharge_energy",
        name="Daily Discharge Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_daily_discharge_energy"),
    ),
    SensorEntityDescription(
        key="ess_accumulated_discharge_energy",
        name="Total Discharge Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_accumulated_discharge_energy"),
    ),
    SensorEntityDescription(
        key="running_state",
        name="Running State",
        icon="mdi:power",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: {
            RunningState.STANDBY: "Standby",
            RunningState.RUNNING: "Running",
            RunningState.FAULT: "Fault",
            RunningState.SHUTDOWN: "Shutdown",
        }.get(data["inverters"].get(inverter_id, {}).get("running_state"), STATE_UNKNOWN),
    ),
    SensorEntityDescription(
        key="active_power",
        name="Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("active_power"),
    ),
    SensorEntityDescription(
        key="reactive_power",
        name="Reactive Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("reactive_power"),
    ),
    SensorEntityDescription(
        key="ess_charge_discharge_power",
        name="Battery Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_charge_discharge_power"),
    ),
    SensorEntityDescription(
        key="ess_battery_soc",
        name="Battery State of Charge",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_battery_soc"),
    ),
    SensorEntityDescription(
        key="ess_battery_soh",
        name="Battery State of Health",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_battery_soh"),
    ),
    SensorEntityDescription(
        key="ess_average_cell_temperature",
        name="Battery Average Cell Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_average_cell_temperature"),
    ),
    SensorEntityDescription(
        key="ess_average_cell_voltage",
        name="Battery Average Cell Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_average_cell_voltage"),
    ),
    SensorEntityDescription(
        key="ess_maximum_battery_temperature",
        name="Battery Maximum Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_maximum_battery_temperature"),
    ),
    SensorEntityDescription(
        key="ess_minimum_battery_temperature",
        name="Battery Minimum Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_minimum_battery_temperature"),
    ),
    SensorEntityDescription(
        key="ess_maximum_battery_cell_voltage",
        name="Battery Maximum Cell Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_maximum_battery_cell_voltage"),
    ),
    SensorEntityDescription(
        key="ess_minimum_battery_cell_voltage",
        name="Battery Minimum Cell Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("ess_minimum_battery_cell_voltage"),
    ),
    SensorEntityDescription(
        key="grid_frequency",
        name="Grid Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("grid_frequency"),
    ),
    SensorEntityDescription(
        key="pcs_internal_temperature",
        name="PCS Internal Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("pcs_internal_temperature"),
    ),
    SensorEntityDescription(
        key="output_type",
        name="Output Type",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: {
            0: "L/N",
            1: "L1/L2/L3",
            2: "L1/L2/L3/N",
            3: "L1/L2/N",
        }.get(data["inverters"].get(inverter_id, {}).get("output_type"), STATE_UNKNOWN),
    ),
    SensorEntityDescription(
        key="phase_a_voltage",
        name="Phase A Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("phase_a_voltage"),
    ),
    SensorEntityDescription(
        key="phase_b_voltage",
        name="Phase B Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("phase_b_voltage"),
    ),
    SensorEntityDescription(
        key="phase_c_voltage",
        name="Phase C Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("phase_c_voltage"),
    ),
    SensorEntityDescription(
        key="phase_a_current",
        name="Phase A Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("phase_a_current"),
    ),
    SensorEntityDescription(
        key="phase_b_current",
        name="Phase B Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("phase_b_current"),
    ),
    SensorEntityDescription(
        key="phase_c_current",
        name="Phase C Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("phase_c_current"),
    ),
    SensorEntityDescription(
        key="power_factor",
        name="Power Factor",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("power_factor"),
    ),
    SensorEntityDescription(
        key="pv_power",
        name="PV Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("pv_power"),
    ),
    SensorEntityDescription(
        key="insulation_resistance",
        name="Insulation Resistance",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("insulation_resistance"),
    ),
]

AC_CHARGER_SENSORS = [
    SensorEntityDescription(
        key="system_state",
        name="System State",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, ac_charger_id: {
            0: "System Init",
            1: "A1/A2",
            2: "B1",
            3: "B2",
            4: "C1",
            5: "C2",
            6: "F",
            7: "E",
        }.get(data["ac_chargers"].get(ac_charger_id, {}).get("system_state"), STATE_UNKNOWN),
    ),
    SensorEntityDescription(
        key="total_energy_consumed",
        name="Total Energy Consumed",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data, ac_charger_id: data["ac_chargers"].get(ac_charger_id, {}).get("total_energy_consumed"),
    ),
    SensorEntityDescription(
        key="charging_power",
        name="Charging Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, ac_charger_id: data["ac_chargers"].get(ac_charger_id, {}).get("charging_power"),
    ),
    SensorEntityDescription(
        key="rated_power",
        name="Rated Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, ac_charger_id: data["ac_chargers"].get(ac_charger_id, {}).get("rated_power"),
    ),
    SensorEntityDescription(
        key="rated_current",
        name="Rated Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, ac_charger_id: data["ac_chargers"].get(ac_charger_id, {}).get("rated_current"),
    ),
    SensorEntityDescription(
        key="rated_voltage",
        name="Rated Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, ac_charger_id: data["ac_chargers"].get(ac_charger_id, {}).get("rated_voltage"),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sigenergy sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    entities = []

    # Add plant sensors
    plant_name = config_entry.data[CONF_NAME]
    for description in PLANT_SENSORS:
        entities.append(
            SigenergySensor(
                coordinator=coordinator,
                description=description,
                name=f"{plant_name} {description.name}",
                device_type=DEVICE_TYPE_PLANT,
                device_id=None,
            )
        )

    # Add inverter sensors
    for inverter_id in coordinator.hub.inverter_slave_ids:
        for description in INVERTER_SENSORS:
            entities.append(
                SigenergySensor(
                    coordinator=coordinator,
                    description=description,
                    name=f"{plant_name} Inverter {inverter_id} {description.name}",
                    device_type=DEVICE_TYPE_INVERTER,
                    device_id=inverter_id,
                )
            )

    # Add AC charger sensors
    for ac_charger_id in coordinator.hub.ac_charger_slave_ids:
        for description in AC_CHARGER_SENSORS:
            entities.append(
                SigenergySensor(
                    coordinator=coordinator,
                    description=description,
                    name=f"{plant_name} AC Charger {ac_charger_id} {description.name}",
                    device_type=DEVICE_TYPE_AC_CHARGER,
                    device_id=ac_charger_id,
                )
            )

    async_add_entities(entities)


class SigenergySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sigenergy sensor."""

    entity_description: SigenergySensorEntityDescription

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        description: SigenergySensorEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[int],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = name
        self._device_type = device_type
        self._device_id = device_id
        
        # Set unique ID
        if device_type == DEVICE_TYPE_PLANT:
            self._attr_unique_id = f"{coordinator.hub.host}_{device_type}_{description.key}"
        else:
            self._attr_unique_id = f"{coordinator.hub.host}_{device_type}_{device_id}_{description.key}"
        
        # Set device info
        if device_type == DEVICE_TYPE_PLANT:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{coordinator.hub.host}_plant")},
                name=name.split(" ", 1)[0],  # Use plant name as device name
                manufacturer="Sigenergy",
                model="Energy Storage System",
                via_device=(DOMAIN, f"{coordinator.hub.host}"),
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
                identifiers={(DOMAIN, f"{coordinator.hub.host}_inverter_{device_id}")},
                name=f"Inverter {device_id}",
                manufacturer="Sigenergy",
                model=model,
                serial_number=serial_number,
                via_device=(DOMAIN, f"{coordinator.hub.host}_plant"),
            )
        elif device_type == DEVICE_TYPE_AC_CHARGER:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{coordinator.hub.host}_ac_charger_{device_id}")},
                name=f"AC Charger {device_id}",
                manufacturer="Sigenergy",
                model="AC Charger",
                via_device=(DOMAIN, f"{coordinator.hub.host}_plant"),
            )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return STATE_UNKNOWN
            
        value = None
        if self._device_type == DEVICE_TYPE_PLANT:
            value = self.entity_description.value_fn(self.coordinator.data, None)
        else:
            value = self.entity_description.value_fn(self.coordinator.data, self._device_id)
            
        # Handle None, "Unknown", or other non-numeric values for numeric sensors
        if value is None:
            return STATE_UNKNOWN
            
        # If this is a numeric sensor (with device_class) and the value is a string like "Unknown"
        if (hasattr(self.entity_description, "device_class") and 
            self.entity_description.device_class in [
                SensorDeviceClass.POWER, 
                SensorDeviceClass.ENERGY,
                SensorDeviceClass.TEMPERATURE,
                SensorDeviceClass.VOLTAGE,
                SensorDeviceClass.CURRENT,
                SensorDeviceClass.BATTERY,
                SensorDeviceClass.FREQUENCY,
            ] and
            isinstance(value, str) and
            not value.replace('.', '', 1).replace('-', '', 1).isdigit()
        ):
            return STATE_UNKNOWN
            
        return value

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
        elif self._device_type == DEVICE_TYPE_AC_CHARGER:
            return (
                self.coordinator.data is not None
                and "ac_chargers" in self.coordinator.data
                and self._device_id in self.coordinator.data["ac_chargers"]
            )
            
        return False
