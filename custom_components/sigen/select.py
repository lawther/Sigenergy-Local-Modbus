"""Select platform for Sigenergy ESS integration."""
from __future__ import annotations

import logging
import asyncio
from typing import Coroutine
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from homeassistant.components.select import SelectEntity, SelectEntityDescription
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
    EMSWorkMode,
    RemoteEMSControlMode,
    DEVICE_TYPE_DC_CHARGER,
)
from .coordinator import SigenergyDataUpdateCoordinator
from .modbus import SigenergyModbusError
from .common import *

_LOGGER = logging.getLogger(__name__)

# Map of grid codes to country names
GRID_CODE_MAP = {
    1: "Germany",
    2: "UK",
    3: "Italy",
    4: "Spain",
    5: "Portugal",
    6: "France",
    7: "Poland",
    8: "Hungary",
    9: "Belgium",
    10: "Norway",
    11: "Sweden",
    12: "Finland",
    13: "Denmark",
    # Add more mappings as they are discovered
}

# Reverse mapping for looking up codes by country name
COUNTRY_TO_CODE_MAP = {country: code for code, country in GRID_CODE_MAP.items()}
# Debug log the grid code map
_LOGGER.debug("GRID_CODE_MAP: %s", GRID_CODE_MAP)

def _get_grid_code_display(data, device_name): # Changed inverter_id to device_name
    """Get the display value for grid code with debug logging."""
    # Log the available inverter data for debugging
    # Access using device_name
    # if device_name in data.get("inverters", {}):
    #     # _LOGGER.debug("Available inverter data keys for %s: %s", device_name, list(data["inverters"][device_name].keys()))
    # else:
    #     _LOGGER.debug("No data available for inverter %s", device_name)
    #     return "Unknown"
    
    # Get the raw grid code value using device_name
    grid_code = data["inverters"].get(device_name, {}).get("inverter_grid_code")
    
    # Debug log the value and type
    # _LOGGER.debug("Grid code value for %s: %s, type: %s", device_name, grid_code, type(grid_code))
    
    # Handle None case
    if grid_code is None:
        return "Unknown"
        
    # Try to convert to int and look up in map
    try:
        grid_code_int = int(grid_code)
        # _LOGGER.debug("Converted grid code to int: %s", grid_code_int)
        
        # Look up in map
        result = GRID_CODE_MAP.get(grid_code_int)
        # _LOGGER.debug("Grid code map lookup result: %s", result)
        
        if result is not None:
            return result
        else:
            return f"Unknown ({grid_code})"
    except (ValueError, TypeError) as e:
        _LOGGER.debug("Error converting grid code for %s: %s", device_name, e)
        return f"Unknown ({grid_code})"



@dataclass
class SigenergySelectEntityDescription(SelectEntityDescription):
    """Class describing Sigenergy select entities."""

    # The second argument 'identifier' will be device_name for inverters, device_id otherwise. Default returns empty string.
    current_option_fn: Callable[[Dict[str, Any], Optional[Any]], str] = lambda data, identifier: ""
    # Make select_option_fn async and update type hint
    select_option_fn: Callable[[Any, Optional[Any], str], Coroutine[Any, Any, None]] = lambda hub, identifier, option: asyncio.sleep(0) # Placeholder async lambda
    available_fn: Callable[[Dict[str, Any], Optional[Any]], bool] = lambda data, _: True
    entity_registry_enabled_default: bool = True


