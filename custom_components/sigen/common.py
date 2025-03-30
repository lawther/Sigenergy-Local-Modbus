"""The Sigenergy ESS integration. Common code."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Optional
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import (CONF_SLAVE_ID)

_LOGGER = logging.getLogger(__name__)

@staticmethod
def get_suffix_if_not_one(name: str) -> str:
    """Get the last part of the name if it is a number other than 1."""
    return name.split()[-1].strip() + " " if len(name.split()) > 1 and name.split()[-1].isdigit() and name.split()[-1] != "1" else ""

def generate_device_name(plant_name: str, device_name: str) -> str:
    """Generate a device name based on plant name and device name."""
    device_type = " ".join(device_name.split()[:-1]) if len(device_name.split()) > 1 and device_name.split()[-1].isdigit() else device_name
    return f"Sigen {get_suffix_if_not_one(plant_name)}{device_type}{get_suffix_if_not_one(device_name)}"

@staticmethod
def generate_sigen_entity(
        plant_name: str,
        device_name: str | None,
        device_conn: dict | None,
        coordinator,
        entity_class: type,
        entity_description: list,
        device_type: str,
        source_entity_id: Optional[str] = None,
        round_digits: Optional[int] = None,
        max_sub_interval: Optional[int] = None
        ) -> list:
    """
    Generate entities for Sigenergy components.
    This function creates a list of entities for a specific device type by
    applying the given entity class with appropriate descriptions.
    Args:
        plant_name (str): Name of the plant/installation
        device_name (str | None): Name of the device, if None will use plant_name
        device_conn (dict | None): Device connection parameters containing slave ID
        coordinator (SigenergyDataUpdateCoordinator): Data update coordinator
        entity_class (type): The entity class to instantiate
        entity_description (list[SigenergyNumberEntityDescription]): List of entity descriptions
        device_type (str): Type of the device
    Returns:
        list: A list of instantiated entities for the device
    """
    if device_name is None:
        device_name = plant_name
        device_id = None
    else:
        device_name = generate_device_name(plant_name, device_name)
        device_id = device_conn[CONF_SLAVE_ID]

    # Helper function to get source entity ID
    def get_source_entity_id(device_type, device_id, source_key):
        """Get the source entity ID for an integration sensor."""
        # Try to find entities by unique ID pattern
        try:
            # Get the Home Assistant entity registry to search
            ha_entity_registry = async_get_entity_registry(hass)
            
            # Determine the unique ID pattern to look for
            config_entry_id = coordinator.hub.config_entry.entry_id
            _LOGGER.debug("Looking for entity with config entry ID: %s, source key: %s, device type: %s, device ID: %s",
                            config_entry_id, source_key, device_type, device_id)
            
            unique_id_pattern = f"{config_entry_id}_{device_type}{f'_{device_id}' if device_id > 1 else ''}_{source_key}"

            _LOGGER.debug("Looking for entity with unique ID pattern: %s", unique_id_pattern)
            entity_id = ha_entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id_pattern)
            _LOGGER.debug("Found entity ID: %s", entity_id)

            return entity_id
        except Exception as ex:
            _LOGGER.warning("Error looking for entity with config entry ID: %s", ex)
        

    entities = []
    for description in entity_description:
        _LOGGER.debug("Description: %s", description)
        entity_kwargs = {
            "coordinator": coordinator,
            "description": description,
            "name": f"{device_name} {description.name}",
            "device_type": device_type,
            "device_id": device_id,
            "device_name": device_name,
        }
        
        if source_entity_id is not None:
            entity_kwargs["source_entity_id"] = source_entity_id
            
        if round_digits is not None:
            entity_kwargs["round_digits"] = round_digits
            
        if max_sub_interval is not None:
            entity_kwargs["max_sub_interval"] = max_sub_interval
            
        entities.append(entity_class(**entity_kwargs))
    return entities

