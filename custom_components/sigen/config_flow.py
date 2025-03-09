"""Config flow for Sigenergy ESS integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_AC_CHARGER_SLAVE_IDS,
    CONF_DC_CHARGER_SLAVE_IDS,
    CONF_DEVICE_TYPE,
    CONF_INVERTER_SLAVE_IDS,
    CONF_PLANT_ID,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DEVICE_TYPE_PLANT,
    DOMAIN,
    STEP_USER,
)

_LOGGER = logging.getLogger(__name__)

# Schema definitions for each step
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_PLANT_ID, default=DEFAULT_SLAVE_ID): int,
        vol.Required(CONF_INVERTER_SLAVE_IDS, default="1"): str,
        vol.Optional(CONF_AC_CHARGER_SLAVE_IDS, default=""): str,
        vol.Optional(CONF_DC_CHARGER_SLAVE_IDS, default=""): str,
    }
)

def validate_slave_ids(raw_ids: str, field_name: str) -> Tuple[List[int], Dict[str, str]]:
    """Validate slave IDs from a comma-separated string.
    
    Returns:
        Tuple containing list of valid IDs and dict of errors (if any)
        An empty string input will return an empty list with no errors.
    """
    errors = {}
    id_list = []
    
    # Skip validation for empty strings (indicating no devices of this type)
    if not raw_ids or raw_ids.strip() == "":
        return [], errors
    
    for part in raw_ids.split(","):
        part = part.strip()
        if not part:
            continue
        if part.isdigit():
            val = int(part)
            if not (1 <= val <= 246):
                errors[field_name] = "each_id_must_be_between_1_and_246"
                break
            id_list.append(val)
        else:
            errors[field_name] = "invalid_integer_value"
            break
            
    # Check for duplicate IDs
    if not errors and not _LOGGER.isEnabledFor(logging.DEBUG):
        if len(set(id_list)) != len(id_list):
            errors[field_name] = "duplicate_ids_found"
            
    return id_list, errors

class SigenergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sigenergy ESS."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data = {}
        self._plants = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_USER,
                data_schema=STEP_USER_DATA_SCHEMA
            )

        # Store plant configuration
        self._data.update(user_input)

        # Check if any plants exist in the system
        await self._async_load_plants()
        plant_no = len(self._plants)

        # Process and validate all slave IDs
        inverter_ids, inv_errors = validate_slave_ids(
            user_input.get(CONF_INVERTER_SLAVE_IDS, ""), 
            CONF_INVERTER_SLAVE_IDS
        )
        errors.update(inv_errors)
        
        ac_charger_ids, ac_errors = validate_slave_ids(
            user_input.get(CONF_AC_CHARGER_SLAVE_IDS, ""), 
            CONF_AC_CHARGER_SLAVE_IDS
        )
        errors.update(ac_errors)
        
        dc_charger_ids, dc_errors = validate_slave_ids(
            user_input.get(CONF_DC_CHARGER_SLAVE_IDS, ""), 
            CONF_DC_CHARGER_SLAVE_IDS
        )
        errors.update(dc_errors)

        # Check for conflicts between device types
        if not errors:
            # Check AC charger IDs don't conflict with inverter IDs
            # Note: Empty AC charger list is valid and means no AC chargers present
            if ac_charger_ids:
                for ac_id in ac_charger_ids:
                    if ac_id in inverter_ids:
                        errors[CONF_AC_CHARGER_SLAVE_IDS] = "ac_charger_conflicts_inverter"
                        break
            
            # Check DC charger IDs are all included in inverter IDs
            # Note: Empty DC charger list is valid and means no DC chargers present
            if dc_charger_ids:
                for dc_id in dc_charger_ids:
                    if dc_id not in inverter_ids:
                        errors[CONF_DC_CHARGER_SLAVE_IDS] = "dc_charger_requires_inverter"
                        break

        # If there are errors, show the form again
        if errors:
            return self.async_show_form(
                step_id=STEP_USER,
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors
            )

        # Store the validated lists
        self._data[CONF_INVERTER_SLAVE_IDS] = inverter_ids
        self._data[CONF_AC_CHARGER_SLAVE_IDS] = ac_charger_ids
        self._data[CONF_DC_CHARGER_SLAVE_IDS] = dc_charger_ids
        
        # Store the plant name generated based on the number of installed plants
        self._data[CONF_NAME] = f"Sigen{' ' if plant_no == 0 else f' {plant_no} '}Plant"
        
        # Set the device type as plant
        self._data[CONF_DEVICE_TYPE] = DEVICE_TYPE_PLANT

        # Create the configuration entry with the default name
        return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

    async def _async_load_plants(self) -> None:
        """Load existing plants from config entries."""
        self._plants = {}
        
        # Log the number of config entries for debugging
        _LOGGER.debug("Total config entries: %s", len(self.hass.config_entries.async_entries(DOMAIN)))
        
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            # Log each entry to see what's being found
            _LOGGER.debug("Found entry: %s, device type: %s", 
                        entry.entry_id, 
                        entry.data.get(CONF_DEVICE_TYPE))
                        
            if entry.data.get(CONF_DEVICE_TYPE) in [DEVICE_TYPE_PLANT]:
                self._plants[entry.entry_id] = entry.data.get(CONF_NAME, f"Plant {entry.entry_id}")
                
        # Log the plants that were found
        _LOGGER.debug("Found plants: %s", self._plants)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle dynamic reconfiguration of inverter and AC charger slave IDs."""
        if user_input is None:
            # Create schema with current values
            schema = self._create_reconfigure_schema()
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=schema,
            )

        # Process and validate all slave IDs
        errors = {}
        inverter_ids, inv_errors = validate_slave_ids(
            user_input.get(CONF_INVERTER_SLAVE_IDS, ""), 
            CONF_INVERTER_SLAVE_IDS
        )
        errors.update(inv_errors)
        
        ac_charger_ids, ac_errors = validate_slave_ids(
            user_input.get(CONF_AC_CHARGER_SLAVE_IDS, ""), 
            CONF_AC_CHARGER_SLAVE_IDS
        )
        errors.update(ac_errors)
        
        dc_charger_ids, dc_errors = validate_slave_ids(
            user_input.get(CONF_DC_CHARGER_SLAVE_IDS, ""), 
            CONF_DC_CHARGER_SLAVE_IDS
        )
        errors.update(dc_errors)

        # Check for conflicts between device types
        if not errors:
            # Note: Empty AC charger list is valid and means no AC chargers present
            if ac_charger_ids:
                for ac_id in ac_charger_ids:
                    if ac_id in inverter_ids:
                        errors[CONF_AC_CHARGER_SLAVE_IDS] = "ac_charger_conflicts_inverter"
                        break
            
            # Note: Empty DC charger list is valid and means no DC chargers present
            if dc_charger_ids:
                for dc_id in dc_charger_ids:
                    if dc_id not in inverter_ids:
                        errors[CONF_DC_CHARGER_SLAVE_IDS] = "dc_charger_requires_inverter"
                        break

        if errors:
            # Re-create schema with user input values for error display
            schema = self._create_reconfigure_schema(
                user_input.get(CONF_INVERTER_SLAVE_IDS, ""),
                user_input.get(CONF_AC_CHARGER_SLAVE_IDS, ""),
                user_input.get(CONF_DC_CHARGER_SLAVE_IDS, "")
            )
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=schema,
                errors=errors,
            )

        # Update the data with the validated IDs
        self._data[CONF_INVERTER_SLAVE_IDS] = inverter_ids
        self._data[CONF_AC_CHARGER_SLAVE_IDS] = ac_charger_ids
        self._data[CONF_DC_CHARGER_SLAVE_IDS] = dc_charger_ids
        
        # Update the configuration entry with the new data
        self.hass.config_entries.async_update_entry(
            self.context.get("entry"), data=self._data
        )
        return self.async_create_entry(title=self._data.get(CONF_NAME, "Reconfigured"), data=self._data)

    def _create_reconfigure_schema(self, inv_ids="", ac_ids="", dc_ids=""):
        """Create schema for reconfiguration step with default or provided values."""
        # Use provided values or get current values from data
        if not inv_ids:
            current_ids = self._data.get(CONF_INVERTER_SLAVE_IDS, [])
            inv_ids = ", ".join(str(i) for i in current_ids) if current_ids else ""
        
        if not ac_ids:
            current_ac_ids = self._data.get(CONF_AC_CHARGER_SLAVE_IDS, [])
            ac_ids = ", ".join(str(i) for i in current_ac_ids) if current_ac_ids else ""
        
        if not dc_ids:
            current_dc_ids = self._data.get(CONF_DC_CHARGER_SLAVE_IDS, [])
            dc_ids = ", ".join(str(i) for i in current_dc_ids) if current_dc_ids else ""
        
        return vol.Schema({
            vol.Required(CONF_INVERTER_SLAVE_IDS, default=inv_ids): str,
            vol.Optional(CONF_AC_CHARGER_SLAVE_IDS, default=ac_ids): str,
            vol.Optional(CONF_DC_CHARGER_SLAVE_IDS, default=dc_ids): str,
        })

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SigenergyOptionsFlowHandler(config_entry)

class SigenergyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Sigenergy options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)
        self._data = dict(config_entry.data)

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options for the custom component."""
        return await self.async_step_reconfigure(user_input=user_input)

    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration of inverter and AC charger slave IDs."""
        errors = {}
        
        if user_input is None:
            # Create schema with current values
            schema = self._create_reconfigure_schema()
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=schema,
            )

        # Process and validate all slave IDs
        inverter_ids, inv_errors = validate_slave_ids(
            user_input.get(CONF_INVERTER_SLAVE_IDS, ""), 
            CONF_INVERTER_SLAVE_IDS
        )
        errors.update(inv_errors)
        
        ac_charger_ids, ac_errors = validate_slave_ids(
            user_input.get(CONF_AC_CHARGER_SLAVE_IDS, ""), 
            CONF_AC_CHARGER_SLAVE_IDS
        )
        errors.update(ac_errors)
        
        dc_charger_ids, dc_errors = validate_slave_ids(
            user_input.get(CONF_DC_CHARGER_SLAVE_IDS, ""), 
            CONF_DC_CHARGER_SLAVE_IDS
        )
        errors.update(dc_errors)

        # Check for conflicts between device types
        if not errors:
            # Note: Empty AC charger list is valid and means no AC chargers present
            if ac_charger_ids:
                for ac_id in ac_charger_ids:
                    if ac_id in inverter_ids:
                        errors[CONF_AC_CHARGER_SLAVE_IDS] = "ac_charger_conflicts_inverter"
                        break
            
            # Note: Empty DC charger list is valid and means no DC chargers present
            if dc_charger_ids:
                for dc_id in dc_charger_ids:
                    if dc_id not in inverter_ids:
                        errors[CONF_DC_CHARGER_SLAVE_IDS] = "dc_charger_requires_inverter"
                        break

        if errors:
            # Re-create schema with user input values for error display
            schema = self._create_reconfigure_schema(
                user_input.get(CONF_INVERTER_SLAVE_IDS, ""),
                user_input.get(CONF_AC_CHARGER_SLAVE_IDS, ""),
                user_input.get(CONF_DC_CHARGER_SLAVE_IDS, "")
            )
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=schema,
                errors=errors,
            )

        # Ensure we preserve the device type (especially important if it's DEVICE_TYPE_PLANT)
        device_type = self._data.get(CONF_DEVICE_TYPE)
        
        # Update the configuration entry with the new IDs
        new_data = {
            **self._data, 
            CONF_INVERTER_SLAVE_IDS: inverter_ids, 
            CONF_AC_CHARGER_SLAVE_IDS: ac_charger_ids, 
            CONF_DC_CHARGER_SLAVE_IDS: dc_charger_ids,
        }
        
        # Ensure device type is preserved
        if device_type:
            new_data[CONF_DEVICE_TYPE] = device_type
            
        self.hass.config_entries.async_update_entry(
            self.config_entry, data=new_data
        )
        
        return self.async_create_entry(title="", data={})

    def _create_reconfigure_schema(self, inv_ids="", ac_ids="", dc_ids=""):
        """Create schema for reconfiguration step with default or provided values."""
        # Use provided values or get current values from data
        if not inv_ids:
            current_ids = self._data.get(CONF_INVERTER_SLAVE_IDS, [])
            inv_ids = ", ".join(str(i) for i in current_ids) if current_ids else ""
        
        if not ac_ids:
            current_ac_ids = self._data.get(CONF_AC_CHARGER_SLAVE_IDS, [])
            ac_ids = ", ".join(str(i) for i in current_ac_ids) if current_ac_ids else ""
        
        if not dc_ids:
            current_dc_ids = self._data.get(CONF_DC_CHARGER_SLAVE_IDS, [])
            dc_ids = ", ".join(str(i) for i in current_dc_ids) if current_dc_ids else ""
        
        return vol.Schema({
            vol.Required(CONF_INVERTER_SLAVE_IDS, default=inv_ids): str,
            vol.Required(CONF_AC_CHARGER_SLAVE_IDS, default=ac_ids): str,
            vol.Required(CONF_DC_CHARGER_SLAVE_IDS, default=dc_ids): str,
        })