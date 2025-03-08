"""Sensor platform for Sigenergy ESS integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEVICE_TYPE_AC_CHARGER,
    DEVICE_TYPE_DC_CHARGER,
    DEVICE_TYPE_INVERTER,
    DEVICE_TYPE_PLANT,
    DOMAIN,
    EMSWorkMode,
    RunningState,
)
from .coordinator import SigenergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class SigenergySensorEntityDescription(SensorEntityDescription):
    """Class describing Sigenergy sensor entities."""

    entity_registry_enabled_default: bool = True
    value_fn: Optional[Callable[[Any], Any]] = None
    extra_fn_data: Optional[bool] = False  # Flag to indicate if value_fn needs coordinator data

def minutes_to_gmt(minutes: Any) -> str:
    """Convert minutes offset to GMT format."""
    if minutes is None:
        return None
    try:
        hours = int(minutes) // 60
        return f"GMT{'+' if hours >= 0 else ''}{hours}"
    except (ValueError, TypeError):
        return None

def epoch_to_datetime(epoch: Any, coordinator_data: Optional[dict] = None) -> datetime:
    """Convert epoch timestamp to datetime using system's configured timezone."""
    if epoch is None or coordinator_data is None:
        return None
    try:
        # Get timezone offset from plant data
        tz_offset = coordinator_data.get("plant", {}).get("plant_system_timezone")
        if tz_offset is None:
            return datetime.fromtimestamp(int(epoch), tz=timezone.utc)
            
        # Create timezone with offset
        tz_minutes = int(tz_offset)
        tz_hours = tz_minutes // 60
        tz_remaining_minutes = tz_minutes % 60
        tz_delta = timezone(timedelta(hours=tz_hours, minutes=tz_remaining_minutes))
        
        # Convert timestamp using the system's timezone
        return datetime.fromtimestamp(int(epoch), tz=tz_delta)
    except (ValueError, TypeError):
        return None


