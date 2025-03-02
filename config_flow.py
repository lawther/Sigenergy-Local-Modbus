"""Config flow for Sigenergy ESS integration."""
# pylint: disable=import-error
# pyright: reportMissingImports=false
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_AC_CHARGER_COUNT,
    CONF_AC_CHARGER_SLAVE_IDS,
    CONF_DC_CHARGER_COUNT,
    CONF_DC_CHARGER_SLAVE_IDS,
    CONF_DEVICE_TYPE,
    CONF_INVERTER_COUNT,
    CONF_INVERTER_SLAVE_IDS,
    CONF_PARENT_DEVICE_ID,
    CONF_PLANT_ID,
    CONF_SLAVE_ID,
    DEFAULT_AC_CHARGER_COUNT,
    DEFAULT_DC_CHARGER_COUNT,
    DEFAULT_INVERTER_COUNT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DEVICE_TYPE_AC_CHARGER,
    DEVICE_TYPE_DC_CHARGER,
    DEVICE_TYPE_INVERTER,
    DEVICE_TYPE_NEW_PLANT,
    DEVICE_TYPE_PLANT,
    DOMAIN,
    STEP_AC_CHARGER_CONFIG,
    STEP_DC_CHARGER_CONFIG,
    STEP_DEVICE_TYPE,
    STEP_INVERTER_CONFIG,
    STEP_PLANT_CONFIG,
    STEP_SELECT_INVERTER,
    STEP_SELECT_PLANT,
    STEP_USER,
)

_LOGGER = logging.getLogger(__name__)

# Schema definitions for each step
STEP_USER_DATA_SCHEMA = vol.Schema({})  # Empty schema for initial step

STEP_DEVICE_TYPE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_TYPE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": DEVICE_TYPE_NEW_PLANT, "label": "New Plant"},
                    {"value": DEVICE_TYPE_INVERTER, "label": "Add Inverter to Plant"},
                    {"value": DEVICE_TYPE_AC_CHARGER, "label": "Add AC Charger to Plant"},
                    {"value": DEVICE_TYPE_DC_CHARGER, "label": "Add DC Charger to Inverter"},
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)

STEP_PLANT_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        # vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_PLANT_ID, default=DEFAULT_SLAVE_ID): int,
        vol.Required(CONF_SLAVE_ID, default=1): int,
        # vol.Required(CONF_INVERTER_COUNT, default=DEFAULT_INVERTER_COUNT): int,
        # vol.Required(CONF_AC_CHARGER_COUNT, default=DEFAULT_AC_CHARGER_COUNT): int,
    }
)

STEP_AC_CHARGER_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="AC Charger"): str,
        vol.Required(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
    }
)

STEP_DC_CHARGER_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="DC Charger"): str,
        vol.Required(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
    }
)


class SigenergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sigenergy ESS."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data = {}
        self._plants = {}
        self._inverters = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # Initialize data if needed
        if user_input is None:
            # Clear existing data
            self._plants = {}

            # Load plants from config entries
            await self._async_load_plants()
            _LOGGER.debug("Plants after loading: %s", self._plants)
            has_plants = len(self._plants) > 0
            _LOGGER.debug("Has plants: %s", has_plants)

            # If no plants exist, go directly to plant configuration
            if not has_plants:
                self._data[CONF_DEVICE_TYPE] = DEVICE_TYPE_NEW_PLANT
                return await self.async_step_plant_config()

            # Show device type selection if plants exist
            return self.async_show_form(
                step_id=STEP_DEVICE_TYPE,
                data_schema=STEP_DEVICE_TYPE_SCHEMA,
            )

        # Store any user input (this will be empty for the initial step with our new flow)
        self._data.update(user_input)

        # Clear existing data
        self._plants = {}

        # Load plants from config entries
        await self._async_load_plants()
        has_plants = len(self._plants) > 0

        # If no plants exist, go directly to plant configuration
        if not has_plants:
            self._data[CONF_DEVICE_TYPE] = DEVICE_TYPE_NEW_PLANT
            return await self.async_step_plant_config()

        # Show device type selection if plants exist
        return self.async_show_form(
            step_id=STEP_DEVICE_TYPE,
            data_schema=STEP_DEVICE_TYPE_SCHEMA,
        )

    async def async_step_device_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device type selection."""
        errors = {}

        # Check if any plants exist in the system
        await self._async_load_plants()
        has_plants = len(self._plants) > 0

        if user_input is None:
            return self.async_show_form(
                step_id=STEP_DEVICE_TYPE,
                data_schema=STEP_DEVICE_TYPE_SCHEMA,
                errors=errors
            )

        device_type = user_input[CONF_DEVICE_TYPE]
        self._data[CONF_DEVICE_TYPE] = device_type

        # If no plants exist and user selected something other than new plant,
        # override and force new plant creation first
        if not has_plants and device_type != DEVICE_TYPE_NEW_PLANT:
            self._data[CONF_DEVICE_TYPE] = DEVICE_TYPE_NEW_PLANT
            return await self.async_step_plant_config()

        # Route to appropriate next step based on device type
        if device_type == DEVICE_TYPE_NEW_PLANT:
            return await self.async_step_plant_config()
        elif device_type == DEVICE_TYPE_INVERTER:
            # Go directly to inverter config (which now includes plant selection)
            return await self.async_step_inverter_config()
        elif device_type == DEVICE_TYPE_AC_CHARGER:
            if len(self._plants) > 1:
                return await self.async_step_select_plant()
            elif len(self._plants) == 1:
                # Auto-connect to the only plant
                plant_id = list(self._plants.keys())[0]
                self._data[CONF_PARENT_DEVICE_ID] = plant_id
                return await self.async_step_ac_charger_config()
        elif device_type == DEVICE_TYPE_DC_CHARGER:
            # Load inverters
            await self._async_load_inverters()
            if len(self._inverters) > 1:
                return await self.async_step_select_inverter()
            elif len(self._inverters) == 1:
                # Auto-connect to the only inverter
                inverter_id = list(self._inverters.keys())[0]
                self._data[CONF_PARENT_DEVICE_ID] = inverter_id
                return await self.async_step_dc_charger_config()
            else:
                errors["base"] = "no_inverters"
                return self.async_show_form(
                    step_id=STEP_DEVICE_TYPE,
                    data_schema=STEP_DEVICE_TYPE_SCHEMA,
                    errors=errors
                )

    async def async_step_plant_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle plant configuration."""
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_PLANT_CONFIG,
                data_schema=STEP_PLANT_CONFIG_SCHEMA
            )

        # Store plant configuration
        self._data.update(user_input)

        # Check if any plants exist in the system
        await self._async_load_plants()
        plant_no = len(self._plants)

        # vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        self._data[CONF_NAME] = f"Sigen{"" if plant_no == 0 else f" {plant_no}"}"
        self._data[CONF_INVERTER_SLAVE_IDS] = [user_input[CONF_SLAVE_ID]]

        # Create the configuration entry with the default name
        return self.async_create_entry(title=DEFAULT_NAME +
                                       "" if plant_no == 0 
                                       else f" {plant_no}", data=self._data)

    async def async_step_inverter_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle inverter configuration."""
        errors = {}

        if user_input is None:
            # Find the next available slave ID after existing inverters to suggest as default
            existing_slave_ids = []
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data.get(CONF_DEVICE_TYPE) in [DEVICE_TYPE_PLANT, DEVICE_TYPE_NEW_PLANT]:
                    existing_slave_ids.extend(entry.data.get(CONF_INVERTER_SLAVE_IDS, []))
                elif entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_INVERTER:
                    existing_slave_ids.append(entry.data.get(CONF_SLAVE_ID, 0))

            # Start from the highest existing slave ID + 1
            next_slave_id = max(existing_slave_ids, default=0) + 1

            # Load plants for selection
            await self._async_load_plants()

            # Create dynamic schema with plants dropdown and other fields
            schema = vol.Schema({
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
            
            return self.async_show_form(
                step_id=STEP_INVERTER_CONFIG,
                data_schema=schema,
                errors=errors
            )

        # Store inverter configuration
        self._data.update(user_input)

        self._data[CONF_NAME] = "Inverter"  # Default name
        # Store the slave ID in the inverter_slave_ids list as well (for compatibility)
        self._data[CONF_INVERTER_SLAVE_IDS] = [user_input[CONF_SLAVE_ID]]
        self._data[CONF_INVERTER_COUNT] = 1  # Always 1 inverter
        self._data[CONF_AC_CHARGER_COUNT] = DEFAULT_AC_CHARGER_COUNT
        self._data[CONF_AC_CHARGER_SLAVE_IDS] = []
        self._data[CONF_DC_CHARGER_COUNT] = DEFAULT_DC_CHARGER_COUNT
        self._data[CONF_DC_CHARGER_SLAVE_IDS] = []

        # Get plant configuration for the inverter
        parent_id = user_input[CONF_PARENT_DEVICE_ID]
        _LOGGER.debug("Selected plant ID for inverter configuration: %s", parent_id)
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.entry_id == parent_id:
                # Copy network configuration from parent plant
                self._data[CONF_HOST] = entry.data.get(CONF_HOST)
                self._data[CONF_PORT] = entry.data.get(CONF_PORT)

                # THIS IS THE IMPORTANT ADDITION
                # Store the plant's modbus ID - crucial for association
                self._data[CONF_PLANT_ID] = entry.data.get(CONF_PLANT_ID)
                _LOGGER.debug("Associated inverter with plant modbus ID: %s", self._data[CONF_PLANT_ID])

                # Also, mark the device type as specific to child inverters
                self._data[CONF_DEVICE_TYPE] = DEVICE_TYPE_INVERTER
                break

        # Create the configuration entry
        return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

    async def async_step_ac_charger_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle AC charger configuration."""
        if user_input is None:
            # Find the next available slave ID after existing AC chargers to suggest as default
            existing_slave_ids = []
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data.get(CONF_DEVICE_TYPE) in [DEVICE_TYPE_PLANT, DEVICE_TYPE_NEW_PLANT]:
                    existing_slave_ids.extend(entry.data.get(CONF_AC_CHARGER_SLAVE_IDS, []))
                elif entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_AC_CHARGER:
                    existing_slave_ids.append(entry.data.get(CONF_SLAVE_ID, 0))
            
            # Start from the highest existing slave ID + 1
            next_slave_id = max(existing_slave_ids, default=0) + 1
            
            # Create a schema with the suggested slave ID
            schema = STEP_AC_CHARGER_CONFIG_SCHEMA.extend({
                vol.Required(CONF_SLAVE_ID, default=next_slave_id): int,
            })
            
            return self.async_show_form(
                step_id=STEP_AC_CHARGER_CONFIG,
                data_schema=schema
            )

        # Store AC charger configuration
        self._data.update(user_input)
        
        # Store the slave ID in the ac_charger_slave_ids list as well (for compatibility)
        self._data[CONF_AC_CHARGER_SLAVE_IDS] = [user_input[CONF_SLAVE_ID]]
        self._data[CONF_AC_CHARGER_COUNT] = 1  # Always 1 AC charger
        self._data[CONF_INVERTER_COUNT] = DEFAULT_INVERTER_COUNT
        self._data[CONF_INVERTER_SLAVE_IDS] = []
        self._data[CONF_DC_CHARGER_COUNT] = DEFAULT_DC_CHARGER_COUNT
        self._data[CONF_DC_CHARGER_SLAVE_IDS] = []
        
        # Create the configuration entry
        return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

    async def async_step_dc_charger_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle DC charger configuration."""
        if user_input is None:
            # Find the next available slave ID after existing DC chargers to suggest as default
            existing_slave_ids = []
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data.get(CONF_DEVICE_TYPE) in [DEVICE_TYPE_PLANT, DEVICE_TYPE_NEW_PLANT]:
                    existing_slave_ids.extend(entry.data.get(CONF_DC_CHARGER_SLAVE_IDS, []))
                elif entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_DC_CHARGER:
                    existing_slave_ids.append(entry.data.get(CONF_SLAVE_ID, 0))

            # Start from the highest existing slave ID + 1
            next_slave_id = max(existing_slave_ids, default=0) + 1

            # Create a schema with the suggested slave ID
            schema = STEP_DC_CHARGER_CONFIG_SCHEMA.extend({
                vol.Required(CONF_SLAVE_ID, default=next_slave_id): int,
            })

            return self.async_show_form(
                step_id=STEP_DC_CHARGER_CONFIG,
                data_schema=schema
            )

        # Store DC charger configuration
        self._data.update(user_input)

        # Store the slave ID in the dc_charger_slave_ids list as well (for compatibility)
        self._data[CONF_DC_CHARGER_SLAVE_IDS] = [user_input[CONF_SLAVE_ID]]
        self._data[CONF_DC_CHARGER_COUNT] = 1  # Always 1 DC charger
        self._data[CONF_INVERTER_COUNT] = DEFAULT_INVERTER_COUNT
        self._data[CONF_INVERTER_SLAVE_IDS] = []
        self._data[CONF_AC_CHARGER_COUNT] = DEFAULT_AC_CHARGER_COUNT
        self._data[CONF_AC_CHARGER_SLAVE_IDS] = []

        # Create the configuration entry
        return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

    async def async_step_select_plant(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle plant selection."""
        if user_input is None:
            # Create a schema with a dropdown of available plants
            plants_schema = vol.Schema(
                {
                    vol.Required(CONF_PARENT_DEVICE_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": plant_id, "label": plant_name}
                                for plant_id, plant_name in self._plants.items()
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            )
            return self.async_show_form(
                step_id=STEP_SELECT_PLANT,
                data_schema=plants_schema
            )

        # Store the selected plant
        parent_id = user_input[CONF_PARENT_DEVICE_ID]
        self._data[CONF_PARENT_DEVICE_ID] = parent_id
        
        # Fetch the parent plant's info and set defaults based on it
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.entry_id == parent_id:
                plant_name = entry.data.get(CONF_NAME, "Plant")
                self._data[CONF_HOST] = entry.data.get(CONF_HOST)
                self._data[CONF_PORT] = entry.data.get(CONF_PORT)
                # Set default name for child devices
                if self._data[CONF_DEVICE_TYPE] == DEVICE_TYPE_INVERTER:
                    self._data[CONF_NAME] = f"{plant_name} Inverter"
                elif self._data[CONF_DEVICE_TYPE] == DEVICE_TYPE_AC_CHARGER:
                    self._data[CONF_NAME] = f"{plant_name} AC Charger"
                break
        
        # Route to appropriate next step based on device type
        if self._data[CONF_DEVICE_TYPE] == DEVICE_TYPE_INVERTER:
            return await self.async_step_inverter_config()
        elif self._data[CONF_DEVICE_TYPE] == DEVICE_TYPE_AC_CHARGER:
            return await self.async_step_ac_charger_config()

    async def async_step_select_inverter(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle inverter selection."""
        if user_input is None:
            # Create a schema with a dropdown of available inverters
            inverters_schema = vol.Schema(
                {
                    vol.Required(CONF_PARENT_DEVICE_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": inverter_id, "label": inverter_name}
                                for inverter_id, inverter_name in self._inverters.items()
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            )
            return self.async_show_form(
                step_id=STEP_SELECT_INVERTER,
                data_schema=inverters_schema
            )

        # Store the selected inverter
        parent_id = user_input[CONF_PARENT_DEVICE_ID]
        self._data[CONF_PARENT_DEVICE_ID] = parent_id
        
        # Fetch the parent inverter's info and set defaults based on it
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.entry_id == parent_id:
                inverter_name = entry.data.get(CONF_NAME, "Inverter")
                # Set default name for DC chargers
                self._data[CONF_NAME] = f"{inverter_name} DC Charger"
                break
        
        # Proceed to DC charger configuration
        return await self.async_step_dc_charger_config()

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
                        
            if entry.data.get(CONF_DEVICE_TYPE) in [DEVICE_TYPE_PLANT, DEVICE_TYPE_NEW_PLANT]:
                self._plants[entry.entry_id] = entry.data.get(CONF_NAME, f"Plant {entry.entry_id}")
                
        # Log the plants that were found
        _LOGGER.debug("Found plants: %s", self._plants)

    async def _async_load_inverters(self) -> None:
        """Load existing inverters from config entries."""
        self._inverters = {}
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_INVERTER:
                self._inverters[entry.entry_id] = entry.data.get(CONF_NAME, f"Inverter {entry.entry_id}")