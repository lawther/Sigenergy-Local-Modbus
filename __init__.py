"""The Sigenergy ESS integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SigenergyDataUpdateCoordinator
from .modbus import SigenergyModbusHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sigenergy ESS from a config entry."""
    _LOGGER.debug("async_setup_entry: Starting setup for entry: %s", entry.title)
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    hub = SigenergyModbusHub(hass, host, port, entry)
    _LOGGER.debug("async_setup_entry: SigenergyModbusHub created: %s", hub)

    try:
        _LOGGER.debug("async_setup_entry: Connecting to Modbus hub...")
        await hub.async_connect()
        _LOGGER.debug("async_setup_entry: Modbus hub connected successfully")
    except Exception as ex:
        _LOGGER.error("async_setup_entry: Error connecting to Sigenergy system at %s:%s - %s", host, port, ex)
        raise ConfigEntryNotReady(f"Error connecting to Sigenergy system: {ex}") from ex

    coordinator = SigenergyDataUpdateCoordinator(
        hass,
        _LOGGER,
        hub=hub,
        name=f"{DOMAIN}_{host}",
        update_interval=timedelta(seconds=scan_interval),
    )
    _LOGGER.debug("async_setup_entry: SigenergyDataUpdateCoordinator created: %s", coordinator)

    _LOGGER.debug("async_setup_entry: Performing first refresh of coordinator...")
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.debug("async_setup_entry: Coordinator first refresh completed")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "hub": hub,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))
    _LOGGER.debug("async_setup_entry: Setup completed successfully for entry: %s", entry.title)
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hub = hass.data[DOMAIN][entry.entry_id]["hub"]
        await hub.async_close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok