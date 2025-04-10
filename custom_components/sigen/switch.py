"""Switch platform for Sigenergy ESS integration."""
from __future__ import annotations
import logging
import asyncio
from typing import Coroutine
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .common import *
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

_LOGGER = logging.getLogger(__name__)


@dataclass
class SigenergySwitchEntityDescription(SwitchEntityDescription):
    """Class describing Sigenergy switch entities."""

    # Provide default lambdas instead of None to satisfy type checker
    # The second argument 'identifier' will be device_name for inverters, device_id otherwise
    is_on_fn: Callable[[Dict[str, Any], Optional[Any]], bool] = lambda data, identifier: False # Remains synchronous
    # Make turn_on/off functions async and update type hint
    turn_on_fn: Callable[[Any, Optional[Any]], Coroutine[Any, Any, None]] = lambda hub, identifier: asyncio.sleep(0) # Placeholder async lambda
    turn_off_fn: Callable[[Any, Optional[Any]], Coroutine[Any, Any, None]] = lambda hub, identifier: asyncio.sleep(0) # Placeholder async lambda
    available_fn: Callable[[Dict[str, Any], Optional[Any]], bool] = lambda data, _: True
    entity_registry_enabled_default: bool = True


PLANT_SWITCHES = [
    SigenergySwitchEntityDescription(
        key="plant_start_stop",
        name="Plant Power",
        icon="mdi:power",
        is_on_fn=lambda data, _: data["plant"].get("plant_running_state") == 1, # Sync
        turn_on_fn=lambda hub, _: hub.async_write_plant_parameter("plant_start_stop", 1), # Already returns awaitable
        turn_off_fn=lambda hub, _: hub.async_write_plant_parameter("plant_start_stop", 0), # Already returns awaitable
    ),
    SigenergySwitchEntityDescription(
        key="plant_remote_ems_enable",
        name="Remote EMS (Controled by Home Assistant)",
        icon="mdi:home-assistant",
        is_on_fn=lambda data, _: data["plant"].get("plant_remote_ems_enable") == 1,
        turn_on_fn=lambda hub, _: hub.async_write_plant_parameter("plant_remote_ems_enable", 1), # Already returns awaitable
        turn_off_fn=lambda hub, _: hub.async_write_plant_parameter("plant_remote_ems_enable", 0), # Already returns awaitable
    ),
    SigenergySwitchEntityDescription(
        key="plant_independent_phase_power_control_enable",
        name="Independent Phase Power Control",
        icon="mdi:tune",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1, # Sync
        turn_on_fn=lambda hub, _: hub.async_write_plant_parameter("plant_independent_phase_power_control_enable", 1), # Already returns awaitable
        turn_off_fn=lambda hub, _: hub.async_write_plant_parameter("plant_independent_phase_power_control_enable", 0), # Already returns awaitable
    ),
]

INVERTER_SWITCHES = [
    SigenergySwitchEntityDescription(
        key="inverter_start_stop",
        name="Inverter Power",
        icon="mdi:power",
        # Use device_name (inverter_name) instead of device_id (now passed as the second arg 'identifier')
        is_on_fn=lambda data, identifier: data["inverters"].get(identifier, {}).get("inverter_running_state") == 1,
        turn_on_fn=lambda hub, identifier: hub.async_write_inverter_parameter(identifier, "inverter_start_stop", 1), # Already returns awaitable
        turn_off_fn=lambda hub, identifier: hub.async_write_inverter_parameter(identifier, "inverter_start_stop", 0), # Already returns awaitable
    ),
    SigenergySwitchEntityDescription(
        key="inverter_remote_ems_dispatch_enable",
        name="Remote EMS Dispatch",
        icon="mdi:remote",
        entity_category=EntityCategory.CONFIG,
        # Use device_name (inverter_name) instead of device_id (now passed as the second arg 'identifier')
        is_on_fn=lambda data, identifier: data["inverters"].get(identifier, {}).get("inverter_remote_ems_dispatch_enable") == 1,
        turn_on_fn=lambda hub, identifier: hub.async_write_inverter_parameter(identifier, "inverter_remote_ems_dispatch_enable", 1), # Already returns awaitable
        turn_off_fn=lambda hub, identifier: hub.async_write_inverter_parameter(identifier, "inverter_remote_ems_dispatch_enable", 0), # Already returns awaitable
    ),
]
AC_CHARGER_SWITCHES = [
    SigenergySwitchEntityDescription(
        key="ac_charger_start_stop",
        name="AC Charger Power",
        icon="mdi:ev-station",
        # identifier here is ac_charger_id
        is_on_fn=lambda data, identifier: data["ac_chargers"].get(identifier, {}).get("ac_charger_system_state") > 0,
        turn_on_fn=lambda hub, identifier: hub.async_write_ac_charger_parameter(identifier, "ac_charger_start_stop", 0), # Already returns awaitable
        turn_off_fn=lambda hub, identifier: hub.async_write_ac_charger_parameter(identifier, "ac_charger_start_stop", 1), # Already returns awaitable
    ),
]

