"""The Sigenergy ESS integration. Common code."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Optional
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.core import HomeAssistant

from .const import (CONF_SLAVE_ID, DOMAIN, DEVICE_TYPE_INVERTER, DEVICE_TYPE_PLANT)

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
        hass: Optional[HomeAssistant] = None
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
    device_name = device_name if device_name else plant_name

    entities = []
    for description in entity_description:
        _LOGGER.debug("Description: %s", description)

        entity_kwargs = {
            "coordinator": coordinator,
            "description": description,
            "name": f"{device_name} {description.name}",
            "device_type": device_type,
            "device_id": generate_device_id(device_name, device_type),
            "device_name": device_name,
        }
        
        if hasattr(description, 'source_key') and description.source_key:
            source_entity_id  = get_source_entity_id(
                device_type,
                device_name,
                description.source_key,
                coordinator,
                hass
            )
            if source_entity_id:
                entity_kwargs["source_entity_id"] = source_entity_id
                _LOGGER.debug("Using source entity ID: %s", source_entity_id)
            else:
                _LOGGER.warning("No source entity ID found for source key '%s' (device: %s). Skipping entity '%s'.", description.source_key, device_name, description.name)
                continue # Skip this entity

        if hasattr(description, 'round_digits') and description.round_digits is not None:
            entity_kwargs["round_digits"] = description.round_digits
            
        if hasattr(description, 'max_sub_interval') and description.max_sub_interval is not None:
            entity_kwargs["max_sub_interval"] = description.max_sub_interval
        
        # if device_type == DEVICE_TYPE_INVERTER:
        #     _LOGGER.debug("Creating inverter entity: %s with kwargs: %s", description.key, entity_kwargs)

        try:
            new_entity = entity_class(**entity_kwargs)
            entities.append(new_entity)
            # _LOGGER.debug("Created entity: %s", new_entity)

        except Exception as ex:
            _LOGGER.exception("Error creating entity '%s' for device '%s': %s", description.name, device_name, ex) # Use .exception
            _LOGGER.debug("Entity creation failed with description: %s", description)
            _LOGGER.debug("Entity creation failed with kwargs: %s", entity_kwargs)
    return entities

@staticmethod
def get_source_entity_id(device_type, device_name, source_key, coordinator, hass):
    """Get the source entity ID for an integration sensor."""
    # Try to find entities by unique ID pattern
    try:
        # Get the Home Assistant entity registry
        ha_entity_registry = async_get_entity_registry(hass)

        # Determine the unique ID pattern to look for
        unique_id_pattern = generate_unique_entity_id(
            device_type=device_type,
            device_name=device_name,
            coordinator=coordinator,
            attr_key=source_key
        )

        _LOGGER.debug("Looking for entity with unique ID pattern: %s", unique_id_pattern)
        entity_id = ha_entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id_pattern)

        if entity_id is None:
            _LOGGER.warning("No entity found for unique ID pattern: %s", unique_id_pattern)
            _LOGGER.debug("unique ID pattern constructed from: \n config_entry_id: %s \n device_type: %s \n device_name: %s \n source_key: %s",
                            coordinator.hub.config_entry.entry_id, device_type, device_name, source_key)
        else:
            _LOGGER.debug("Found entity ID: %s", entity_id)

        return entity_id
    except Exception as ex:
        _LOGGER.warning("Error looking for entity with config entry ID: %s", ex)

@staticmethod
def generate_unique_entity_id(
        device_type: str,
        device_name: str | None,
        coordinator,
        attr_key: str,
        pv_string_idx: int | None = None,
) -> str:
    """Generate a unique ID for the entity."""

    # Use the device name if available, otherwise use the device type
    unique_device_part = generate_device_id(device_name, device_type)
    if pv_string_idx is not None:
        unique_id = f"{coordinator.hub.config_entry.entry_id}_{unique_device_part}_pv{pv_string_idx}_{attr_key}"
    else:
        unique_id = f"{coordinator.hub.config_entry.entry_id}_{unique_device_part}_{attr_key}"

    _LOGGER.debug("Generated unique ID: %s", unique_id)
    return unique_id

@staticmethod
def generate_device_id(
    device_name: str,
    device_type: str,
) -> str:
    unique_device_part = str(device_name).lower().replace(' ', '_') if device_name else device_type
    return unique_device_part