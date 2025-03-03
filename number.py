"""Number platform for Sigenergy ESS integration."""
# pylint: disable=import-error
# pyright: reportMissingImports=false
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

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
    DEVICE_TYPE_AC_CHARGER,
    DEVICE_TYPE_INVERTER,
    DEVICE_TYPE_PLANT,
    DOMAIN,
    DEFAULT_PLANT_NAME,
)
from .coordinator import SigenergyDataUpdateCoordinator
from .modbus import SigenergyModbusError

_LOGGER = logging.getLogger(__name__)


@dataclass
class SigenergyNumberEntityDescription(NumberEntityDescription):
    """Class describing Sigenergy number entities."""

    value_fn: Callable[[Dict[str, Any], Optional[int]], float] = None
    set_value_fn: Callable[[Any, Optional[int], float], None] = None
    available_fn: Callable[[Dict[str, Any], Optional[int]], bool] = lambda data, _: True
    entity_registry_enabled_default: bool = True


PLANT_NUMBERS = [
    SigenergyNumberEntityDescription(
        key="active_power_fixed_adjustment_target",
        name="Active Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=-100,
        native_max_value=100,
        native_step=0.1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("active_power_fixed_adjustment_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_plant_parameter("active_power_fixed_adjustment_target", value),
    ),
    SigenergyNumberEntityDescription(
        key="reactive_power_fixed_adjustment_target",
        name="Reactive Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement="kVar",
        native_min_value=-100,
        native_max_value=100,
        native_step=0.1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("reactive_power_fixed_adjustment_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_plant_parameter("reactive_power_fixed_adjustment_target", value),
    ),
    SigenergyNumberEntityDescription(
        key="active_power_percentage_adjustment_target",
        name="Active Power Percentage Adjustment",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-100,
        native_max_value=100,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("active_power_percentage_adjustment_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_plant_parameter("active_power_percentage_adjustment_target", value),
    ),
    SigenergyNumberEntityDescription(
        key="q_s_adjustment_target",
        name="Q/S Adjustment",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-60,
        native_max_value=60,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("q_s_adjustment_target", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_plant_parameter("q_s_adjustment_target", value),
    ),
    SigenergyNumberEntityDescription(
        key="power_factor_adjustment_target",
        name="Power Factor Adjustment",
        icon="mdi:sine-wave",
        native_min_value=-1,
        native_max_value=1,
        native_step=0.01,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("power_factor_adjustment_target", 0) / 1000,
        set_value_fn=lambda hub, _, value: hub.async_write_plant_parameter("power_factor_adjustment_target", value),
    ),
    SigenergyNumberEntityDescription(
        key="ess_max_charging_limit",
        name="ESS Max Charging Limit",
        icon="mdi:battery-charging",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0,
        native_max_value=100,  # This will be adjusted dynamically based on rated power
        native_step=0.1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("ess_max_charging_limit", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_plant_parameter("ess_max_charging_limit", value),
    ),
    SigenergyNumberEntityDescription(
        key="ess_max_discharging_limit",
        name="ESS Max Discharging Limit",
        icon="mdi:battery-charging-outline",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0,
        native_max_value=100,  # This will be adjusted dynamically based on rated power
        native_step=0.1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("ess_max_discharging_limit", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_plant_parameter("ess_max_discharging_limit", value),
    ),
    SigenergyNumberEntityDescription(
        key="pv_max_power_limit",
        name="PV Max Power Limit",
        icon="mdi:solar-power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0,
        native_max_value=100,  # This will be adjusted dynamically based on rated power
        native_step=0.1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("pv_max_power_limit", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_plant_parameter("pv_max_power_limit", value),
    ),
    SigenergyNumberEntityDescription(
        key="grid_point_maximum_export_limitation",
        name="Grid Export Limitation",
        icon="mdi:transmission-tower-export",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0,
        native_max_value=100,  # This will be adjusted dynamically based on rated power
        native_step=0.1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("grid_point_maximum_export_limitation", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_plant_parameter("grid_point_maximum_export_limitation", value),
    ),
    SigenergyNumberEntityDescription(
        key="grid_point_maximum_import_limitation",
        name="Grid Import Limitation",
        icon="mdi:transmission-tower-import",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=0,
        native_max_value=100,  # This will be adjusted dynamically based on rated power
        native_step=0.1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, _: data["plant"].get("grid_point_maximum_import_limitation", 0),
        set_value_fn=lambda hub, _, value: hub.async_write_plant_parameter("grid_point_maximum_import_limitation", value),
    ),
]

INVERTER_NUMBERS = [
    SigenergyNumberEntityDescription(
        key="active_power_fixed_value_adjustment",
        name="Active Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=-100,
        native_max_value=100,
        native_step=0.1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("active_power_fixed_value_adjustment", 0),
        set_value_fn=lambda hub, inverter_id, value: hub.async_write_inverter_parameter(inverter_id, "active_power_fixed_value_adjustment", value),
    ),
    SigenergyNumberEntityDescription(
        key="reactive_power_fixed_value_adjustment",
        name="Reactive Power Fixed Adjustment",
        icon="mdi:flash",
        native_unit_of_measurement="kVar",
        native_min_value=-100,
        native_max_value=100,
        native_step=0.1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("reactive_power_fixed_value_adjustment", 0),
        set_value_fn=lambda hub, inverter_id, value: hub.async_write_inverter_parameter(inverter_id, "reactive_power_fixed_value_adjustment", value),
    ),
    SigenergyNumberEntityDescription(
        key="active_power_percentage_adjustment",
        name="Active Power Percentage Adjustment",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-100,
        native_max_value=100,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("active_power_percentage_adjustment", 0),
        set_value_fn=lambda hub, inverter_id, value: hub.async_write_inverter_parameter(inverter_id, "active_power_percentage_adjustment", value),
    ),
    SigenergyNumberEntityDescription(
        key="reactive_power_q_s_adjustment",
        name="Reactive Power Q/S Adjustment",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-60,
        native_max_value=60,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("reactive_power_q_s_adjustment", 0),
        set_value_fn=lambda hub, inverter_id, value: hub.async_write_inverter_parameter(inverter_id, "reactive_power_q_s_adjustment", value),
    ),
    SigenergyNumberEntityDescription(
        key="power_factor_adjustment",
        name="Power Factor Adjustment",
        icon="mdi:sine-wave",
        native_min_value=-1,
        native_max_value=1,
        native_step=0.01,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("power_factor_adjustment", 0) / 1000,
        set_value_fn=lambda hub, inverter_id, value: hub.async_write_inverter_parameter(inverter_id, "power_factor_adjustment", value),
    ),
]

AC_CHARGER_NUMBERS = [
    SigenergyNumberEntityDescription(
        key="charger_output_current",
        name="Charger Output Current",
        icon="mdi:current-ac",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        native_min_value=6,
        native_max_value=32,  # This will be adjusted dynamically based on rated current
        native_step=1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda data, ac_charger_id: data["ac_chargers"].get(ac_charger_id, {}).get("charger_output_current", 0),
        set_value_fn=lambda hub, ac_charger_id, value: hub.async_write_ac_charger_parameter(ac_charger_id, "charger_output_current", value),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sigenergy number platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    hub = hass.data[DOMAIN][config_entry.entry_id]["hub"]
    entities = []

    # Add plant numbers
    plant_name = config_entry.data[CONF_NAME]
    for description in PLANT_NUMBERS:
        entities.append(
            SigenergyNumber(
                coordinator=coordinator,
                hub=hub,
                description=description,
                name=f"{plant_name} {description.name}",
                device_type=DEVICE_TYPE_PLANT,
                device_id=None,
                plant_name=plant_name
            )
        )

    # Add inverter numbers
    for inverter_id in coordinator.hub.inverter_slave_ids:
        for description in INVERTER_NUMBERS:
            entities.append(
                SigenergyNumber(
                    coordinator=coordinator,
                    hub=hub,
                    description=description,
                    name=f"{plant_name} Inverter {inverter_id} {description.name}",
                    device_type=DEVICE_TYPE_INVERTER,
                    device_id=inverter_id,
                )
            )

    # Add AC charger numbers
    for ac_charger_id in coordinator.hub.ac_charger_slave_ids:
        for description in AC_CHARGER_NUMBERS:
            entities.append(
                SigenergyNumber(
                    coordinator=coordinator,
                    hub=hub,
                    description=description,
                    name=f"{plant_name} AC Charger {ac_charger_id} {description.name}",
                    device_type=DEVICE_TYPE_AC_CHARGER,
                    device_id=ac_charger_id,
                )
            )

    async_add_entities(entities)


class SigenergyNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Sigenergy number."""

    entity_description: SigenergyNumberEntityDescription

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        hub: Any,
        description: SigenergyNumberEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[int],
        plant_name: Optional[str] =DEFAULT_PLANT_NAME,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self.entity_description = description
        self.hub = hub
        self._attr_name = name
        self._device_type = device_type
        self._device_id = device_id
        
        # Set unique ID
        if device_type == DEVICE_TYPE_PLANT:
            self._attr_unique_id = f"{coordinator.hub.host}_{device_type}_{description.key}"
        else:
            # self._attr_unique_id = f"{coordinator.hub.host}_{device_type}_{device_id}_{description.key}"
            # Used for testing in development to allow multiple sensors with the same unique ID
            # Remove this line before submitting a PR
            self._attr_unique_id = f"{coordinator.hub.plant_id}_{device_type}_{device_id}_{description.key}_{random.randint(0, 10000)}"
        
        # Set device info
        if device_type == DEVICE_TYPE_PLANT:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{coordinator.hub.host}_plant")},
                # name=f"{hub.name} qqq", #.split(" ", 1)[0],  # Use plant name as device name
                name=plant_name,
                manufacturer="Sigenergy",
                model="Energy Storage System",
                via_device=(DOMAIN, f"{coordinator.hub.host}_plant"),
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
                name=f"Sigen Inverter{'' if device_id == 1 else f' {device_id}'}",
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
    def native_value(self) -> float:
        """Return the value of the number."""
        if self.coordinator.data is None:
            return 0
            
        return self.entity_description.value_fn(self.coordinator.data, self._device_id)

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

    async def async_set_native_value(self, value: float) -> None:
        """Set the value of the number."""
        try:
            await self.entity_description.set_value_fn(self.hub, self._device_id, value)
            await self.coordinator.async_request_refresh()
        except SigenergyModbusError as error:
            _LOGGER.error("Failed to set value %s for %s: %s", value, self.name, error)