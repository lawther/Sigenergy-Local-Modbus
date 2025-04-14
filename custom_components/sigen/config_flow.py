"""Config flow for Sigenergy ESS integration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import re
import voluptuous as vol
import logging

from homeassistant import (
    config_entries,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.config_entries import (  # pylint: disable=syntax-error
    ConfigFlowResult,
)
from homeassistant.helpers.device_registry import (
    async_get as async_get_device_registry,
    async_entries_for_config_entry,  # Import the helper function
)
from homeassistant.helpers.entity_registry import (
    async_get as async_get_entity_registry,
    async_entries_for_device,
)
from .const import (
    CONF_AC_CHARGER_CONNECTIONS,
    CONF_DC_CHARGER_CONNECTIONS,
    CONF_DEVICE_TYPE,
    CONF_INVERTER_SLAVE_ID,
    CONF_INVERTER_CONNECTIONS,
    CONF_PARENT_INVERTER_ID,
    CONF_PARENT_PLANT_ID,
    CONF_SLAVE_ID,
    CONF_SCAN_INTERVAL,  # Added
    DEFAULT_PORT,
    DEFAULT_PLANT_SLAVE_ID,
    DEFAULT_INVERTER_SLAVE_ID,
    DEFAULT_SCAN_INTERVAL,  # Added
    DEVICE_TYPE_NEW_PLANT,
    DEVICE_TYPE_PLANT,
    DEVICE_TYPE_INVERTER,
    DEVICE_TYPE_AC_CHARGER,
    DEVICE_TYPE_DC_CHARGER,
    DOMAIN,
    STEP_DEVICE_TYPE,
    STEP_PLANT_CONFIG,
    STEP_INVERTER_CONFIG,
    STEP_AC_CHARGER_CONFIG,
    STEP_SELECT_PLANT,
    STEP_SELECT_INVERTER,
    STEP_DHCP_SELECT_PLANT,
    DEFAULT_READ_ONLY,
    CONF_INVERTER_HAS_DCCHARGER,
    DEFAULT_INVERTER_HAS_DCCHARGER,
    CONF_PLANT_CONNECTION,
)

# Define a constant for the ignore action (can also be added to const.py)
ACTION_IGNORE = "ignore"

# Define constants that might not be in the .const module
CONF_READ_ONLY = "read_only"
CONF_REMOVE_DEVICE = "remove_device"

STEP_DC_CHARGER_CONFIG = "dc_charger_config"
STEP_SELECT_DEVICE = "select_device"
STEP_RECONFIGURE = "reconfigure"


_LOGGER = logging.getLogger(__name__)

# Schema definitions for each step
STEP_DEVICE_TYPE_SCHEMA = vol.Schema(
    {
        vol.Required("device_type"): vol.In(
            {
                DEVICE_TYPE_NEW_PLANT: "New Plant",
                DEVICE_TYPE_INVERTER: "Inverter",
                DEVICE_TYPE_AC_CHARGER: "AC Charger",
                DEVICE_TYPE_DC_CHARGER: "DC Charger",
            }
        ),
    }
)

STEP_PLANT_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_INVERTER_SLAVE_ID, default=DEFAULT_INVERTER_SLAVE_ID): int,
        vol.Required(CONF_READ_ONLY, default=DEFAULT_READ_ONLY): bool,
    }
)

STEP_INVERTER_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_SLAVE_ID, default=DEFAULT_INVERTER_SLAVE_ID): int,
    }
)

STEP_AC_CHARGER_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_SLAVE_ID): int,
    }
)


def validate_host_port(host: str, port: int) -> Dict[str, str]:
    """Validate host and port combination.

    Args:
        host: The host address
        port: The port number

    Returns:
        Dictionary of errors, empty if validation passes
    """
    errors = {}

    if host is None or host == "":
        errors["host"] = "invalid_host"

    if not port or not 1 <= port <= 65535:
        errors["port"] = "invalid_port"

    return errors


def validate_slave_id(slave_id: int, field_name: str = CONF_SLAVE_ID) -> Dict[str, str]:
    """Validate a slave ID."""
    errors = {}

    if slave_id is None or not 1 <= slave_id <= 246:
        errors[field_name] = "each_id_must_be_between_1_and_246"

    return errors


def get_highest_device_number(names: List[str]) -> int:
    """Get the highest numbered device from a list of device names.
    This function extracts the numeric part from each device name in the list,
    and returns the highest number found. If no numbers are found in any name,
    or if the list is empty, returns 0.
    Args:
        names: A list of device name strings, potentially containing numbers
    Returns:
        int: The highest device number found, or 0 if no numbered devices exist
    """
    if not names or len(names) < 1:
        return 0

    def extract_number(name):
        if not name:
            return 0
        match = re.search(r"\d+", name)
        return int(match.group()) if match else 0

    name = max(names, key=extract_number, default="")
    match = re.search(r"\d+", name)
    return int(match.group()) if match else 1


@config_entries.HANDLERS.register(DOMAIN)
class SigenergyConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for Sigenergy ESS."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data = {}
        self._plants = {}
        self._inverters = {}
        self._devices = {}
        self._selected_plant_entry_id = None
        self._discovered_ip = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step when adding a new device."""
        _LOGGER.debug("Starting config initiated by user.")
        # Load existing plants
        await self._async_load_plants()

        # If no plants exist, go directly to plant configuration
        if not self._plants:
            self._data[CONF_DEVICE_TYPE] = DEVICE_TYPE_NEW_PLANT
            return await self.async_step_plant_config()

        # Otherwise, show device type selection
        return await self.async_step_device_type()

    async def async_step_dhcp(self, discovery_info) -> ConfigFlowResult:
        """Handle DHCP discovery."""

        # Store the discovered IP
        self._discovered_ip = discovery_info.ip
        _LOGGER.debug("Starting config for DHCP discovered with ip: %s", self._discovered_ip)

        # Set unique ID based on discovery info to allow ignoring/updates
        unique_id = f"dhcp_{self._discovered_ip}"
        await self.async_set_unique_id(unique_id)
        # Abort if this discovery (IP) is already configured OR ignored
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._discovered_ip})

        # Check if this IP is already configured in any *active* config entry
        # This prevents offering configuration for an already integrated device part
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.source == config_entries.SOURCE_IGNORE:
                continue # Skip ignored entries

            # Check Plant connection
            plant_conn = entry.data.get(CONF_PLANT_CONNECTION, {})
            if plant_conn.get(CONF_HOST) == self._discovered_ip:
                _LOGGER.info(
                    "DHCP discovered IP %s matches existing plant %s. Aborting.",
                    self._discovered_ip, entry.title
                )
                return self.async_abort(reason="already_configured_device") # Use generic reason

            # Check Inverter connections
            inverter_conns = entry.data.get(CONF_INVERTER_CONNECTIONS, {})
            for inv_name, inv_details in inverter_conns.items():
                if inv_details.get(CONF_HOST) == self._discovered_ip:
                    _LOGGER.info(
                        "DHCP discovered IP %s matches existing inverter %s in plant %s. Aborting.",
                        self._discovered_ip, inv_name, entry.title
                    )
                    return self.async_abort(reason="already_configured_device") # Use generic reason

            # Check AC Charger connections
            ac_charger_conns = entry.data.get(CONF_AC_CHARGER_CONNECTIONS, {})
            for ac_name, ac_details in ac_charger_conns.items():
                if ac_details.get(CONF_HOST) == self._discovered_ip:
                    _LOGGER.info(
                        "DHCP discovered IP %s matches existing AC charger %s in plant %s. Aborting.",
                        self._discovered_ip, ac_name, entry.title
                    )
                    return self.async_abort(reason="already_configured_device") # Use generic reason

        await self._async_load_plants()
        _LOGGER.debug("Loaded plants: %s", self._plants)

        # If no plants exist, configure as new plant (DHCP implies it might be the primary inverter)
        if not self._plants:
            self._data[CONF_DEVICE_TYPE] = DEVICE_TYPE_NEW_PLANT
            # Unique ID for the discovery was set above.
            return await self.async_step_plant_config()

        # Otherwise, let user choose configuration type or ignore
        return await self.async_step_dhcp_select_plant()

    async def async_step_dhcp_select_plant(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle selection between new plant or adding to existing plant."""
        if user_input is None:
            options = {
                DEVICE_TYPE_NEW_PLANT: "Configure as New Plant",
                DEVICE_TYPE_INVERTER: "Add as Inverter to Existing Plant",
                ACTION_IGNORE: "Ignore this device",  # Add ignore option
            }
            return self.async_show_form(
                step_id=STEP_DHCP_SELECT_PLANT,
                data_schema=vol.Schema({
                    # Changed key to 'action' to reflect broader choices
                    vol.Required("action"): vol.In(options)
                }),
                description_placeholders={"ip_address": self._discovered_ip or "unknown"},
                # last_step=False # Indicate this isn't necessarily the final step
            )

        # Use 'action' key instead of 'device_type'
        selected_action = user_input["action"]

        # Handle ignore action
        if selected_action == ACTION_IGNORE:
            _LOGGER.info("User chose to ignore discovered device at %s", self._discovered_ip)
            # Unique ID was already set in async_step_dhcp.
            # Aborting with ignored_device tells HA this discovery is ignored.
            # No need to create an entry with SOURCE_IGNORE manually here.
            return self.async_abort(reason="ignored_device")

        # Existing logic for new plant or adding inverter
        self._data[CONF_DEVICE_TYPE] = selected_action # Store the selected device type

        if selected_action == DEVICE_TYPE_NEW_PLANT:
            # Unique ID for the discovery was set in async_step_dhcp.
            # We might need a different unique ID if creating a full plant entry.
            # Let's reset it here to be specific to the plant being created.
            await self.async_set_unique_id(f"plant_{self._discovered_ip}", raise_on_progress=False)
            self._abort_if_unique_id_configured(updates={CONF_HOST: self._discovered_ip})
            return await self.async_step_plant_config()
        # Assuming DEVICE_TYPE_INVERTER is the only other non-ignore option here
        else: # DEVICE_TYPE_INVERTER
            # Ensure plants are loaded if we jump directly here via DHCP with existing plants
            if not self._plants:
                await self._async_load_plants()
            # No unique ID needed here as we are adding to an existing plant entry
            return await self.async_step_select_plant()

    async def async_step_device_type(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the device type selection when adding a new device."""
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_DEVICE_TYPE,
                data_schema=STEP_DEVICE_TYPE_SCHEMA,
            )

        device_type = user_input["device_type"]
        self._data[CONF_DEVICE_TYPE] = device_type

        if device_type == DEVICE_TYPE_NEW_PLANT:
            return await self.async_step_plant_config()
        elif device_type in [
            DEVICE_TYPE_INVERTER,
            DEVICE_TYPE_AC_CHARGER,
            DEVICE_TYPE_DC_CHARGER,
        ]:
            return await self.async_step_select_plant()

        # Should never reach here
        return self.async_abort(reason="unknown_device_type")

    async def async_step_plant_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the plant configuration step when adding a new plant device."""
        errors = {}

        if self._discovered_ip:
            # Test connecting trough Modbus to ip with DEFAULT_PORT and DEFAULT_INVERTER_SLAVE_ID
            connection_succeded = False
            if connection_succeded:
                user_input = {
                    CONF_HOST: self._discovered_ip,
                    CONF_PORT: DEFAULT_PORT,
                    CONF_INVERTER_SLAVE_ID: DEFAULT_INVERTER_SLAVE_ID,
                    CONF_READ_ONLY: DEFAULT_READ_ONLY
                }

        if user_input is None:
            # Dynamically create schema to pre-fill host if discovered via DHCP
            schema = vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._discovered_ip or ""): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_INVERTER_SLAVE_ID, default=DEFAULT_INVERTER_SLAVE_ID): int,
                    vol.Required(CONF_READ_ONLY, default=DEFAULT_READ_ONLY): bool,
                }
            )
            return self.async_show_form(
                step_id=STEP_PLANT_CONFIG,
                data_schema=schema,
            )

        # Process and validate inverter ID
        try:
            inverter_id = int(user_input[CONF_INVERTER_SLAVE_ID])
            if not 1 <= inverter_id <= 246:
                errors[CONF_INVERTER_SLAVE_ID] = "each_id_must_be_between_1_and_246"
        except (ValueError, TypeError):
            errors[CONF_INVERTER_SLAVE_ID] = "invalid_integer_value"

        if errors:
            return self.async_show_form(
                step_id=STEP_PLANT_CONFIG,
                data_schema=STEP_PLANT_CONFIG_SCHEMA,
                errors=errors,
            )

        # Create the plant connection dictionary
        self._data[CONF_PLANT_CONNECTION] = {
            CONF_HOST: user_input[CONF_HOST],
            CONF_PORT: user_input[CONF_PORT],
            CONF_SLAVE_ID: DEFAULT_PLANT_SLAVE_ID,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        }

        # Create the inverter connections dictionary for the implicit first inverter
        inverter_name = "Sigen Inverter"
        self._data[CONF_INVERTER_CONNECTIONS] = {
            inverter_name: {
                CONF_HOST: self._data[CONF_PLANT_CONNECTION][CONF_HOST],
                CONF_PORT: self._data[CONF_PLANT_CONNECTION][CONF_PORT],
                CONF_SLAVE_ID: inverter_id,
                CONF_INVERTER_HAS_DCCHARGER: DEFAULT_INVERTER_HAS_DCCHARGER,
            }
        }

        # Store the plant name generated based on the number of installed plants
        plant_no = get_highest_device_number(list(self._plants.keys()))

        self._data[CONF_NAME] = (
            f"Sigen Plant{'' if plant_no == 0 else f' {plant_no + 1}'}"
        )

        # Set the device type as plant
        self._data[CONF_DEVICE_TYPE] = DEVICE_TYPE_PLANT

        # Set default scan interval silently
        self._data[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL

        # Create the configuration entry with the default name
        return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

    async def async_step_select_plant(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the plant selection step when adding a new child device."""
        if not self._plants:
            # No plants available, abort with error
            return self.async_abort(reason="no_plants_available")

        if user_input is None:
            # Create schema with plant selection
            schema = vol.Schema(
                {vol.Required(CONF_PARENT_PLANT_ID): vol.In(self._plants)}
            )

            return self.async_show_form(
                step_id=STEP_SELECT_PLANT,
                data_schema=schema,
            )

        # Store the selected plant ID
        self._selected_plant_entry_id = user_input[CONF_PARENT_PLANT_ID]
        self._data[CONF_PARENT_PLANT_ID] = self._selected_plant_entry_id

        # Proceed based on the device type
        device_type = self._data.get(CONF_DEVICE_TYPE)

        if device_type == DEVICE_TYPE_INVERTER:
            return await self.async_step_inverter_config()
        elif device_type == DEVICE_TYPE_AC_CHARGER:
            return await self.async_step_ac_charger_config()
        elif device_type == DEVICE_TYPE_DC_CHARGER:
            # For DC Charger, we need to load inverters from the selected plant
            await self._async_load_inverters(self._selected_plant_entry_id)
            return await self.async_step_select_inverter()

        # Should never reach here
        return self.async_abort(reason="unknown_device_type")

    async def async_step_inverter_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the inverter configuration step when adding a new inverter device."""
        if user_input is None:
            # Dynamically create schema to pre-fill host if discovered via DHCP
            schema = vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._discovered_ip or ""): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_SLAVE_ID, default=DEFAULT_INVERTER_SLAVE_ID): int,
                }
            )
            return self.async_show_form(
                step_id=STEP_INVERTER_CONFIG,
                data_schema=schema,
            )

        # Check for duplicate IDs
        assert self._selected_plant_entry_id is not None  # Ensure ID is set before use
        plant_entry = self.hass.config_entries.async_get_entry(
            self._selected_plant_entry_id
        )
        if plant_entry:
            _LOGGER.debug("Selected plant entry ID: %s", self._selected_plant_entry_id)
            _LOGGER.debug("Plant entry data: %s", plant_entry.data)
            # Check against existing inverter slave IDs in the connections dictionary
            inverter_connections = plant_entry.data.get(CONF_INVERTER_CONNECTIONS, {})
            _LOGGER.debug("Existing inverter connections: %s", inverter_connections)

            # Get the inverter name based on number of existing inverters
            inverter_no = get_highest_device_number(list(inverter_connections.keys()))
            inverter_name = (
                f"Sigen Inverter{'' if inverter_no == 0 else f' {inverter_no + 1}'}"
            )
            _LOGGER.debug("InverterName generated: %s", inverter_name)

            # Create the new connection
            new_inverter_connection = {
                CONF_HOST: user_input[CONF_HOST],
                CONF_PORT: user_input[CONF_PORT],
                CONF_SLAVE_ID: user_input[CONF_SLAVE_ID],
                CONF_INVERTER_HAS_DCCHARGER: DEFAULT_INVERTER_HAS_DCCHARGER,
            }

            # Create or update the inverter connections dictionary
            new_data = dict(plant_entry.data)
            inverter_connections[inverter_name] = new_inverter_connection
            _LOGGER.debug("Updated inverter connections: %s", inverter_connections)

            # Update the plant's configuration with the new inverter
            new_data[CONF_INVERTER_CONNECTIONS] = inverter_connections
            _LOGGER.debug("New data for plant entry: %s", new_data)

            # Update the plant's configuration with the new inverter
            self.hass.config_entries.async_update_entry(plant_entry, data=new_data)
            self.hass.config_entries._async_schedule_save()
            # Reload the entry to ensure changes take effect
            await self.hass.config_entries.async_reload(plant_entry.entry_id)

            return self.async_abort(reason="device_added")

        return self.async_abort(reason="parent_plant_not_found")

    async def async_step_ac_charger_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the AC charger configuration step when adding a new AC charger device."""
        errors = {}

        def get_schema(data_source: Dict):
            return vol.Schema({
                vol.Required(CONF_HOST, default=data_source.get(CONF_HOST, "")): str,
                vol.Required(CONF_PORT, default=data_source.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Required(CONF_SLAVE_ID, default=data_source.get(CONF_SLAVE_ID, DEFAULT_INVERTER_SLAVE_ID)): int,
                })

        if user_input is None:
            return self.async_show_form(
                step_id=STEP_AC_CHARGER_CONFIG,
                data_schema=get_schema({}),
            )

        # Validate the slave ID
        slave_id = user_input.get(CONF_SLAVE_ID)
        if slave_id is None or not 1 <= slave_id <= 246:
            errors[CONF_SLAVE_ID] = "each_id_must_be_between_1_and_246"
            return self.async_show_form(
                step_id=STEP_AC_CHARGER_CONFIG,
                data_schema=get_schema(user_input),
                errors=errors,
            )

        # Check for duplicate IDs and conflicts with inverters
        assert self._selected_plant_entry_id is not None  # Ensure ID is set before use
        plant_entry = self.hass.config_entries.async_get_entry(
            self._selected_plant_entry_id
        )
        if plant_entry:
            # Get existing AC charger connections dictionary
            ac_charger_connections = plant_entry.data.get(
                CONF_AC_CHARGER_CONNECTIONS, {}
            )

            if errors:
                return self.async_show_form(
                    step_id=STEP_AC_CHARGER_CONFIG,
                    data_schema=get_schema(user_input),
                    errors=errors,
                )

            # Get the AC charger name based on number of existing AC chargers
            ac_charger_no = get_highest_device_number(
                list(ac_charger_connections.keys())
            )

            # Get the number if any from the last ac_charger if any.
            ac_charger_name = (
                f"Sigen AC Charger{'' if ac_charger_no == 0 else f' {ac_charger_no + 1}'}"
            )

            # Create or update the AC charger connections dictionary
            new_data = dict(plant_entry.data)
            ac_charger_connections = new_data.get(CONF_AC_CHARGER_CONNECTIONS, {})
            ac_charger_connections[ac_charger_name] = {
                CONF_HOST: user_input[CONF_HOST],
                CONF_PORT: user_input[CONF_PORT],
                CONF_SLAVE_ID: slave_id,
            }

            # Update the plant's configuration with the new AC charger
            new_data[CONF_AC_CHARGER_CONNECTIONS] = ac_charger_connections

            self.hass.config_entries.async_update_entry(plant_entry, data=new_data)

            # Save configuration to file
            self.hass.config_entries._async_schedule_save()

            # Reload the entry to ensure changes take effect
            await self.hass.config_entries.async_reload(plant_entry.entry_id)

            return self.async_abort(reason="device_added")

        return self.async_abort(reason="parent_plant_not_found")

    async def async_step_select_inverter(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the inverter selection step when adding a new DC charger device."""

        # Get the plant data
        assert self._selected_plant_entry_id is not None  # Ensure ID is set before use
        plant_entry = self.hass.config_entries.async_get_entry(
            self._selected_plant_entry_id
        )
        if not plant_entry:
            return self.async_abort(reason="parent_plant_not_found")

        # Get the inverter connections without a DC Charger
        inverter_connections_without_dc = {
            name: details
            for name, details in plant_entry.data.get(
                CONF_INVERTER_CONNECTIONS, {}
            ).items()
            if not details.get(CONF_INVERTER_HAS_DCCHARGER, False)
        }
        _LOGGER.debug("Inverter connections: %s", inverter_connections_without_dc)

        inverters_without_dc = self._get_inverters_to_display(
            inverter_connections_without_dc
        )

        if not inverters_without_dc:
            # No inverters available, abort with error
            return self.async_abort(reason="no_inverters_available")

        if user_input is None:
            # Create schema with inverter selection
            schema = vol.Schema(
                {vol.Required(CONF_PARENT_INVERTER_ID): vol.In(inverters_without_dc)}
            )

            return self.async_show_form(
                step_id=STEP_SELECT_INVERTER,
                data_schema=schema,
            )

        # Get the selected inverter connection details
        selected_inverter = user_input[CONF_PARENT_INVERTER_ID]
        _LOGGER.debug("Selected inverter: %s", selected_inverter)

        selected_inverter_name = selected_inverter.split(" (Host:")[0]
        inverter_details = inverter_connections_without_dc[selected_inverter_name]
        inverter_name = selected_inverter_name
        _LOGGER.debug(
            "Selected inverter: %s, details: %s", inverter_name, inverter_details
        )

        # Create the new connection
        new_inverter_connection = {
            CONF_HOST: inverter_details[CONF_HOST],
            CONF_PORT: inverter_details[CONF_PORT],
            CONF_SLAVE_ID: inverter_details[CONF_SLAVE_ID],
            CONF_INVERTER_HAS_DCCHARGER: True,
        }

        # Create or update the inverter connections dictionary
        new_data = dict(plant_entry.data)
        inverter_connections = new_data.get(CONF_INVERTER_CONNECTIONS, {})
        inverter_connections[inverter_name] = new_inverter_connection
        _LOGGER.debug("Updated inverter connections: %s", inverter_connections)

        # Update the plant's configuration with the new inverter
        new_data[CONF_INVERTER_CONNECTIONS] = inverter_connections
        _LOGGER.debug("New data for plant entry: %s", new_data)

        # Update the plant's configuration with the new inverter
        self.hass.config_entries.async_update_entry(plant_entry, data=new_data)
        self.hass.config_entries._async_schedule_save()
        # Reload the entry to ensure changes take effect
        await self.hass.config_entries.async_reload(plant_entry.entry_id)

        return self.async_abort(reason="device_added")

    async def _async_load_plants(self) -> None:
        """Load existing plants from config entries when adding a new device."""
        self._plants = {}

        # Log the number of config entries for debugging
        _LOGGER.debug(
            "Total config entries: %s",
            len(self.hass.config_entries.async_entries(DOMAIN)),
        )

        for entry in self.hass.config_entries.async_entries(DOMAIN):
            # Log each entry to see what's being found
            _LOGGER.debug(
                "Found entry: %s, device type: %s",
                entry.entry_id,
                entry.data.get(CONF_DEVICE_TYPE),
            )

            if entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_PLANT:
                self._plants[entry.entry_id] = entry.data.get(
                    CONF_NAME, f"Plant {entry.entry_id}"
                )

        # Log the plants that were found
        _LOGGER.debug("Found plants: %s", self._plants)

    async def _async_load_inverters(self, plant_entry_id: str) -> None:
        """Load existing inverters for a specific plant when adding a new DC charger device."""
        self._inverters = {}

        plant_entry = self.hass.config_entries.async_get_entry(plant_entry_id)
        if not plant_entry:
            _LOGGER.error(
                "SigenergyConfigFlow.async_load_inverters: No plant entry found for ID: %s",
                plant_entry_id,
            )
            return
        plant_data = dict(plant_entry.data)
        inverter_connections = plant_data.get(CONF_INVERTER_CONNECTIONS, {})
        _LOGGER.debug("Inverter connections: %s", inverter_connections)

        self._inverters = self._get_inverters_to_display(inverter_connections)
        _LOGGER.debug(
            "Found inverters for plant %s: %s", plant_entry_id, self._inverters
        )

    def _get_inverters_to_display(
        self,
        inverter_connections: Dict[str, Dict],
        with_dc: Optional[bool] = True,
        without_dc: Optional[bool] = True,
    ) -> List[str]:
        """Retrieve inverters for a specific plant."""

        inverters = []

        for inv_name, inv_details in inverter_connections.items():
            has_dc = inv_details.get(CONF_DC_CHARGER_CONNECTIONS, False)
            _LOGGER.debug("Processing inverter: %s, has DC: %s", inv_name, has_dc)
            if not without_dc and not has_dc:
                continue
            if not with_dc and has_dc:
                continue
            display_name = f"{inv_name} (Host: {inv_details.get(CONF_HOST)}, ID: {inv_details.get(CONF_SLAVE_ID)})"
            inverters.append(
                display_name
            )  # Changed from inverters[i] to inverters.append

        return inverters

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SigenergyOptionsFlowHandler(config_entry)


class SigenergyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Sigenergy options for reconfiguring existing devices."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)
        self._data = dict(config_entry.data)
        self._plants = {}
        self._devices = {}
        self._inverters = {}
        self._devices_loaded = False
        self._selected_device = None
        self._temp_config = {}

    async def _async_load_devices(self) -> None:
        """Load all existing devices for reconfiguration selection."""
        self._devices = {}
        device_type = self._data.get(CONF_DEVICE_TYPE)
        _LOGGER.debug("Loading devices for device type: %s", device_type)

        if device_type == DEVICE_TYPE_PLANT:
            # For plants, load all child devices
            plant_entry_id = self.config_entry.entry_id
            plant_name = self._data.get(CONF_NAME, f"Plant {plant_entry_id}")
            plant_host = self._data.get(CONF_PLANT_CONNECTION, {}).get(CONF_HOST, "")

            # Add the plant itself with host info
            self._devices[f"plant_{plant_entry_id}"] = (
                f"{plant_name} (Host: {plant_host})"
            )

            # Add inverters
            inverter_connections = self._data.get(CONF_INVERTER_CONNECTIONS, {})

            # Process inverters
            for inv_name, inv_details in inverter_connections.items():
                device_key = f"inverter_{inv_name}"

                display_name = f"{inv_name} (Host: {inv_details.get(CONF_HOST)}, ID: {inv_details.get(CONF_SLAVE_ID)})"

                self._devices[device_key] = display_name

            # Add AC chargers with host info
            ac_charger_connections = self._data.get(CONF_AC_CHARGER_CONNECTIONS, {})

            for ac_name, ac_details in ac_charger_connections.items():
                device_key = f"ac_{ac_name}"

                display_name = f"{ac_name} (Host: {ac_details.get(CONF_HOST)}, ID: {ac_details.get(CONF_SLAVE_ID)})"

                self._devices[device_key] = display_name

            # Add DC chargers
            for inv_name, inv_details in inverter_connections.items():
                if not inv_details.get(CONF_INVERTER_HAS_DCCHARGER, False):
                    continue

                device_key = f"dc_{inv_name}"
                display_name = f"{inv_name} DC Charger (Host: {inv_details.get(CONF_HOST)}, ID: {inv_details.get(CONF_SLAVE_ID)})"

                self._devices[device_key] = display_name

        self._devices_loaded = True

        _LOGGER.debug("Loaded devices for selection: %s", self._devices)

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Initial handler for device reconfiguration options."""
        device_type = self._data.get(CONF_DEVICE_TYPE)
        _LOGGER.debug("Options flow init for device type: %s", device_type)

        # If this is a plant, load devices and show device selection
        if device_type == DEVICE_TYPE_PLANT and not self._devices_loaded:
            await self._async_load_devices()
            return await self.async_step_select_device()

        # For non-plant devices or if no devices loaded, go to device-specific options
        if device_type == DEVICE_TYPE_PLANT:
            return await self.async_step_plant_config(user_input)
        elif device_type == DEVICE_TYPE_INVERTER:
            return await self.async_step_inverter_config(user_input)
        elif device_type == DEVICE_TYPE_AC_CHARGER:
            return await self.async_step_ac_charger_config(user_input)
        elif device_type == DEVICE_TYPE_DC_CHARGER:
            return await self.async_step_dc_charger_config(user_input)

        # Fallback
        return self.async_abort(reason="unknown_device_type")

    async def async_step_select_device(self, user_input: dict[str, Any] | None = None):
        """Handle selection of which existing device to reconfigure."""
        if not self._devices:
            _LOGGER.debug("No devices available for selection, going to plant config")
            return await self.async_step_plant_config()

        if user_input is None:
            # Create schema with device selection
            schema = vol.Schema(
                {vol.Required("selected_device"): vol.In(self._devices)}
            )

            return self.async_show_form(
                step_id=STEP_SELECT_DEVICE,
                data_schema=schema,
            )

        # Parse the selected device
        _LOGGER.debug("Selected device: %s", user_input["selected_device"])
        selected_device = user_input.get("selected_device", "")
        device_parts = selected_device.split("_", 1)

        if len(device_parts) < 2:
            return self.async_abort(reason="invalid_device_selection")

        device_type = device_parts[0]
        device_id = device_parts[1]

        # Store the selected device info
        self._selected_device = {"type": device_type, "id": device_id}
        _LOGGER.debug("Parsed selected device: %s", self._selected_device)

        # Store the selected device for later use
        self._temp_config["selected_device"] = self._selected_device

        # Route to the appropriate configuration step
        if device_type == "plant":
            return await self.async_step_plant_config()
        elif device_type == "inverter":
            return await self.async_step_inverter_config()
        elif device_type == "ac":
            return await self.async_step_ac_charger_config()
        elif device_type == "dc":
            return await self.async_step_dc_charger_config()

        # Fallback
        return self.async_abort(reason=f"unknown_device_type: {device_type}")

    async def async_step_plant_config(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle reconfiguration of an existing plant device."""
        errors = {}

        def get_schema(data_source: Dict):
            return vol.Schema(
                {
                    vol.Required(CONF_HOST, default=data_source.get(CONF_HOST, "")): str,
                    vol.Required(
                        CONF_PORT, default=data_source.get(CONF_PORT, DEFAULT_PORT)
                    ): int,
                    vol.Required(
                        CONF_READ_ONLY,
                        default=data_source.get(CONF_READ_ONLY, DEFAULT_READ_ONLY),
                    ): bool,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=data_source.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                }
            )

        if user_input is None:
            return self.async_show_form(
                step_id=STEP_PLANT_CONFIG,
                data_schema=get_schema(self._data[CONF_PLANT_CONNECTION])
            )

        # Validate host and port
        host_port_errors = validate_host_port(
            user_input.get(CONF_HOST, ""), user_input.get(CONF_PORT, 0)
        )
        errors.update(host_port_errors)

        # Validate scan interval

        if errors:
            # Re-create schema with user input values for error display
            return self.async_show_form(
                step_id=STEP_PLANT_CONFIG,
                data_schema=get_schema(user_input),
                errors=errors
            )

        # Update the configuration entry data (only host, port, read_only)
        new_data = dict(self._data) # Start with existing data
        new_data[CONF_PLANT_CONNECTION][CONF_HOST] = user_input[CONF_HOST]
        new_data[CONF_PLANT_CONNECTION][CONF_PORT] = user_input[CONF_PORT]
        new_data[CONF_PLANT_CONNECTION][CONF_READ_ONLY] = user_input[CONF_READ_ONLY]
        new_data[CONF_PLANT_CONNECTION][CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]

        # Update data if changed (optional check, keeping existing behavior for now)
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

        # Save configuration to file
        self.hass.config_entries._async_schedule_save()

        # Reload the entry to ensure changes take effect
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)

        return self.async_create_entry(title="Sigenergy", data={})

    async def async_step_inverter_config(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle reconfiguration of an existing inverter device."""
        errors = {}

        # Get the inverter details
        inverter_name = self._selected_device["id"] if self._selected_device else None
        inverter_connections = self._data.get(CONF_INVERTER_CONNECTIONS, {})
        _LOGGER.debug(
            "Inverter name: %s, connections: %s", inverter_name, inverter_connections
        )
        inverter_details = inverter_connections.get(inverter_name, {})

        if user_input is None:
            # Create schema with previously saved values
            schema = vol.Schema(
                {
                    vol.Optional(CONF_REMOVE_DEVICE, default=False): bool,
                    vol.Required(
                        CONF_HOST, default=inverter_details.get(CONF_HOST, "")
                    ): str,
                    vol.Required(
                        CONF_PORT, default=inverter_details.get(CONF_PORT, DEFAULT_PORT)
                    ): int,
                    vol.Required(
                        CONF_SLAVE_ID,
                        default=inverter_details.get(
                            CONF_SLAVE_ID, DEFAULT_INVERTER_SLAVE_ID
                        ),
                    ): int,
                }
            )

            return self.async_show_form(
                step_id=STEP_INVERTER_CONFIG,
                data_schema=schema,
            )

        # Create schema with current values that we can return on errors.
        schema = vol.Schema(
            {
                vol.Optional(CONF_REMOVE_DEVICE, default=False): bool,
                vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
                vol.Required(
                    CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_PORT)
                ): int,
                vol.Required(
                    CONF_SLAVE_ID,
                    default=user_input.get(CONF_SLAVE_ID, DEFAULT_INVERTER_SLAVE_ID),
                ): int,
            }
        )

        # Check if user wants to remove the device
        if user_input.get(CONF_REMOVE_DEVICE, False):
            # Get configuration data to change
            new_data = dict(self._data)

            # Remove from inverter connections
            new_inverter_connections = dict(inverter_connections)
            if inverter_name in new_inverter_connections:
                del new_inverter_connections[inverter_name]

        # Else if we update the info
        else:
            # Validate host, port, and slave ID
            host_port = user_input.get(CONF_PORT, "")
            host_port_errors = validate_host_port(
                host_port, user_input.get(CONF_PORT, 0)
            )
            errors.update(host_port_errors)

            # Validate slave ID
            slave_id = user_input.get(CONF_SLAVE_ID)
            errors.update(validate_slave_id(slave_id or 0) or {})

            if errors:
                return self.async_show_form(
                    step_id=STEP_INVERTER_CONFIG,
                    data_schema=schema,
                    errors=errors,
                )

            # Create the new inverter details
            new_connection = {
                CONF_HOST: user_input.get(CONF_HOST),
                CONF_PORT: host_port,
                CONF_SLAVE_ID: slave_id,
                CONF_INVERTER_HAS_DCCHARGER: inverter_details.get(
                    CONF_INVERTER_HAS_DCCHARGER, False
                ),
            }

            # If the inverter connections have changed
            if new_connection != inverter_details:
                # Update the inverter configuration
                new_inverter_connections = dict(inverter_connections)
                new_inverter_connections[inverter_name] = new_connection

        ### End if

        # Update the configuration entry with the new connections
        new_data = dict(self._data)
        new_data[CONF_INVERTER_CONNECTIONS] = new_inverter_connections

        # Update the configuration entry (Ensure correct arguments and remove duplicate)
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

        # Wipe all old entities and devices
        _LOGGER.debug(
            "Inverter config updated (removed), removing existing devices/entities before reload."
        )
        await self._async_remove_devices_and_entities(inverter_name)

        # Save configuration to file
        self.hass.config_entries._async_schedule_save()

        # Reload the entry to ensure changes take effect
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)

        return self.async_create_entry(title="Sigenergy", data={})

    async def async_step_ac_charger_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing AC charger device."""
        errors = {}

        # Get the AC charger details
        ac_charger_name: Optional[str] = (
            self._selected_device["id"] if self._selected_device else None
        )
        ac_charger_connections = self._data.get(CONF_AC_CHARGER_CONNECTIONS, {})
        ac_charger_details = ac_charger_connections.get(ac_charger_name, {})

        if user_input is None:
            # Create schema with current values
            schema = vol.Schema(
                {
                    vol.Optional(CONF_REMOVE_DEVICE, default=False): bool,
                    vol.Required(
                        CONF_HOST, default=ac_charger_details.get(CONF_HOST, "")
                    ): str,
                    vol.Required(
                        CONF_PORT,
                        default=ac_charger_details.get(CONF_PORT, DEFAULT_PORT),
                    ): int,
                    vol.Required(
                        CONF_SLAVE_ID, default=ac_charger_details.get(CONF_SLAVE_ID, 1)
                    ): int,
                }
            )

            return self.async_show_form(
                step_id=STEP_AC_CHARGER_CONFIG,
                data_schema=schema,
            )

        # Re-create schema with user input values for error display
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_REMOVE_DEVICE,
                    default=user_input.get(CONF_REMOVE_DEVICE, False),
                ): bool,
                vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
                vol.Required(
                    CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_PORT)
                ): int,
                vol.Required(
                    CONF_SLAVE_ID, default=user_input.get(CONF_SLAVE_ID, 1)
                ): int,
            }
        )

        # Check if user wants to remove the device
        if user_input.get(CONF_REMOVE_DEVICE, False):
            # Remove the AC charger
            new_data = dict(self._data)

            # Remove from AC charger connections
            new_ac_charger_connections = dict(ac_charger_connections)
            if ac_charger_name in new_ac_charger_connections:
                del new_ac_charger_connections[ac_charger_name]

        # Else if we update the info
        else:
            # Validate host, port, and slave ID
            host_port = user_input.get(CONF_PORT, "")
            host_port_errors = validate_host_port(
                host_port, user_input.get(CONF_PORT, 0)
            )
            errors.update(host_port_errors)

            # Validate slave ID
            slave_id = user_input.get(CONF_SLAVE_ID)
            errors.update(validate_slave_id(slave_id or 0) or {})

            if errors:
                return self.async_show_form(
                    step_id=STEP_AC_CHARGER_CONFIG,
                    data_schema=schema,
                    errors=errors,
                )

            # Create the new inverter details
            new_connection = {
                CONF_HOST: user_input[CONF_HOST],
                CONF_PORT: user_input[CONF_PORT],
                CONF_SLAVE_ID: slave_id,
            }

            # If the AC Charger connection has changed
            if new_connection != ac_charger_details:
                new_ac_charger_connections = dict(ac_charger_connections)
                new_ac_charger_connections[ac_charger_name] = new_connection

        # Update the AC charger configuration
        new_data = dict(self._data)
        new_data[CONF_AC_CHARGER_CONNECTIONS] = new_ac_charger_connections

        # Update the configuration entry (Ensure correct arguments and remove duplicate)
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

        # Wipe all old entities and devices
        await self._async_remove_devices_and_entities(ac_charger_name)

        # Save configuration to file
        self.hass.config_entries._async_schedule_save()

        # Reload the entry to ensure changes take effect
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)

        return self.async_create_entry(title="Sigenergy", data={})

    async def async_step_dc_charger_config(
        self, user_input: dict[str, Any] | None = None
    ):
        """Handle reconfiguration of an existing DC charger device."""
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Optional(CONF_REMOVE_DEVICE, default=False): bool,
                }
            )

            return self.async_show_form(
                step_id=STEP_DC_CHARGER_CONFIG,
                data_schema=schema,
            )

        if user_input.get(CONF_REMOVE_DEVICE, False):
            plant_entry = self
            inverter_name: str = (
                self._selected_device.get("id", "") if self._selected_device else ""
            )
            inverter_connections = plant_entry._data.get(CONF_INVERTER_CONNECTIONS, {})
            _LOGGER.debug("Inverter connections: %s", inverter_connections)
            inverter_details = inverter_connections[inverter_name]

            new_inverter_connection = {
                CONF_HOST: inverter_details[CONF_HOST],
                CONF_PORT: inverter_details[CONF_PORT],
                CONF_SLAVE_ID: inverter_details[CONF_SLAVE_ID],
                CONF_INVERTER_HAS_DCCHARGER: False,
            }

            # Create or update the inverter connections dictionary
            new_data = dict(plant_entry._data)
            inverter_connections = new_data.get(CONF_INVERTER_CONNECTIONS, {})
            inverter_connections[inverter_name] = new_inverter_connection
            _LOGGER.debug("Updated inverter connections: %s", inverter_connections)

            # Update the plant's configuration with the new inverter
            new_data[CONF_INVERTER_CONNECTIONS] = inverter_connections
            _LOGGER.debug("New data for plant entry: %s", new_data)

            # Update the plant's configuration with the new inverter
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )

            # Wipe all old entities and devices
            _LOGGER.debug(
                "Inverter config updated (removed), removing existing devices/entities before reload."
            )
            await self._async_remove_devices_and_entities(f"{inverter_name} DC Charger")

            # Save configuration to file
            self.hass.config_entries._async_schedule_save()

            # Reload the entry to ensure changes take effect
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title="Sigenergy", data={})

        # Handle non-removal case (no changes, but still cleanup before returning)
        _LOGGER.debug(
            "DC charger config step finished without removal, cleaning up before returning."
        )

        return self.async_create_entry(
            title="", data={}
        )  # Existing return for non-removal

    async def _async_remove_devices_and_entities(
        self, device_name: str | None = None
    ) -> None:
        """Remove all devices and entities associated with this config entry."""
        device_registry = async_get_device_registry(self.hass)
        entity_registry = async_get_entity_registry(self.hass)

        _LOGGER.info(
            "Removing all devices and entities for config entry %s prior to reload",
            self.config_entry.entry_id,
        )
        devices_in_config = async_entries_for_config_entry(
            device_registry, self.config_entry.entry_id
        )

        if not devices_in_config:
            _LOGGER.debug(
                "No devices found for config entry %s to remove.",
                self.config_entry.entry_id,
            )
            return

        _LOGGER.debug("Found total of %d devices.", len(devices_in_config))

        for device_entry in devices_in_config:
            if (
                device_name
                and device_entry.name
                and not device_entry.name.startswith(device_name)
            ):
                continue
            entity_entries = async_entries_for_device(
                entity_registry, device_entry.id, include_disabled_entities=True
            )
            _LOGGER.debug(
                "Found %d entities for device %s (%s, %s) to remove.",
                len(entity_entries),
                device_entry.id,
                device_entry.name_by_user or "",
                device_entry.name or "",
            )
            for entity_entry in entity_entries:
                _LOGGER.debug("Removing entity: %s", entity_entry.entity_id)
                entity_registry.async_remove(entity_entry.entity_id)

            _LOGGER.debug("Removing device: %s", device_entry.id)
            device_registry.async_remove_device(device_entry.id)

        _LOGGER.info(
            "Finished removing devices and entities for config entry %s.",
            self.config_entry.entry_id,
        )
