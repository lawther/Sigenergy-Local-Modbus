"""Switch platform for Sigenergy Energy Storage System integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEVICE_TYPE_AC_CHARGER,
    DEVICE_TYPE_INVERTER,
    DEVICE_TYPE_PLANT,
    DOMAIN,
)
from .coordinator import SigenergyDataUpdateCoordinator
from .modbus import SigenergyModbusError

_LOGGER = logging.getLogger(__name__)


@dataclass
class SigenergySwitchEntityDescription(SwitchEntityDescription):
    """Class describing Sigenergy switch entities."""

    is_on_fn: Callable[[Dict[str, Any], Optional[int]], bool] = None
    turn_on_fn: Callable[[Any, Optional[int]], None] = None
    turn_off_fn: Callable[[Any, Optional[int]], None] = None
    available_fn: Callable[[Dict[str, Any], Optional[int]], bool] = lambda data, _: True
    entity_registry_enabled_default: bool = True


PLANT_SWITCHES = [
    SigenergySwitchEntityDescription(
        key="plant_start_stop",
        name="Plant Power",
        icon="mdi:power",
        is_on_fn=lambda data, _: data["plant"].get("plant_running_state") == 1,
        turn_on_fn=lambda hub, _: hub.async_write_plant_parameter("start_stop", 1),
        turn_off_fn=lambda hub, _: hub.async_write_plant_parameter("start_stop", 0),
    ),
    SigenergySwitchEntityDescription(
        key="remote_ems_enable",
        name="Remote EMS",
        icon="mdi:remote",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda data, _: data["plant"].get("remote_ems_enable") == 1,
        turn_on_fn=lambda hub, _: hub.async_write_plant_parameter("remote_ems_enable", 1),
        turn_off_fn=lambda hub, _: hub.async_write_plant_parameter("remote_ems_enable", 0),
    ),
    SigenergySwitchEntityDescription(
        key="independent_phase_power_control_enable",
        name="Independent Phase Power Control",
        icon="mdi:tune",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda data, _: data["plant"].get("independent_phase_power_control_enable") == 1,
        turn_on_fn=lambda hub, _: hub.async_write_plant_parameter("independent_phase_power_control_enable", 1),
        turn_off_fn=lambda hub, _: hub.async_write_plant_parameter("independent_phase_power_control_enable", 0),
    ),
]

INVERTER_SWITCHES = [
    SigenergySwitchEntityDescription(
        key="inverter_start_stop",
        name="Inverter Power",
        icon="mdi:power",
        is_on_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("running_state") == 1,
        turn_on_fn=lambda hub, inverter_id: hub.async_write_inverter_parameter(inverter_id, "start_stop", 1),
        turn_off_fn=lambda hub, inverter_id: hub.async_write_inverter_parameter(inverter_id, "start_stop", 0),
    ),
    SigenergySwitchEntityDescription(
        key="dc_charger_start_stop",
        name="DC Charger",
        icon="mdi:ev-station",
        is_on_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("dc_charger_start_stop") == 0,
        turn_on_fn=lambda hub, inverter_id: hub.async_write_inverter_parameter(inverter_id, "dc_charger_start_stop", 0),
        turn_off_fn=lambda hub, inverter_id: hub.async_write_inverter_parameter(inverter_id, "dc_charger_start_stop", 1),
    ),
    SigenergySwitchEntityDescription(
        key="remote_ems_dispatch_enable",
        name="Remote EMS Dispatch",
        icon="mdi:remote",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda data, inverter_id: data["inverters"].get(inverter_id, {}).get("remote_ems_dispatch_enable") == 1,
        turn_on_fn=lambda hub, inverter_id: hub.async_write_inverter_parameter(inverter_id, "remote_ems_dispatch_enable", 1),
        turn_off_fn=lambda hub, inverter_id: hub.async_write_inverter_parameter(inverter_id, "remote_ems_dispatch_enable", 0),
    ),
]

AC_CHARGER_SWITCHES = [
    SigenergySwitchEntityDescription(
        key="ac_charger_start_stop",
        name="AC Charger Power",
        icon="mdi:ev-station",
        is_on_fn=lambda data, ac_charger_id: data["ac_chargers"].get(ac_charger_id, {}).get("system_state") > 0,
        turn_on_fn=lambda hub, ac_charger_id: hub.async_write_ac_charger_parameter(ac_charger_id, "start_stop", 0),
        turn_off_fn=lambda hub, ac_charger_id: hub.async_write_ac_charger_parameter(ac_charger_id, "start_stop", 1),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sigenergy switch platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    hub = hass.data[DOMAIN][config_entry.entry_id]["hub"]
    entities = []

    # Add plant switches
    plant_name = config_entry.data[CONF_NAME]
    for description in PLANT_SWITCHES:
        entities.append(
            SigenergySwitch(
                coordinator=coordinator,
                hub=hub,
                description=description,
                name=f"{plant_name} {description.name}",
                device_type=DEVICE_TYPE_PLANT,
                device_id=None,
            )
        )

    # Add inverter switches
    for inverter_id in coordinator.hub.inverter_slave_ids:
        for description in INVERTER_SWITCHES:
            entities.append(
                SigenergySwitch(
                    coordinator=coordinator,
                    hub=hub,
                    description=description,
                    name=f"{plant_name} Inverter {inverter_id} {description.name}",
                    device_type=DEVICE_TYPE_INVERTER,
                    device_id=inverter_id,
                )
            )

    # Add AC charger switches
    for ac_charger_id in coordinator.hub.ac_charger_slave_ids:
        for description in AC_CHARGER_SWITCHES:
            entities.append(
                SigenergySwitch(
                    coordinator=coordinator,
                    hub=hub,
                    description=description,
                    name=f"{plant_name} AC Charger {ac_charger_id} {description.name}",
                    device_type=DEVICE_TYPE_AC_CHARGER,
                    device_id=ac_charger_id,
                )
            )

    async_add_entities(entities)


class SigenergySwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Sigenergy switch."""

    entity_description: SigenergySwitchEntityDescription

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        hub: Any,
        description: SigenergySwitchEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[int],
    ) -> None:
        """Initialize the switch."""
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
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if self.coordinator.data is None:
            return False
            
        return self.entity_description.is_on_fn(self.coordinator.data, self._device_id)

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            await self.entity_description.turn_on_fn(self.hub, self._device_id)
            await self.coordinator.async_request_refresh()
        except SigenergyModbusError as error:
            _LOGGER.error("Failed to turn on %s: %s", self.name, error)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            await self.entity_description.turn_off_fn(self.hub, self._device_id)
            await self.coordinator.async_request_refresh()
        except SigenergyModbusError as error:
            _LOGGER.error("Failed to turn off %s: %s", self.name, error)