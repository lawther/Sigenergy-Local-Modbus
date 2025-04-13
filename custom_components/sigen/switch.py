"""Switch platform for Sigenergy ESS integration."""
from __future__ import annotations
import logging
import asyncio
from dataclasses import dataclass
from typing import Any, Coroutine, Callable, Dict, Optional

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry  #pylint: disable=no-name-in-module, syntax-error
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common import *
from .const import (
    DEVICE_TYPE_AC_CHARGER,
    DEVICE_TYPE_DC_CHARGER,
    DEVICE_TYPE_INVERTER,
    DEVICE_TYPE_PLANT,
    DOMAIN,
    CONF_INVERTER_HAS_DCCHARGER,
)
from .coordinator import SigenergyDataUpdateCoordinator
from .modbus import SigenergyModbusError
from .sigen_entity import SigenergyEntity # Import the new base class

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
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
        turn_on_fn=lambda hub, _: hub.async_write_parameter("plant", None, "plant_start_stop", 1), # Already returns awaitable
        turn_off_fn=lambda hub, _: hub.async_write_parameter("plant", None, "plant_start_stop", 0), # Already returns awaitable
    ),
    SigenergySwitchEntityDescription(
        key="plant_remote_ems_enable",
        name="Remote EMS (Controled by Home Assistant)",
        icon="mdi:home-assistant",
        is_on_fn=lambda data, _: data["plant"].get("plant_remote_ems_enable") == 1,
        turn_on_fn=lambda hub, _: hub.async_write_parameter("plant", None, "plant_remote_ems_enable", 1), # Already returns awaitable
        turn_off_fn=lambda hub, _: hub.async_write_parameter("plant", None, "plant_remote_ems_enable", 0), # Already returns awaitable
    ),
    SigenergySwitchEntityDescription(
        key="plant_independent_phase_power_control_enable",
        name="Independent Phase Power Control",
        icon="mdi:tune",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda data, _: data["plant"].get("plant_independent_phase_power_control_enable") == 1, # Sync
        turn_on_fn=lambda hub, _: hub.async_write_parameter("plant", None, "plant_independent_phase_power_control_enable", 1), # Already returns awaitable
        turn_off_fn=lambda hub, _: hub.async_write_parameter("plant", None, "plant_independent_phase_power_control_enable", 0), # Already returns awaitable
    ),
]

