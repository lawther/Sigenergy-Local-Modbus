"""Config flow for Sigenergy ESS integration."""
# pylint: disable=import-error
# pyright: reportMissingImports=false
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DEVELOPER_MODE,
    CONF_AC_CHARGER_SLAVE_IDS,
    CONF_DC_CHARGER_SLAVE_IDS,
    CONF_DEVICE_TYPE,
    CONF_INVERTER_SLAVE_IDS,
    CONF_PARENT_DEVICE_ID,
    CONF_PLANT_ID,
    CONF_SLAVE_ID,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DEVICE_TYPE_INVERTER,
    DEVICE_TYPE_PLANT,
    DOMAIN,
    STEP_USER,
    DEFAULT_PLANT_NAME,
)

_LOGGER = logging.getLogger(__name__)

# Schema definitions for each step
STEP_USER_DATA_SCHEMA = vol.Schema({})  # Empty schema for initial step

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_PLANT_ID, default=DEFAULT_SLAVE_ID): int,
        vol.Required(CONF_INVERTER_SLAVE_IDS, default="1"): str,
        vol.Required(CONF_AC_CHARGER_SLAVE_IDS, default=""): str,
        vol.Required(CONF_DC_CHARGER_SLAVE_IDS, default=""): str,
    }
)

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

        # Process the inverter slave IDs
        raw_ids = user_input.get(CONF_INVERTER_SLAVE_IDS, "")
        id_list = []
        
        for part in raw_ids.split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                val = int(part)
                if not (1 <= val <= 246):
                    errors[CONF_INVERTER_SLAVE_IDS] = "Each ID must be between 1 and 246."
                    break
                id_list.append(val)
            else:
                errors[CONF_INVERTER_SLAVE_IDS] = "Invalid integer value."
                break

        # Check for duplicate Inverter IDs
        if not DEVELOPER_MODE:
            if len(set(id_list)) != len(id_list):
                errors[CONF_INVERTER_SLAVE_IDS] = "Duplicate IDs found."
            
        # Process the AC charger slave IDs
        raw_ac_ids = user_input.get(CONF_AC_CHARGER_SLAVE_IDS, "")
        ac_id_list = []
        
        for part in raw_ac_ids.split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                val = int(part)
                if not (1 <= val <= 246):
                    errors[CONF_AC_CHARGER_SLAVE_IDS] = "Each ID must be between 1 and 246."
                    break
                ac_id_list.append(val)
            else:
                errors[CONF_AC_CHARGER_SLAVE_IDS] = "Invalid integer value."
                break

        # Check for duplicates in AC charger IDs
        if not DEVELOPER_MODE:
            if len(set(ac_id_list)) != len(ac_id_list):
                errors[CONF_AC_CHARGER_SLAVE_IDS] = "Duplicate IDs found."

        # If there are errors, show the form again
        if errors:
            return self.async_show_form(
                step_id=STEP_USER,
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=errors
            )

        # Store the validated list of inverter slave IDs
        self._data[CONF_INVERTER_SLAVE_IDS] = id_list
        
        # Store the validated list of AC charger slave IDs
        self._data[CONF_AC_CHARGER_SLAVE_IDS] = ac_id_list
        
        # Process the DC charger slave IDs
        raw_dc_ids = user_input.get(CONF_DC_CHARGER_SLAVE_IDS, "")
        dc_id_list = []
        
        for part in raw_dc_ids.split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                val = int(part)
                if not (1 <= val <= 246):
                    errors[CONF_DC_CHARGER_SLAVE_IDS] = "Each ID must be between 1 and 246."
                    break
                dc_id_list.append(val)
            else:
                errors[CONF_DC_CHARGER_SLAVE_IDS] = "Invalid integer value."
                break

        # Check for duplicates in DC charger IDs
        if not DEVELOPER_MODE:
            if len(set(dc_id_list)) != len(dc_id_list):
                errors[CONF_DC_CHARGER_SLAVE_IDS] = "Duplicate IDs found."

        # Store the validated list of DC charger slave IDs
        self._data[CONF_DC_CHARGER_SLAVE_IDS] = dc_id_list

        # Store the plant name generated based on the number of installed plants
        self._data[CONF_NAME] = f"{DEFAULT_PLANT_NAME}{'' if plant_no == 0 else f' {plant_no}'}"

        # Create the configuration entry with the default name
        return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

    def generate_inverter_config_schema(self) -> vol.Schema:
        """Generate the inverter configuration schema."""
        # Find the next available slave ID after existing inverters to suggest as default
        existing_slave_ids = []
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data.get(CONF_DEVICE_TYPE) in [DEVICE_TYPE_PLANT]:
                existing_slave_ids.extend(entry.data.get(CONF_INVERTER_SLAVE_IDS, []))
            elif entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_INVERTER:
                existing_slave_ids.append(entry.data.get(CONF_SLAVE_ID, 0))

        # Start from the highest existing slave ID + 1
        next_slave_id = max(existing_slave_ids, default=0) + 1

        # Create dynamic schema with plants dropdown and other fields
        return vol.Schema({
            # vol.Required(CONF_NAME, default="Inverter"): str,
            vol.Required(CONF_SLAVE_ID, default=next_slave_id): int,
            vol.Required(CONF_PARENT_DEVICE_ID): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": plant_id, "label": plant_name}
                        for plant_id, plant_name in self._plants.items()
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        })

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
            # Retrieve current inverter slave IDs as a comma-separated string
            current_ids = self._data.get(CONF_INVERTER_SLAVE_IDS, [])
            current_str = ", ".join(str(i) for i in current_ids) if current_ids else ""
            
            # Retrieve current AC charger slave IDs as a comma-separated string
            current_ac_ids = self._data.get(CONF_AC_CHARGER_SLAVE_IDS, [])
            current_ac_str = ", ".join(str(i) for i in current_ac_ids) if current_ac_ids else ""
            
            # Retrieve current DC charger slave IDs as a comma-separated string
            current_dc_ids = self._data.get(CONF_DC_CHARGER_SLAVE_IDS, [])
            current_dc_str = ", ".join(str(i) for i in current_dc_ids) if current_dc_ids else ""
            
            schema = vol.Schema({
                vol.Required(CONF_INVERTER_SLAVE_IDS, default=current_str): str,
                vol.Required(CONF_AC_CHARGER_SLAVE_IDS, default=current_ac_str): str,
                vol.Required(CONF_DC_CHARGER_SLAVE_IDS, default=current_dc_str): str,
            })
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=schema,
            )

        errors = {}
        
        # Process the inverter slave IDs
        raw_ids = user_input.get(CONF_INVERTER_SLAVE_IDS, "")
        id_list = []
        for part in raw_ids.split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                val = int(part)
                if not (1 <= val <= 246):
                    errors[CONF_INVERTER_SLAVE_IDS] = "Each ID must be between 1 and 246."
                    break
                id_list.append(val)
            else:
                errors[CONF_INVERTER_SLAVE_IDS] = "Invalid integer value."
                break

        # Check for duplicate Inverter IDs
        if not DEVELOPER_MODE:
            if len(set(id_list)) != len(id_list):
                errors[CONF_INVERTER_SLAVE_IDS] = "Duplicate IDs found."
            
        # Process the AC charger slave IDs
        raw_ac_ids = user_input.get(CONF_AC_CHARGER_SLAVE_IDS, "")
        ac_id_list = []
        for part in raw_ac_ids.split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                val = int(part)
                if not (1 <= val <= 246):
                    errors[CONF_AC_CHARGER_SLAVE_IDS] = "Each ID must be between 1 and 246."
                    break
                ac_id_list.append(val)
            else:
                errors[CONF_AC_CHARGER_SLAVE_IDS] = "Invalid integer value."
                break

        # Check for duplicates in AC charger IDs
        if not DEVELOPER_MODE:
            if len(set(ac_id_list)) != len(ac_id_list):
                errors[CONF_AC_CHARGER_SLAVE_IDS] = "Duplicate IDs found."
            
        # Process the DC charger slave IDs
        raw_dc_ids = user_input.get(CONF_DC_CHARGER_SLAVE_IDS, "")
        dc_id_list = []
        for part in raw_dc_ids.split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                val = int(part)
                if not (1 <= val <= 246):
                    errors[CONF_DC_CHARGER_SLAVE_IDS] = "Each ID must be between 1 and 246."
                    break
                dc_id_list.append(val)
            else:
                errors[CONF_DC_CHARGER_SLAVE_IDS] = "Invalid integer value."
                break

        # Check for duplicates in DC charger IDs
        if not DEVELOPER_MODE:
            if len(set(dc_id_list)) != len(dc_id_list):
                errors[CONF_DC_CHARGER_SLAVE_IDS] = "Duplicate IDs found."

        if errors:
            schema = vol.Schema({
                vol.Required(CONF_INVERTER_SLAVE_IDS, default=raw_ids): str,
                vol.Required(CONF_AC_CHARGER_SLAVE_IDS, default=raw_ac_ids): str,
                vol.Required(CONF_DC_CHARGER_SLAVE_IDS, default=raw_dc_ids): str,
            })
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=schema,
                errors=errors,
            )

        # Update the data with the validated IDs
        self._data[CONF_INVERTER_SLAVE_IDS] = id_list
        self._data[CONF_AC_CHARGER_SLAVE_IDS] = ac_id_list
        self._data[CONF_DC_CHARGER_SLAVE_IDS] = dc_id_list
        
        # Update the configuration entry with the new data
        self.hass.config_entries.async_update_entry(
            self.context.get("entry"), data=self._data
        )
        return self.async_create_entry(title=self._data.get(CONF_NAME, "Reconfigured"), data=self._data)

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

    async def async_step_init(self, user_input=None):
        """Manage the options for the custom component."""
        return await self.async_step_reconfigure()

    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration of inverter and AC charger slave IDs."""
        errors = {}
        
        if user_input is None:
            # Retrieve current inverter slave IDs as a comma-separated string
            current_ids = self._data.get(CONF_INVERTER_SLAVE_IDS, [])
            current_str = ", ".join(str(i) for i in current_ids) if current_ids else ""
            # Retrieve current AC charger slave IDs as a comma-separated string
            current_ac_ids = self._data.get(CONF_AC_CHARGER_SLAVE_IDS, [])
            current_ac_str = ", ".join(str(i) for i in current_ac_ids) if current_ac_ids else ""
            
            # Retrieve current DC charger slave IDs as a comma-separated string
            current_dc_ids = self._data.get(CONF_DC_CHARGER_SLAVE_IDS, [])
            current_dc_str = ", ".join(str(i) for i in current_dc_ids) if current_dc_ids else ""
            
            schema = vol.Schema({
                vol.Required(CONF_INVERTER_SLAVE_IDS, default=current_str): str,
                vol.Required(CONF_AC_CHARGER_SLAVE_IDS, default=current_ac_str): str,
                vol.Required(CONF_DC_CHARGER_SLAVE_IDS, default=current_dc_str): str,
            })
            
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=schema,
            )

        # Process the inverter slave IDs
        raw_ids = user_input.get(CONF_INVERTER_SLAVE_IDS, "")
        id_list = []
        
        for part in raw_ids.split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                val = int(part)
                if not (1 <= val <= 246):
                    errors[CONF_INVERTER_SLAVE_IDS] = "Each ID must be between 1 and 246."
                    break
                id_list.append(val)
            else:
                errors[CONF_INVERTER_SLAVE_IDS] = "Invalid integer value."
                break

        # Check for duplicate Inverter IDs
        if not DEVELOPER_MODE:
            if len(set(id_list)) != len(id_list):
                errors[CONF_INVERTER_SLAVE_IDS] = "Duplicate IDs found."
            
        # Process the AC charger slave IDs
        raw_ac_ids = user_input.get(CONF_AC_CHARGER_SLAVE_IDS, "")
        ac_id_list = []
        
        for part in raw_ac_ids.split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                val = int(part)
                if not (1 <= val <= 246):
                    errors[CONF_AC_CHARGER_SLAVE_IDS] = "Each ID must be between 1 and 246."
                    break
                ac_id_list.append(val)
            else:
                errors[CONF_AC_CHARGER_SLAVE_IDS] = "Invalid integer value."
                break

        # Check for duplicates in AC charger IDs
        if not DEVELOPER_MODE:
            if len(set(ac_id_list)) != len(ac_id_list):
                errors[CONF_AC_CHARGER_SLAVE_IDS] = "Duplicate IDs found."
            
        # Process the DC charger slave IDs
        raw_dc_ids = user_input.get(CONF_DC_CHARGER_SLAVE_IDS, "")
        dc_id_list = []
        
        for part in raw_dc_ids.split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                val = int(part)
                if not (1 <= val <= 246):
                    errors[CONF_DC_CHARGER_SLAVE_IDS] = "Each ID must be between 1 and 246."
                    break
                dc_id_list.append(val)
            else:
                errors[CONF_DC_CHARGER_SLAVE_IDS] = "Invalid integer value."
                break

        # Check for duplicates in DC charger IDs
        if not DEVELOPER_MODE:
            if len(set(dc_id_list)) != len(dc_id_list):
                errors[CONF_DC_CHARGER_SLAVE_IDS] = "Duplicate IDs found."

        # If there are errors, show the form again
        if errors:
            schema = vol.Schema({
                vol.Required(CONF_INVERTER_SLAVE_IDS, default=raw_ids): str,
                vol.Required(CONF_AC_CHARGER_SLAVE_IDS, default=raw_ac_ids): str,
                vol.Required(CONF_DC_CHARGER_SLAVE_IDS, default=raw_dc_ids): str,
            })
            
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=schema,
                errors=errors,
            )

        # Update the configuration entry with the new IDs
        new_data = {**self._data, CONF_INVERTER_SLAVE_IDS: id_list, CONF_AC_CHARGER_SLAVE_IDS: ac_id_list, CONF_DC_CHARGER_SLAVE_IDS: dc_id_list}
        self.hass.config_entries.async_update_entry(
            self.config_entry, data=new_data
        )
        
        return self.async_create_entry(title="", data={})