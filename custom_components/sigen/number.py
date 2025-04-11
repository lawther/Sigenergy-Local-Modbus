"""Number platform for Sigenergy ESS integration."""
from __future__ import annotations

import logging
import asyncio
from typing import Coroutine
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    EntityCategory,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_SLAVE_ID, # Import CONF_SLAVE_ID
    DEVICE_TYPE_AC_CHARGER,
    DEVICE_TYPE_DC_CHARGER,
    DEVICE_TYPE_INVERTER,
    DEVICE_TYPE_PLANT,
    DOMAIN,
)
from .coordinator import SigenergyDataUpdateCoordinator
from .modbus import SigenergyModbusError
from .common import(generate_device_name, generate_sigen_entity, generate_unique_entity_id)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SigenergyNumberEntityDescription(NumberEntityDescription):
    """Class describing Sigenergy number entities."""

    # Provide default lambdas instead of None to satisfy type checker
    # The second argument 'identifier' will be device_name for inverters, device_id otherwise
    value_fn: Callable[[Dict[str, Any], Optional[Any]], float] = lambda data, identifier: 0.0
    # Make set_value_fn async and update type hint
    set_value_fn: Callable[[Any, Optional[Any], float], Coroutine[Any, Any, None]] = lambda hub, identifier, value: asyncio.sleep(0) # Placeholder async lambda
    available_fn: Callable[[Dict[str, Any], Optional[Any]], bool] = lambda data, _: True
    entity_registry_enabled_default: bool = True


PLANT_NUMBERS = [
    SigenergyNumberEntityDescription(
        key="plant_active_power_fixed_target",
        name="Active Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=-100,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_active_power_fixed_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_active_power_fixed_target", value), # Already returns awaitable
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_reactive_power_fixed_target",
        name="Reactive Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement="kVar",
        native_min_value=-100,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_reactive_power_fixed_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_reactive_power_fixed_target", value), # Already returns awaitable
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_active_power_percentage_target",
        name="Active Power Percentage Adjustment",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-100,
        native_max_value=100,
        native_step=0.01,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_active_power_percentage_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_active_power_percentage_target", value), # Already returns awaitable
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_qs_ratio_target",
        name="Q/S Adjustment",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-60,
        native_max_value=60,
        native_step=0.01,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_qs_ratio_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_qs_ratio_target", value), # Already returns awaitable
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_power_factor_target",
        name="Power Factor Adjustment",
        icon="mdi:sine-wave",
        native_min_value=-1,
        native_max_value=1,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_power_factor_target", 0) / 1000,
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_power_factor_target", value), # Already returns awaitable
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_ess_max_charging_limit",
        name="ESS Max Charging Limit",
        icon="mdi:battery-charging",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_ess_max_charging_limit", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_ess_max_charging_limit", value), # Already returns awaitable
    ),
    SigenergyNumberEntityDescription(
        key="plant_ess_max_discharging_limit",
        name="ESS Max Discharging Limit",
        icon="mdi:battery-charging-outline",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_ess_max_discharging_limit", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_ess_max_discharging_limit", value), # Already returns awaitable
    ),
    SigenergyNumberEntityDescription(
        key="plant_pv_max_power_limit",
        name="PV Max Power Limit",
        icon="mdi:solar-power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_pv_max_power_limit", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_pv_max_power_limit", value), # Already returns awaitable
    ),
    SigenergyNumberEntityDescription(
        key="plant_grid_point_maximum_export_limitation",
        name="Grid Export Limitation",
        icon="mdi:transmission-tower-export",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_grid_point_maximum_export_limitation", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_grid_point_maximum_export_limitation", value), # Already returns awaitable
    ),
    SigenergyNumberEntityDescription(
        key="plant_grid_maximum_import_limitation",
        name="Grid Import Limitation",
        icon="mdi:transmission-tower-import",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_grid_maximum_import_limitation", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_grid_maximum_import_limitation", value), # Already returns awaitable
    ),
    SigenergyNumberEntityDescription(
        key="plant_pcs_maximum_export_limitation",
        name="PCS Export Limitation",
        icon="mdi:transmission-tower-export",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_pcs_maximum_export_limitation", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_pcs_maximum_export_limitation", value), # Already returns awaitable
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_pcs_maximum_import_limitation",
        name="PCS Import Limitation",
        icon="mdi:transmission-tower-import",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_pcs_maximum_import_limitation", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_pcs_maximum_import_limitation", value), # Already returns awaitable
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_phase_a_active_power_fixed_target",
        name="Phase A Active Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=-100,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_phase_a_active_power_fixed_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_phase_a_active_power_fixed_target", value), # Already returns awaitable
        available_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1,
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_phase_b_active_power_fixed_target",
        name="Phase B Active Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=-100,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_phase_b_active_power_fixed_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_phase_b_active_power_fixed_target", value), # Already returns awaitable
        available_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1,
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_phase_c_active_power_fixed_target",
        name="Phase C Active Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=-100,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_phase_c_active_power_fixed_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_phase_c_active_power_fixed_target", value), # Already returns awaitable
        available_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1,
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_phase_a_reactive_power_fixed_target",
        name="Phase A Reactive Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement="kVar",
        native_min_value=-100,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_phase_a_reactive_power_fixed_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_phase_a_reactive_power_fixed_target", value), # Already returns awaitable
        available_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1,
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_phase_b_reactive_power_fixed_target",
        name="Phase B Reactive Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement="kVar",
        native_min_value=-100,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_phase_b_reactive_power_fixed_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_phase_b_reactive_power_fixed_target", value), # Already returns awaitable
        available_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1,
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_phase_c_reactive_power_fixed_target",
        name="Phase C Reactive Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement="kVar",
        native_min_value=-100,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_phase_c_reactive_power_fixed_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_phase_c_reactive_power_fixed_target", value), # Already returns awaitable
        available_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1,
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_phase_a_active_power_percentage_target",
        name="Phase A Active Power Percentage",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-100,
        native_max_value=100,
        native_step=0.01,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_phase_a_active_power_percentage_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_phase_a_active_power_percentage_target", value), # Already returns awaitable
        available_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1,
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_phase_b_active_power_percentage_target",
        name="Phase B Active Power Percentage",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-100,
        native_max_value=100,
        native_step=0.01,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_phase_b_active_power_percentage_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_phase_b_active_power_percentage_target", value), # Already returns awaitable
        available_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1,
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_phase_c_active_power_percentage_target",
        name="Phase C Active Power Percentage",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-100,
        native_max_value=100,
        native_step=0.01,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_phase_c_active_power_percentage_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_phase_c_active_power_percentage_target", value), # Already returns awaitable
        available_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1,
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_phase_a_qs_ratio_target",
        name="Phase A Q/S Ratio",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-60,
        native_max_value=60,
        native_step=0.01,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_phase_a_qs_ratio_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_phase_a_qs_ratio_target", value), # Already returns awaitable
        available_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1,
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_phase_b_qs_ratio_target",
        name="Phase B Q/S Ratio",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-60,
        native_max_value=60,
        native_step=0.01,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_phase_b_qs_ratio_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_phase_b_qs_ratio_target", value), # Already returns awaitable
        available_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1,
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="plant_phase_c_qs_ratio_target",
        name="Phase C Q/S Ratio",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-60,
        native_max_value=60,
        native_step=0.01,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("plant_phase_c_qs_ratio_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_parameter("plant", None, "plant_phase_c_qs_ratio_target", value), # Already returns awaitable
        available_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1,
        entity_registry_enabled_default=False,
    ),
]