INVERTER_SWITCHES = [
    SigenergySwitchEntityDescription(
        key="inverter_start_stop",
        name="Inverter Power",
        icon="mdi:power",
        # Use device_name (inverter_name) instead of device_id (now passed as the second arg 'identifier')
        is_on_fn=lambda data, identifier: data["inverters"].get(identifier, {}).get("inverter_running_state") == 1,
        turn_on_fn=lambda hub, identifier: hub.async_write_parameter("inverter", identifier, "inverter_start_stop", 1), # Already returns awaitable
        turn_off_fn=lambda hub, identifier: hub.async_write_parameter("inverter", identifier, "inverter_start_stop", 0), # Already returns awaitable
    ),
    SigenergySwitchEntityDescription(
        key="inverter_remote_ems_dispatch_enable",
        name="Remote EMS Dispatch",
        icon="mdi:remote",
        entity_category=EntityCategory.CONFIG,
        # Use device_name (inverter_name) instead of device_id (now passed as the second arg 'identifier')
        is_on_fn=lambda data, identifier: data["inverters"].get(identifier, {}).get("inverter_remote_ems_dispatch_enable") == 1,
        turn_on_fn=lambda hub, identifier: hub.async_write_parameter("inverter", identifier, "inverter_remote_ems_dispatch_enable", 1), # Already returns awaitable
        turn_off_fn=lambda hub, identifier: hub.async_write_parameter("inverter", identifier, "inverter_remote_ems_dispatch_enable", 0), # Already returns awaitable
    ),
]
AC_CHARGER_SWITCHES = [
    SigenergySwitchEntityDescription(
        key="ac_charger_start_stop",
        name="AC Charger Power",
        icon="mdi:ev-station",
        # identifier here will be ac_charger_name
        is_on_fn=lambda data, identifier: data["ac_chargers"].get(identifier, {}).get("ac_charger_system_state") > 0,
        turn_on_fn=lambda hub, identifier: hub.async_write_parameter("ac_charger", identifier, "ac_charger_start_stop", 0), # Already returns awaitable
        turn_off_fn=lambda hub, identifier: hub.async_write_parameter("ac_charger", identifier, "ac_charger_start_stop", 1), # Already returns awaitable
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
        turn_on_fn=lambda hub, identifier: hub.async_write_parameter("inverter", identifier, "dc_charger_start_stop", 0), # TODO: Review this logic - Assuming DC charger controlled via inverter. Already returns awaitable
        turn_off_fn=lambda hub, identifier: hub.async_write_parameter("inverter", identifier, "dc_charger_start_stop", 1), # TODO: Review this logic - Assuming DC charger controlled via inverter. Already returns awaitable
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
        entities += generate_sigen_entity(plant_name, device_name, device_conn, coordinator, 
                                          SigenergySwitch, INVERTER_SWITCHES, DEVICE_TYPE_INVERTER)

        # Add DC charger sensors
        if device_conn.get(CONF_INVERTER_HAS_DCCHARGER, False):
            dc_name = f"{device_name} DC Charger"
            parent_inverter_id = f"{coordinator.hub.config_entry.entry_id}_{generate_device_id(device_name)}"
            dc_id = f"{parent_inverter_id}_dc_charger"
            _LOGGER.debug("[switch] Adding DC Charger with dc_name: %s, parent_inverter_id: %s, dc_id: %s",
                          dc_name, parent_inverter_id, dc_id)

            # Create device info
            dc_device_info = DeviceInfo(
                identifiers={(DOMAIN, dc_id)},
                name=dc_name,
                manufacturer="Sigenergy",
                model="DC Charger",
                via_device=(DOMAIN, parent_inverter_id),
            )

            # Static Sensors:
            async_add_entities(
                generate_sigen_entity(
                    plant_name,
                    device_name,
                    device_conn,
                    coordinator,
                    SigenergySwitch,
                    DC_CHARGER_SWITCHES,
                    DEVICE_TYPE_DC_CHARGER,
                    device_info=dc_device_info
                )
            )

    # Add AC charger Switches
    for device_name, device_conn in coordinator.hub.ac_charger_connections.items():
        entities += generate_sigen_entity(plant_name, device_name, device_conn, coordinator,
                                          SigenergySwitch, AC_CHARGER_SWITCHES,
                                          DEVICE_TYPE_AC_CHARGER)

    _LOGGER.debug(f"Class to add {SigenergySwitch}")
    async_add_entities(entities)
    return

class SigenergySwitch(SigenergyEntity, SwitchEntity):
    """Representation of a Sigenergy switch."""

    entity_description: SigenergySwitchEntityDescription

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        description: SigenergySwitchEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[str] = None, # Changed to Optional[str]
        device_name: Optional[str] = "",
        device_info: Optional[DeviceInfo] = None,
        pv_string_idx: Optional[int] = None,
    ) -> None:
        """Initialize the switch."""
        # Call the base class __init__
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
        # No switch-specific init needed for now

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if self.coordinator.data is None:
            return False
            
        # Pass device_name for inverters, device_id otherwise
        # Use device_name as the primary identifier passed to the lambda,
        # consistent with base class setup and other platforms.
        # The lambda itself needs to handle how to access data (e.g., using device_name for inverters/AC, or potentially device_id for AC if needed)
        identifier = self._device_name
        return self.entity_description.is_on_fn(self.coordinator.data, identifier)

    # The 'available' property is now inherited from SigenergyEntity

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            # Pass device_name for inverters, device_id otherwise
            identifier = self._device_name # Use device_name for both Inverter and AC Charger now
            await self.entity_description.turn_on_fn(self.hub, identifier)
            await self.coordinator.async_request_refresh()
        except SigenergyModbusError as error:
            _LOGGER.error("Failed to turn on %s: %s", self.name, error)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            # Pass device_name for inverters, device_id otherwise
            identifier = self._device_name # Use device_name for both Inverter and AC Charger now
            await self.entity_description.turn_off_fn(self.hub, identifier)
            await self.coordinator.async_request_refresh()
        except SigenergyModbusError as error:
            _LOGGER.error("Failed to turn off %s: %s", self.name, error)