PLANT_SELECTS = [
    SigenergySelectEntityDescription(
        key="plant_remote_ems_control_mode",
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
        current_option_fn=lambda data, _: {
            RemoteEMSControlMode.PCS_REMOTE_CONTROL: "PCS Remote Control",
            RemoteEMSControlMode.STANDBY: "Standby",
            RemoteEMSControlMode.MAXIMUM_SELF_CONSUMPTION: "Maximum Self Consumption",
            RemoteEMSControlMode.COMMAND_CHARGING_GRID_FIRST: "Command Charging (Grid First)",
            RemoteEMSControlMode.COMMAND_CHARGING_PV_FIRST: "Command Charging (PV First)",
            RemoteEMSControlMode.COMMAND_DISCHARGING_PV_FIRST: "Command Discharging (PV First)",
            RemoteEMSControlMode.COMMAND_DISCHARGING_ESS_FIRST: "Command Discharging (ESS First)",
        }.get(data["plant"].get("plant_remote_ems_control_mode"), "Unknown"),
        select_option_fn=lambda hub, _, option: hub.async_write_plant_parameter( # Already returns awaitable
            "plant_remote_ems_control_mode",
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
        available_fn=lambda data, _: data["plant"].get("plant_remote_ems_enable") == 1,
    ),
]

INVERTER_SELECTS = [
    SigenergySelectEntityDescription(
        key="inverter_grid_code",
        name="Grid Code",
        icon="mdi:transmission-tower",
        options=list(GRID_CODE_MAP.values()),
        entity_category=EntityCategory.CONFIG,
        # Use identifier (device_name for inverters)
        current_option_fn=lambda data, identifier: _get_grid_code_display(data, identifier),
        # Use identifier (device_name for inverters)
        select_option_fn=lambda hub, identifier, option: hub.async_write_inverter_parameter( # Already returns awaitable
            identifier,
            "inverter_grid_code",
            COUNTRY_TO_CODE_MAP.get(option, 0)  # Default to 0 if country not found
        ),
    ),
]

AC_CHARGER_SELECTS = []
DC_CHARGER_SELECTS = []

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sigenergy select platform."""
    coordinator: SigenergyDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    plant_name = config_entry.data[CONF_NAME]
    _LOGGER.debug(f"Starting to add {SigenergySelect}")
    # Add plant Selects
    entities : list[SigenergySelect] = generate_sigen_entity(plant_name, None, None, coordinator, SigenergySelect,
                                           PLANT_SELECTS, DEVICE_TYPE_PLANT)

    # Add inverter Selects
    for device_name, device_conn in coordinator.hub.inverter_connections.items():
        entities += generate_sigen_entity(plant_name, device_name, device_conn, coordinator, SigenergySelect,
                                           INVERTER_SELECTS, DEVICE_TYPE_INVERTER)

    # Add AC charger Selects
    for device_name, device_conn in coordinator.hub.ac_charger_connections.items():
        entities += generate_sigen_entity(plant_name, device_name, device_conn, coordinator, SigenergySelect,
                                           AC_CHARGER_SELECTS, DEVICE_TYPE_AC_CHARGER)

    # Add DC charger Selects
    for device_name, device_conn in coordinator.hub.dc_charger_connections.items():
        entities += generate_sigen_entity(plant_name, device_name, device_conn, coordinator, SigenergySelect,
                                           DC_CHARGER_SELECTS, DEVICE_TYPE_DC_CHARGER)
        
    _LOGGER.debug(f"Class to add {SigenergySelect}")
    async_add_entities(entities)
    return

class SigenergySelect(CoordinatorEntity, SelectEntity):
    """Representation of a Sigenergy select."""

    entity_description: SigenergySelectEntityDescription

    def __init__(
        self,
        coordinator: SigenergyDataUpdateCoordinator,
        description: SigenergySelectEntityDescription,
        name: str,
        device_type: str,
        device_id: Optional[int],
        device_name: Optional[str] = "",
        pv_string_idx: Optional[int] = None,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self.entity_description = description
        self.hub = coordinator.hub
        self._attr_name = name
        self._device_type = device_type
        self._device_id = device_id # Keep slave ID if needed
        self._device_name = device_name # Store device name
        # Ensure options is a list, default to empty list if None
        self._attr_options = description.options if description.options is not None else []
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
        elif device_type == DEVICE_TYPE_DC_CHARGER: # Added DC Charger
             self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_{str(device_name).lower().replace(' ', '_')}")},
                name=device_name,
                manufacturer="Sigenergy",
                model="DC Charger",
                via_device=(DOMAIN, f"{coordinator.hub.config_entry.entry_id}_plant"),
            )


    @property
    def current_option(self) -> str:
        """Return the selected entity option."""
        if self.coordinator.data is None:
            return self.options[0] if self.options else ""
            
        # Pass device_name for inverters, device_id otherwise
        identifier = self._device_name if self._device_type == DEVICE_TYPE_INVERTER else self._device_id
        try:
            option = self.entity_description.current_option_fn(self.coordinator.data, identifier)
            return option if option is not None else ""
        except Exception as e:
            _LOGGER.error(f"Error getting current_option for {self.entity_id} (identifier: {identifier}): {e}")
            return ""


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

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        try:
            # Pass device_name for inverters, device_id otherwise
            identifier = self._device_name if self._device_type == DEVICE_TYPE_INVERTER else self._device_id
            await self.entity_description.select_option_fn(self.hub, identifier, option)
            await self.coordinator.async_request_refresh()
        except SigenergyModbusError as error:
            _LOGGER.error("Failed to select option %s for %s: %s", option, self.name, error)
        except Exception as e:
             _LOGGER.error(f"Unexpected error selecting option for {self.entity_id}: {e}")