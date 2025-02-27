"""Select platform for Sigenergy Energy Storage System integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEVICE_TYPE_INVERTER,
    DEVICE_TYPE_PLANT,
    DOMAIN,
    EMSWorkMode,
    RemoteEMSControlMode,
)
from .coordinator import SigenergyDataUpdateCoordinator
from .modbus import SigenergyModbusError

_LOGGER = logging.getLogger(__name__)


@dataclass
class SigenergySelectEntityDescription(SelectEntityDescription):
    """Class describing Sigenergy select entities."""

    current_option_fn: Callable[[Dict[str, Any], Optional[int]], str] = None
    select_option_fn: Callable[[Any, Optional[int], str], None] = None
    available_fn: Callable[[Dict[str, Any], Optional[int]], bool] = lambda data, _: True
    entity_registry_enabled_default: bool = True


PLANT_SELECTS = [
    SigenergySelectEntityDescription(
        key="ems_work_mode",
        name="EMS Work Mode",
        icon="mdi:home-battery",
        options=[
            "Maximum Self Consumption",
            "AI Mode",
            "Time of Use",
            "Remote EMS",
        ],
        entity_category=EntityCategory.CONFIG,
        current_option_fn=lambda data, _: {
            EMSWorkMode.MAX_SELF_CONSUMPTION: "Maximum Self Consumption",
            EMSWorkMode.AI_MODE: "AI Mode",
            EMSWorkMode.TOU: "Time of Use",
            EMSWorkMode.REMOTE_EMS: "Remote EMS",
        }.get(data["plant"].get("ems_work_mode"), "Unknown"),
        select_option_fn=lambda hub, _, option: hub.async_write_plant_parameter(
            "ems_work_mode",
            {
                "Maximum Self Consumption": EMSWorkMode.MAX_SELF_CONSUMPTION,
                "AI Mode": EMSWorkMode.AI_MODE,
                "Time of Use": EMSWorkMode.TOU,
                "Remote EMS": EMSWorkMode.REMOTE_EMS,
            }.get(option, EMSWorkMode.MAX_SELF_CONSUMPTION),
        ),
    ),
    SigenergySelectEntityDescription(
        key="remote_ems_control_mode",
        name="Remote EMS Control Mode",
        icon="mdi:remote",
        options=[
            "PCS Remote Control",
            "Standby",
            "Maximum Self Consumption",
            "Command Charging (Grid First)",
            "Command Charging (PV First)",
            "Command Discharging (PV First)",
            "Command Discharging (ESS First)",
        ],
        entity_category=EntityCategory.CONFIG,
        current_option_fn=lambda data, _: {
            RemoteEMSControlMode.PCS_REMOTE_CONTROL: "PCS Remote Control",
            RemoteEMSControlMode.STANDBY: "Standby",
            RemoteEMSControlMode.MAXIMUM_SELF_CONSUMPTION: "Maximum Self Consumption",
            RemoteEMSControlMode.COMMAND_CHARGING_GRID_FIRST: "Command Charging (Grid First)",
            RemoteEMSControlMode.COMMAND_CHARGING_PV_FIRST: "Command Charging (PV First)",
            RemoteEMSControlMode.COMMAND_DISCHARGING_PV_FIRST: "Command Discharging (PV First)",
            RemoteEMSControlMode.COMMAND_DISCHARGING_ESS_FIRST: "Command Discharging (ESS First)",
        }.get(data["plant"].get("remote_ems_control_mode"), "Unknown"),
        select_option_fn=lambda hub, _, option: hub.async_write_plant_parameter(
            "remote_ems_control_mode",
            {
                "PCS Remote Control": RemoteEMSControlMode.PCS_REMOTE_CONTROL,
                "Standby": RemoteEMSControlMode.STANDBY,
                "Maximum Self Consumption": RemoteEMSControlMode.MAXIMUM_SELF_CONSUMPTION,
                "Command Charging (Grid First)": RemoteEMSControlMode.COMMAND_CHARGING_GRID_FIRST,
                "Command Charging (PV First)": RemoteEMSControlMode.COMMAND_CHARGING_PV_FIRST,
                "Command Discharging (PV First)": RemoteEMSControlMode.COMMAND_DISCHARGING_PV_FIRST,
                "Command Discharging (ESS First)": RemoteEMSControlMode.COMMAND_DISCHARGING_ESS_FIRST,
            }.get(option, RemoteEMSControlMode.PCS_REMOTE_CONTROL),
        ),
        available_fn=lambda data, _: data["plant"].get("remote_ems_enable") == 1,
    ),
]

INVERTER_SELECTS = [
    # Add inverter-specific selects if needed
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sigenergy select platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    hub = hass.data[DOMAIN][config_entry.entry_id]["hub"]
    entities = []

    # Add plant selects
    plant_name = config_entry.data[CONF_NAME]
    for description in PLANT_SELECTS:
        entities.append(
            SigenergySelect(
                coordinator=coordinator,
                hub=hub,
                description=description,
                name=f"{plant_name} {description.name}",
                device_type=DEVICE_TYPE_PLANT,
                device_id=None,
            )
        )

    # Add inverter selects
    for inverter_id in coordinator.hub.inverter_slave_ids:
        for description in INVERTER_SELECTS:
            entities.append(
                SigenergySelect(
                    coordinator=coordinator,
                    hub=hub,
                    description=description,
                    name=f"{plant_name} Inverter {inverter_id} {description.name}",
                    device_type=DEVICE_TYPE_INVERTER,
                    device_id=inverter_id,
                )
            )

    async_add_entities(entities)


class SigenergySelect(CoordinatorEntity, SelectEntity):
    """Representation of a Sigenergy select."""

    entity_description: SigenergySelectEntityDescription

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        hub: Any,
        description: SigenergySelectEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[int],
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self.entity_description = description
        self.hub = hub
        self._attr_name = name
        self._device_type = device_type
        self._device_id = device_id
        self._attr_options = description.options
        
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
                name=f"Inverter {device_id}",
                manufacturer="Sigenergy",
                model=model,
                serial_number=serial_number,
                via_device=(DOMAIN, f"{coordinator.hub.host}_plant"),
            )

    @property
    def current_option(self) -> str:
        """Return the selected entity option."""
        if self.coordinator.data is None:
            return self.options[0] if self.options else ""
            
        return self.entity_description.current_option_fn(self.coordinator.data, self._device_id)

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
        elif self._device_type == DEVICE_TYPE_INVERTER:
            if not (
                self.coordinator.data is not None
                and "inverters" in self.coordinator.data
                and self._device_id in self.coordinator.data["inverters"]
            ):
                return False
                
            # Check if the entity has a specific availability function
            if hasattr(self.entity_description, "available_fn"):
                return self.entity_description.available_fn(self.coordinator.data, self._device_id)
                
            return True
            
        return False

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        try:
            await self.entity_description.select_option_fn(self.hub, self._device_id, option)
            await self.coordinator.async_request_refresh()
        except SigenergyModbusError as error:
            _LOGGER.error("Failed to select option %s for %s: %s", option, self.name, error)