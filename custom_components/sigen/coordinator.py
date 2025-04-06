"""Data update coordinator for Sigenergy ESS."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_SLAVE_ID # Import CONF_SLAVE_ID
from .modbus import SigenergyModbusHub

_LOGGER = logging.getLogger(__name__)


class SigenergyDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Sigenergy ESS."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        hub: SigenergyModbusHub,
        name: str,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.hub = hub
        self.platforms = []

        super().__init__(
            hass,
            logger,
            name=name,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via Modbus library."""
        try:
            async with async_timeout.timeout(60):
                # Fetch plant data
                plant_data = await self.hub.async_read_plant_data()

                # Fetch inverter data for each inverter
                inverter_data = {}
                for inverter_name in self.hub.inverter_connections.keys():
                    inverter_data[inverter_name] = await self.hub.async_read_inverter_data(inverter_name)
                    # _LOGGER.debug("Inverter data for %s: %s", inverter_name, inverter_data[inverter_name])

                # Fetch AC charger data for each AC charger
                ac_charger_data = {}
                for ac_charger_id in self.hub.ac_charger_slave_ids:
                    ac_charger_data[ac_charger_id] = await self.hub.async_read_ac_charger_data(ac_charger_id)

                # Fetch DC charger data for each DC charger
                dc_charger_data = {}
                # Iterate through the connection details dictionary
                for charger_name, connection_details in self.hub.dc_charger_connections.items():
                    # Extract the slave ID from the details
                    dc_charger_id = connection_details.get(CONF_SLAVE_ID)
                    if dc_charger_id is not None:
                        _LOGGER.debug("Fetching data for DC charger %s (ID: %s)", charger_name, dc_charger_id)
                        dc_charger_data[dc_charger_id] = await self.hub.async_read_dc_charger_data(dc_charger_id)
                    else:
                        _LOGGER.warning("Missing slave ID for DC charger '%s' in configuration", charger_name)
                
                # Combine all data
                # _LOGGER.debug("[CS][Coordinator] Plant data keys: %s", list(plant_data.keys()) if plant_data else None)
                data = {
                    "plant": plant_data,
                    "inverters": inverter_data,
                    "ac_chargers": ac_charger_data,
                    "dc_chargers": dc_charger_data,
                }

                # Log the final DC charger data structure
                # _LOGGER.debug("Coordinator Update: Final dc_chargers data: %s", dc_charger_data)

                return data
        except asyncio.TimeoutError as exception:
            raise UpdateFailed("Timeout communicating with Sigenergy system") from exception
        except Exception as exception:
            raise UpdateFailed(f"Error communicating with Sigenergy system: {exception}") from exception