DC_CHARGER_SWITCHES = [
    SigenergySwitchEntityDescription(
        key="dc_charger_start_stop",
        name="DC Charger",
        icon="mdi:ev-station",
        # consider changing is_on_fn to check for dc_charger_output_power > 0 if the below doesn't work
        # identifier here is dc_charger_id (but it's accessing inverter data?) - This seems wrong, needs review based on coordinator data structure
        is_on_fn=lambda data, identifier: data["inverters"].get(identifier, {}).get("dc_charger_start_stop") == 0, # TODO: Review this logic - should likely use dc_charger data
        turn_on_fn=lambda hub, identifier: hub.async_write_inverter_parameter(identifier, "dc_charger_start_stop", 0), # TODO: Review this logic - Already returns awaitable
        turn_off_fn=lambda hub, identifier: hub.async_write_inverter_parameter(identifier, "dc_charger_start_stop", 1), # TODO: Review this logic - Already returns awaitable
    ),
]



async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sigenergy switch platform."""
    coordinator: SigenergyDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    plant_name = config_entry.data[CONF_NAME]
    _LOGGER.debug(f"Starting to add {SigenergySwitch}")
    # Add plant Switches
    entities : list[SigenergySwitch] = generate_sigen_entity(plant_name, None, None, coordinator, SigenergySwitch,
                                           PLANT_SWITCHES, DEVICE_TYPE_PLANT)

    # Add inverter Switches
    for device_name, device_conn in coordinator.hub.inverter_connections.items():
        entities += generate_sigen_entity(plant_name, device_name, device_conn, coordinator, SigenergySwitch,
                                           INVERTER_SWITCHES, DEVICE_TYPE_INVERTER)

    # Add AC charger Switches
    for device_name, device_conn in coordinator.hub.ac_charger_connections.items():
        entities += generate_sigen_entity(plant_name, device_name, device_conn, coordinator, SigenergySwitch,
                                           AC_CHARGER_SWITCHES, DEVICE_TYPE_AC_CHARGER)

    # Add DC charger Switches
    for device_name, device_conn in coordinator.hub.dc_charger_connections.items():
        entities += generate_sigen_entity(plant_name, device_name, device_conn, coordinator, SigenergySwitch,
                                           DC_CHARGER_SWITCHES, DEVICE_TYPE_DC_CHARGER)
        
    _LOGGER.debug(f"Class to add {SigenergySwitch}")
    async_add_entities(entities)
    return

class SigenergySwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Sigenergy switch."""

    entity_description: SigenergySwitchEntityDescription

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        description: SigenergySwitchEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[int],
        device_name: Optional[str] = "",
        pv_string_idx: Optional[int] = None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self.hub = coordinator.hub
        self._attr_name = name
        self._device_type = device_type
        self._device_id = device_id # Keep slave ID if needed elsewhere, but prefer name for inverter lookups
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
                name=device_name, # Should be plant_name here
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
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if self.coordinator.data is None:
            return False
            
        # Pass device_name for inverters, device_id otherwise
        identifier = self._device_name if self._device_type == DEVICE_TYPE_INVERTER else self._device_id
        return self.entity_description.is_on_fn(self.coordinator.data, identifier)

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
                # Check availability using device_name (inverter_name)
                and self._device_name in self.coordinator.data["inverters"]
            )
        elif self._device_type == DEVICE_TYPE_AC_CHARGER:
            return (
                self.coordinator.data is not None
                and "ac_chargers" in self.coordinator.data
                and self._device_id in self.coordinator.data["ac_chargers"] # AC Chargers still use ID
            )

        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            # Pass device_name for inverters, device_id otherwise
            identifier = self._device_name if self._device_type == DEVICE_TYPE_INVERTER else self._device_id
            await self.entity_description.turn_on_fn(self.hub, identifier)
            await self.coordinator.async_request_refresh()
        except SigenergyModbusError as error:
            _LOGGER.error("Failed to turn on %s: %s", self.name, error)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            # Pass device_name for inverters, device_id otherwise
            identifier = self._device_name if self._device_type == DEVICE_TYPE_INVERTER else self._device_id
            await self.entity_description.turn_off_fn(self.hub, identifier)
            await self.coordinator.async_request_refresh()
        except SigenergyModbusError as error:
            _LOGGER.error("Failed to turn off %s: %s", self.name, error)