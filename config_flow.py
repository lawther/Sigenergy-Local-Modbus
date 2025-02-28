"""Config flow for Sigenergy ESS integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_AC_CHARGER_COUNT,
    CONF_AC_CHARGER_SLAVE_IDS,
    CONF_INVERTER_COUNT,
    CONF_INVERTER_SLAVE_IDS,
    CONF_PLANT_ID,
    DEFAULT_AC_CHARGER_COUNT,
    DEFAULT_INVERTER_COUNT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_PLANT_ID, default=DEFAULT_SLAVE_ID): int,
        vol.Required(CONF_INVERTER_COUNT, default=DEFAULT_INVERTER_COUNT): int,
        vol.Required(CONF_AC_CHARGER_COUNT, default=DEFAULT_AC_CHARGER_COUNT): int,
    }
)


class SigenergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sigenergy ESS."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        # Generate inverter slave IDs
        inverter_count = user_input[CONF_INVERTER_COUNT]
        ac_charger_count = user_input[CONF_AC_CHARGER_COUNT]
        
        inverter_slave_ids = list(range(1, inverter_count + 1))
        ac_charger_slave_ids = list(range(inverter_count + 1, inverter_count + ac_charger_count + 1))
        
        user_input[CONF_INVERTER_SLAVE_IDS] = inverter_slave_ids
        user_input[CONF_AC_CHARGER_SLAVE_IDS] = ac_charger_slave_ids
        
        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)