INVERTER_NUMBERS = [
    SigenergyNumberEntityDescription(
        key="inverter_active_power_fixed_adjustment",
        name="Active Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=-100,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        # Use identifier (device_name for inverters)
        value_fn=lambda data, identifier: data["inverters"].get(identifier, {}).get("inverter_active_power_fixed_adjustment", 0),
        set_value_fn=lambda hub, identifier, value: hub.async_write_parameter("inverter", identifier, "inverter_active_power_fixed_adjustment", value), # Already returns awaitable
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="inverter_reactive_power_fixed_adjustment",
        name="Reactive Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement="kVar",
        native_min_value=-100,
        native_max_value=100,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        # Use identifier (device_name for inverters)
        value_fn=lambda data, identifier: data["inverters"].get(identifier, {}).get("inverter_reactive_power_fixed_adjustment", 0),
        set_value_fn=lambda hub, identifier, value: hub.async_write_parameter("inverter", identifier, "inverter_reactive_power_fixed_adjustment", value), # Already returns awaitable
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="inverter_active_power_percentage_adjustment",
        name="Active Power Percentage Adjustment",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-100,
        native_max_value=100,
        native_step=0.01,
        entity_category=EntityCategory.CONFIG,
        # Use identifier (device_name for inverters)
        value_fn=lambda data, identifier: data["inverters"].get(identifier, {}).get("inverter_active_power_percentage_adjustment", 0),
        set_value_fn=lambda hub, identifier, value: hub.async_write_parameter("inverter", identifier, "inverter_active_power_percentage_adjustment", value), # Already returns awaitable
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="inverter_reactive_power_qs_adjustment",
        name="Reactive Power Q/S Adjustment",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-60,
        native_max_value=60,
        native_step=0.01,
        entity_category=EntityCategory.CONFIG,
        # Use identifier (device_name for inverters)
        value_fn=lambda data, identifier: data["inverters"].get(identifier, {}).get("inverter_reactive_power_qs_adjustment", 0),
        set_value_fn=lambda hub, identifier, value: hub.async_write_parameter("inverter", identifier, "inverter_reactive_power_qs_adjustment", value), # Already returns awaitable
        entity_registry_enabled_default=False,
    ),
    SigenergyNumberEntityDescription(
        key="inverter_power_factor_adjustment",
        name="Power Factor Adjustment",
        icon="mdi:sine-wave",
        native_min_value=-1,
        native_max_value=1,
        native_step=0.001,
        entity_category=EntityCategory.CONFIG,
        # Use identifier (device_name for inverters)
        value_fn=lambda data, identifier: data["inverters"].get(identifier, {}).get("inverter_power_factor_adjustment", 0) / 1000,
        set_value_fn=lambda hub, identifier, value: hub.async_write_parameter("inverter", identifier, "inverter_power_factor_adjustment", value), # Already returns awaitable
        entity_registry_enabled_default=False,
    ),
]
AC_CHARGER_NUMBERS = [
    SigenergyNumberEntityDescription(
        key="ac_charger_output_current",
        name="Charger Output Current",
        icon="mdi:current-ac",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        native_min_value=6,
        native_max_value=32,  # This will be adjusted dynamically based on rated current
        native_step=1,
        entity_category=EntityCategory.CONFIG,
        # identifier here will be ac_charger_name
        value_fn=lambda data, identifier: data["ac_chargers"].get(identifier, {}).get("ac_charger_output_current", 0),
        set_value_fn=lambda hub, identifier, value: hub.async_write_parameter("ac_charger", identifier, "ac_charger_output_current", value), # Already returns awaitable
    ),
]