PLANT_SENSORS = [
    # System time and timezone
    SigenergySensorEntityDescription(
        key="plant_system_time",
        name="System Time",
        icon="mdi:clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=epoch_to_datetime,
        extra_fn_data=True,  # Indicates that this sensor needs coordinator data for timestamp conversion
    ),
    SigenergySensorEntityDescription(
        key="plant_system_timezone",
        name="System Timezone",
        icon="mdi:earth",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=minutes_to_gmt,
    ),
    # EMS Work Mode sensor with value mapping
    SigenergySensorEntityDescription(
        key="plant_ems_work_mode",
        name="EMS Work Mode",
        icon="mdi:home-battery",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda value: {
            EMSWorkMode.MAX_SELF_CONSUMPTION: "Maximum Self Consumption",
            EMSWorkMode.AI_MODE: "AI Mode",
            EMSWorkMode.TOU: "Time of Use",
            EMSWorkMode.REMOTE_EMS: "Remote EMS",
        }.get(value, "Unknown"),
    ),
    SensorEntityDescription(
        key="plant_grid_sensor_status",
        name="Grid Sensor Status",
        icon="mdi:power-plug",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_grid_sensor_active_power",
        name="Grid Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_grid_sensor_reactive_power",
        name="Grid Reactive Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_on_off_grid_status",
        name="Grid Connection Status",
        icon="mdi:transmission-tower",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Max power metrics
    SensorEntityDescription(
        key="plant_max_active_power",
        name="Max Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_max_apparent_power",
        name="Max Apparent Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_ess_soc",
        name="Battery State of Charge",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Phase-specific active power
    SensorEntityDescription(
        key="plant_phase_a_active_power",
        name="Phase A Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_phase_b_active_power",
        name="Phase B Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_phase_c_active_power",
        name="Phase C Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Phase-specific reactive power
    SensorEntityDescription(
        key="plant_phase_a_reactive_power",
        name="Phase A Reactive Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_phase_b_reactive_power",
        name="Phase B Reactive Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_phase_c_reactive_power",
        name="Phase C Reactive Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Alarm registers
    SensorEntityDescription(
        key="plant_general_alarm1",
        name="General Alarm 1",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_general_alarm2",
        name="General Alarm 2",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_general_alarm3",
        name="General Alarm 3",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_general_alarm4",
        name="General Alarm 4",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_general_alarm5",
        name="General Alarm 5",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_active_power",
        name="Plant Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_reactive_power",
        name="Plant Reactive Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_photovoltaic_power",
        name="PV Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_ess_power",
        name="Battery Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_ess_available_max_charging_power",
        name="Available Max Charging Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_ess_available_max_discharging_power",
        name="Available Max Discharging Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_running_state",
        name="Plant Running State",
        icon="mdi:power",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Grid sensor phase-specific metrics
    SensorEntityDescription(
        key="plant_grid_sensor_phase_a_active_power",
        name="Grid Phase A Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_grid_sensor_phase_b_active_power",
        name="Grid Phase B Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_grid_sensor_phase_c_active_power",
        name="Grid Phase C Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_grid_sensor_phase_a_reactive_power",
        name="Grid Phase A Reactive Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_grid_sensor_phase_b_reactive_power",
        name="Grid Phase B Reactive Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="plant_grid_sensor_phase_c_reactive_power",
        name="Grid Phase C Reactive Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ESS rated power metrics
    SensorEntityDescription(
        key="plant_ess_rated_charging_power",
        name="ESS Rated Charging Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_ess_rated_discharging_power",
        name="ESS Rated Discharging Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_ess_available_max_charging_capacity",
        name="Available Max Charging Capacity",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_ess_available_max_discharging_capacity",
        name="Available Max Discharging Capacity",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_ess_rated_energy_capacity",
        name="Rated Energy Capacity",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_ess_charge_cut_off_soc",
        name="Charge Cut-Off SOC",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_ess_discharge_cut_off_soc",
        name="Discharge Cut-Off SOC",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="plant_ess_soh",
        name="Battery State of Health",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]

INVERTER_SENSORS = [
    # Power ratings
    SensorEntityDescription(
        key="inverter_model_type",
        name="Model Type",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_serial_number",
        name="Serial Number",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_machine_firmware_version",
        name="Firmware Version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_rated_active_power",
        name="Rated Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_max_apparent_power",
        name="Max Apparent Power",
        native_unit_of_measurement="kVA",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_max_active_power",
        name="Max Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_max_absorption_power",
        name="Max Absorption Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_rated_battery_capacity",
        name="Rated Battery Capacity",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_ess_rated_charge_power",
        name="ESS Rated Charge Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_ess_rated_discharge_power",
        name="ESS Rated Discharge Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_ess_daily_charge_energy",
        name="Daily Charge Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="inverter_ess_accumulated_charge_energy",
        name="Total Charge Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="inverter_ess_daily_discharge_energy",
        name="Daily Discharge Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="inverter_ess_accumulated_discharge_energy",
        name="Total Discharge Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="inverter_running_state",
        name="Running State",
        icon="mdi:power",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Power adjustment values
    SensorEntityDescription(
        key="inverter_max_active_power_adjustment_value",
        name="Max Active Power Adjustment",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_min_active_power_adjustment_value",
        name="Min Active Power Adjustment",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_max_reactive_power_adjustment_value_fed",
        name="Max Reactive Power Fed",
        native_unit_of_measurement="kVar",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_max_reactive_power_adjustment_value_absorbed",
        name="Max Reactive Power Absorbed",
        native_unit_of_measurement="kVar",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_active_power",
        name="Active Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_reactive_power",
        name="Reactive Power",
        native_unit_of_measurement="kVar",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_ess_charge_discharge_power",
        name="Battery Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # Battery power metrics
    SensorEntityDescription(
        key="inverter_ess_max_battery_charge_power",
        name="Max Battery Charge Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_ess_max_battery_discharge_power",
        name="Max Battery Discharge Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_ess_available_battery_charge_energy",
        name="Available Battery Charge Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_ess_available_battery_discharge_energy",
        name="Available Battery Discharge Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_ess_battery_soc",
        name="Battery State of Charge",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_ess_battery_soh",
        name="Battery State of Health",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_ess_average_cell_temperature",
        name="Battery Average Cell Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_ess_average_cell_voltage",
        name="Battery Average Cell Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_ess_maximum_battery_temperature",
        name="Battery Maximum Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_ess_minimum_battery_temperature",
        name="Battery Minimum Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_ess_maximum_battery_cell_voltage",
        name="Battery Maximum Cell Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_ess_minimum_battery_cell_voltage",
        name="Battery Minimum Cell Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Alarm registers
    SensorEntityDescription(
        key="inverter_alarm1",
        name="Alarm 1",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_alarm2",
        name="Alarm 2",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_alarm3",
        name="Alarm 3",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_alarm4",
        name="Alarm 4",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_alarm5",
        name="Alarm 5",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_grid_frequency",
        name="Grid Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_pcs_internal_temperature",
        name="PCS Internal Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_output_type",
        name="Output Type",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Grid metrics
    SensorEntityDescription(
        key="inverter_rated_grid_voltage",
        name="Rated Grid Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_rated_grid_frequency",
        name="Rated Grid Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Line voltages
    SensorEntityDescription(
        key="inverter_ab_line_voltage",
        name="A-B Line Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_bc_line_voltage",
        name="B-C Line Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_ca_line_voltage",
        name="C-A Line Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_phase_a_voltage",
        name="Phase A Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_phase_b_voltage",
        name="Phase B Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_phase_c_voltage",
        name="Phase C Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_phase_a_current",
        name="Phase A Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_phase_b_current",
        name="Phase B Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_phase_c_current",
        name="Phase C Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_power_factor",
        name="Power Factor",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # PV system metrics
    SensorEntityDescription(
        key="inverter_pack_count",
        name="PACK Count",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_pv_string_count",
        name="PV String Count",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_mppt_count",
        name="MPPT Count",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="inverter_pv_power",
        name="PV Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="inverter_insulation_resistance",
        name="Insulation Resistance",
        native_unit_of_measurement="MΩ",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SigenergySensorEntityDescription(
        key="inverter_startup_time",
        name="Startup Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=epoch_to_datetime,
        extra_fn_data=True,  # Indicates that this sensor needs coordinator data for timestamp conversion
    ),
    SigenergySensorEntityDescription(
        key="inverter_shutdown_time",
        name="Shutdown Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=epoch_to_datetime,
        extra_fn_data=True,  # Indicates that this sensor needs coordinator data for timestamp conversion
    ),
]
AC_CHARGER_SENSORS = [
    SensorEntityDescription(
        key="ac_charger_system_state",
        name="System State",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="ac_charger_total_energy_consumed",
        name="Total Energy Consumed",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="ac_charger_charging_power",
        name="Charging Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="ac_charger_rated_power",
        name="Rated Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="ac_charger_rated_current",
        name="Rated Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="ac_charger_rated_voltage",
        name="Rated Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Additional AC charger metrics
    SensorEntityDescription(
        key="ac_charger_input_breaker_rated_current",
        name="Input Breaker Rated Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Alarm registers
    SensorEntityDescription(
        key="ac_charger_alarm1",
        name="Alarm 1",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="ac_charger_alarm2",
        name="Alarm 2",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="ac_charger_alarm3",
        name="Alarm 3",
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]

DC_CHARGER_SENSORS = [
    SensorEntityDescription(
        key="dc_charger_vehicle_battery_voltage",
        name="DC Charger Vehicle Battery Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="dc_charger_charging_current",
        name="DC Charger Charging Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="dc_charger_output_power",
        name="DC Charger Output Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="dc_charger_vehicle_soc",
        name="DC Charger Vehicle SOC",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="dc_charger_current_charging_capacity",
        name="DC Charger Current Charging Capacity (Single Time)",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
    ),
    SensorEntityDescription(
        key="dc_charger_current_charging_duration",
        name="DC Charger Current Charging Duration (Single Time)",
        icon="mdi:timer",
        state_class=SensorStateClass.MEASUREMENT,
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

    _LOGGER.debug("Setting up sensors for %s", config_entry.data[CONF_NAME])
    _LOGGER.debug("Inverters: %s", coordinator.hub.inverter_slave_ids)
    _LOGGER.debug("config_entry: %s", config_entry)
    _LOGGER.debug("coordinator: %s", coordinator)
    _LOGGER.debug("config_entry.data: %s", config_entry.data)
    _LOGGER.debug("coordinator.hub: %s", coordinator.hub)
    _LOGGER.debug("coordinator.hub.config_entry: %s", coordinator.hub.config_entry)
    _LOGGER.debug("coordinator.hub.config_entry.data: %s", coordinator.hub.config_entry.data)
    _LOGGER.debug("coordinator.hub.config_entry.entry_id: %s", coordinator.hub.config_entry.entry_id)

    # Set plant name
    plant_name : str = config_entry.data[CONF_NAME]

    # Add plant sensors
    for description in PLANT_SENSORS:
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

    # Add inverter sensors
    inverter_no = 0
    for inverter_id in coordinator.hub.inverter_slave_ids:
        inverter_name = f"Sigen { f'{plant_name.split()[-1] } ' if plant_name.split()[-1].isdigit() else ''}Inverter{'' if inverter_no == 0 else f' {inverter_no}'}"
        _LOGGER.debug("Adding inverter %s with inverter_no %s as %s", inverter_id, inverter_no, inverter_name)
        for description in INVERTER_SENSORS:
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
        inverter_no += 1

    # Add AC charger sensors
    ac_charger_no = 0
    for ac_charger_id in coordinator.hub.ac_charger_slave_ids:
        ac_charger_name=f"Sigen { f'{plant_name.split()[-1] } ' if plant_name.split()[-1].isdigit() else ''}AC Charger{'' if ac_charger_no == 0 else f' {ac_charger_no}'}"
        _LOGGER.debug("Adding AC charger %s with ac_charger_no %s as %s", ac_charger_id, ac_charger_no, ac_charger_name)
        for description in AC_CHARGER_SENSORS:
            entities.append(
                SigenergySensor(
                    coordinator=coordinator,
                    description=description,
                    name=f"{ac_charger_name} {description.name}",
                    device_type=DEVICE_TYPE_AC_CHARGER,
                    device_id=ac_charger_id,
                    device_name=ac_charger_name,
                )
            )
        ac_charger_no += 1

    # Add DC charger sensors
    dc_charger_no = 0
    for dc_charger_id in coordinator.hub.dc_charger_slave_ids:
        dc_charger_name=f"Sigen { f'{plant_name.split()[-1] } ' if plant_name.split()[-1].isdigit() else ''}DC Charger{'' if dc_charger_no == 0 else f' {dc_charger_no}'}"
        _LOGGER.debug("Adding DC charger %s with dc_charger_no %s as %s", dc_charger_id, dc_charger_no, dc_charger_name)
        for description in DC_CHARGER_SENSORS:
            entities.append(
                SigenergySensor(
                    coordinator=coordinator,
                    description=description,
                    name=f"{dc_charger_name} {description.name}",
                    device_type=DEVICE_TYPE_DC_CHARGER,
                    device_id=dc_charger_id,
                    device_name=dc_charger_name,
                )
            )
        dc_charger_no += 1

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
        device_name: Optional[str] ="",
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = name
        self._device_type = device_type
        self._device_id = device_id

        # Get the device number if any as a string for use in names
        device_number_str = device_name.split()[-1]
        device_number_str = f" {device_number_str}" if device_number_str.isdigit() else ""

        # Set unique ID
        if device_type == DEVICE_TYPE_PLANT:
            # self._attr_unique_id = f"{coordinator.hub.host}_{device_type}_{description.key}"
            self._attr_unique_id = f"{coordinator.hub.config_entry.entry_id}_{device_type}_{description.key}"
        else:
            # self._attr_unique_id = f"{coordinator.hub.host}_{device_type}_{device_id}_{description.key}"
            # Used for testing in development to allow multiple sensors with the same unique ID
            self._attr_unique_id = f"{coordinator.hub.config_entry.entry_id}_{device_type}_{device_number_str}_{description.key}"

        # Set device info
        if device_type == DEVICE_TYPE_PLANT:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_plant")},
                # name=f"{hub.name} qqq", #.split(" ", 1)[0],  # Use plant name as device name
                name=device_name,
                manufacturer="Sigenergy",
                model="Energy Storage System",
                # via_device=(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_plant"),
            )
        elif device_type == DEVICE_TYPE_INVERTER:
            # Get model and serial number if available
            model = None
            serial_number = None
            sw_version = None
            if coordinator.data and "inverters" in coordinator.data:
                inverter_data = coordinator.data["inverters"].get(device_id, {})
                model = inverter_data.get("inverter_model_type")
                serial_number = inverter_data.get("inverter_serial_number")
                sw_version = inverter_data.get("inverter_machine_firmware_version")

            self._attr_device_info = DeviceInfo(
                # identifiers={(DOMAIN, f"{coordinator.hub.host}_inverter_{device_id}")},
                identifiers={(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_{str(device_name).lower().replace(' ', '_')}")},
                name=device_name,
                manufacturer="Sigenergy",
                model=model,
                serial_number=serial_number,
                sw_version=sw_version,
                via_device=(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_plant"),
            )
        elif device_type == DEVICE_TYPE_AC_CHARGER:
            self._attr_device_info = DeviceInfo(
                # identifiers={(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_ac_charger_{device_id}")},
                identifiers={(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_{str(device_name).lower().replace(' ', '_')}")},
                name=device_name,
                manufacturer="Sigenergy",
                model="AC Charger",
                via_device=(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_plant"),
            )
        elif device_type == DEVICE_TYPE_DC_CHARGER:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_{str(device_name).lower().replace(' ', '_')}")},
                name=device_name,
                manufacturer="Sigenergy",
                model="DC Charger",
                via_device=(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_plant"),
            )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return STATE_UNKNOWN
            
        if self._device_type == DEVICE_TYPE_PLANT:
            # Use the key directly with plant_ prefix already included
            value = self.coordinator.data["plant"].get(self.entity_description.key)
        elif self._device_type == DEVICE_TYPE_INVERTER:
            # Use the key directly with inverter_ prefix already included
            value = self.coordinator.data["inverters"].get(self._device_id, {}).get(
                self.entity_description.key
            )
        elif self._device_type == DEVICE_TYPE_AC_CHARGER:
            # Use the key directly with ac_charger_ prefix already included
            value = self.coordinator.data["ac_chargers"].get(self._device_id, {}).get(
                self.entity_description.key
            )
        elif self._device_type == DEVICE_TYPE_DC_CHARGER:
            # Use the key directly with dc_charger_ prefix already included
            value = self.coordinator.data["dc_chargers"].get(self._device_id, {}).get(
                self.entity_description.key
            )
        else:
            value = None

        if value is None or str(value).lower() == "unknown":
            if (self.entity_description.native_unit_of_measurement is not None
                or self.entity_description.state_class == SensorStateClass.MEASUREMENT):
                return None
            else:
                return STATE_UNKNOWN
                
        # Apply value_fn if available
        if hasattr(self.entity_description, "value_fn") and self.entity_description.value_fn is not None:
            # Pass coordinator data if needed by the value_fn
            if hasattr(self.entity_description, "extra_fn_data") and self.entity_description.extra_fn_data:
                transformed_value = self.entity_description.value_fn(value, self.coordinator.data)
            else:
                transformed_value = self.entity_description.value_fn(value)
                
            if transformed_value is not None:
                return transformed_value

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
            _LOGGER.debug("inverter_running_state value: %s", value)
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
        elif self._device_type == DEVICE_TYPE_DC_CHARGER:
            return (
                self.coordinator.data is not None
                and "dc_chargers" in self.coordinator.data
                and self._device_id in self.coordinator.data["dc_chargers"]
            )
            
        return False
