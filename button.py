"""Button platform for Sigenergy ESS integration."""
# pylint: disable=import-error
# pyright: reportMissingImports=false
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEVICE_TYPE_PLANT,
    DOMAIN,
)
from .coordinator import SigenergyDataUpdateCoordinator
from .modbus import SigenergyModbusError

_LOGGER = logging.getLogger(__name__)


@dataclass
class SigenergyButtonEntityDescription(ButtonEntityDescription):
    """Class describing Sigenergy button entities."""

    press_fn: Callable[[Any, Optional[int]], None] = None
    available_fn: Callable[[Dict[str, Any], Optional[int]], bool] = lambda data, _: True
    entity_registry_enabled_default: bool = True


PLANT_BUTTONS = [
    # Add plant-specific buttons if needed
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sigenergy button platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    hub = hass.data[DOMAIN][config_entry.entry_id]["hub"]
    entities = []

    # Add plant buttons
    plant_name = config_entry.data[CONF_NAME]
    for description in PLANT_BUTTONS:
        entities.append(
            SigenergyButton(
                coordinator=coordinator,
                hub=hub,
                description=description,
                name=f"{plant_name} {description.name}",
                device_type=DEVICE_TYPE_PLANT,
                device_id=None,
            )
        )

    async_add_entities(entities)


class SigenergyButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Sigenergy button."""

    entity_description: SigenergyButtonEntityDescription

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        hub: Any,
        description: SigenergyButtonEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[int],
    ) -> None:
        """Initialize the button."""
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

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
            
        if self._device_type == DEVICE_TYPE_PLANT:
            if not (self.coordinator.data is not None and "plant" in self.coordinator.data):
                return False
                
            # Check if the entity has a specific availability function
            if hasattr(self.entity_description, "available_fn"):
                return self.entity_description.available_fn(self.coordinator.data, self._device_id)
                
            return True
            
        return False

    async def async_press(self) -> None:
        """Press the button."""
        try:
            await self.entity_description.press_fn(self.hub, self._device_id)
            await self.coordinator.async_request_refresh()
        except SigenergyModbusError as error:
            _LOGGER.error("Failed to press button %s: %s", self.name, error)