DC_CHARGER_NUMBERS = []


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sigenergy number platform."""
    coordinator: SigenergyDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    plant_name = config_entry.data[CONF_NAME]
    _LOGGER.debug(f"Starting to add {SigenergyNumber}")
    # Add plant numbers
    entities : list[SigenergyNumber] = generate_sigen_entity(plant_name, None, None, coordinator, SigenergyNumber,
                                           PLANT_NUMBERS, DEVICE_TYPE_PLANT)

    # Add inverter numbers
    for device_name, device_conn in coordinator.hub.inverter_connections.items():
        entities += generate_sigen_entity(plant_name, device_name, device_conn, coordinator, SigenergyNumber,
                                           INVERTER_NUMBERS, DEVICE_TYPE_INVERTER)

    # Add AC charger numbers
    for device_name, device_conn in coordinator.hub.ac_charger_connections.items():
        entities += generate_sigen_entity(plant_name, device_name, device_conn, coordinator, SigenergyNumber,
                                           AC_CHARGER_NUMBERS, DEVICE_TYPE_AC_CHARGER)

    _LOGGER.debug(f"Class to add {SigenergyNumber}")
    async_add_entities(entities)


class SigenergyNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Sigenergy number."""

    entity_description: SigenergyNumberEntityDescription

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        description: SigenergyNumberEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[int],
        device_name: Optional[str] = "",
        pv_string_idx: Optional[int] = None,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self.entity_description = description
        self.hub = coordinator.hub
        self._attr_name = name
        self._device_type = device_type
        self._device_id = device_id # Keep slave ID if needed elsewhere
        self._device_name = device_name # Store device name
        self._pv_string_idx = pv_string_idx
        
        # Get the device number if any as a string for use in names
        device_number_str = ""
        if device_name: # Check if device_name is not None or empty
            parts = device_name.split()
            if parts and parts[-1].isdigit():
                device_number_str = f" {parts[-1]}"

        # Set unique ID (already uses device_name)
        self._attr_unique_id = generate_unique_entity_id(device_type, device_name, coordinator, description.key, pv_string_idx)
        
        # Set device info
        if device_type == DEVICE_TYPE_PLANT:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_plant")},
                name=device_name, # Should be plant_name
                manufacturer="Sigenergy",
                model="Energy Storage System",
            )
        elif device_type == DEVICE_TYPE_INVERTER:
            # Get model and serial number if available
            model = None
            serial_number = None
            sw_version = None
            if coordinator.data and "inverters" in coordinator.data:
                # Use device_name (inverter_name) to fetch data
                inverter_data = coordinator.data["inverters"].get(device_name, {})
                model = inverter_data.get("inverter_model_type")
                serial_number = inverter_data.get("inverter_serial_number")
                sw_version = inverter_data.get("inverter_machine_firmware_version")


            self._attr_device_info = DeviceInfo(
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
    def native_value(self) -> float:
        """Return the value of the number."""
        if self.coordinator.data is None:
            return 0.0 # Return float default
            
        # Pass device_name for inverters, device_id otherwise
        identifier = self._device_name if self._device_type == DEVICE_TYPE_INVERTER else self._device_id
        try:
            value = self.entity_description.value_fn(self.coordinator.data, identifier)
            # Ensure the value is a float
            return float(value) if value is not None else 0.0
        except (TypeError, ValueError, KeyError) as e:
            _LOGGER.error(f"Error getting native value for {self.entity_id} (identifier: {identifier}): {e}")
            return 0.0


    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        # Determine the correct identifier and data key based on device type
        if self._device_type == DEVICE_TYPE_PLANT:
            data_key = "plant"
            identifier = None # Plant entities don't use a specific identifier in the data dict
            device_data = self.coordinator.data.get(data_key, {}) if self.coordinator.data else {}
            base_available = self.coordinator.data is not None and data_key in self.coordinator.data
        elif self._device_type == DEVICE_TYPE_INVERTER:
            data_key = "inverters"
            identifier = self._device_name # Use name for inverters
            device_data = self.coordinator.data.get(data_key, {}).get(identifier, {}) if self.coordinator.data else {}
            base_available = (
                self.coordinator.data is not None
                and data_key in self.coordinator.data
                and identifier in self.coordinator.data[data_key]
            )
        elif self._device_type == DEVICE_TYPE_AC_CHARGER:
            data_key = "ac_chargers"
            identifier = self._device_id # Use ID for AC chargers
            device_data = self.coordinator.data.get(data_key, {}).get(identifier, {}) if self.coordinator.data else {}
            base_available = (
                self.coordinator.data is not None
                and data_key in self.coordinator.data
                and identifier in self.coordinator.data[data_key]
            )
        elif self._device_type == DEVICE_TYPE_DC_CHARGER:
            data_key = "dc_chargers"
            identifier = self._device_id # Use ID for DC chargers (assuming based on pattern)
            device_data = self.coordinator.data.get(data_key, {}).get(identifier, {}) if self.coordinator.data else {}
            base_available = (
                self.coordinator.data is not None
                and data_key in self.coordinator.data
                and identifier in self.coordinator.data[data_key]
            )
        else:
            return False # Unknown device type

        if not base_available:
            return False

        # Check specific availability function if defined
        if hasattr(self.entity_description, "available_fn"):
            try:
                # Pass the main coordinator data and the specific identifier
                return self.entity_description.available_fn(self.coordinator.data, identifier)
            except Exception as e:
                _LOGGER.error(f"Error in available_fn for {self.entity_id}: {e}")
                return False # Treat errors in availability check as unavailable

        return True # Default to available if base checks pass and no specific function

    async def async_set_native_value(self, value: float) -> None:
        """Set the value of the number."""
        try:
            # Pass device_name for inverters, device_id otherwise
            identifier = self._device_name # Use device_name for both Inverter and AC Charger now
            await self.entity_description.set_value_fn(self.hub, identifier, value)
            await self.coordinator.async_request_refresh()
        except SigenergyModbusError as error:
            _LOGGER.error("Failed to set value %s for %s: %s", value, self.name, error)
        except Exception as e:
             _LOGGER.error(f"Unexpected error setting value for {self.entity_id}: {e}")