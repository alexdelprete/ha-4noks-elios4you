"""Diagnostics support for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import Elios4YouConfigEntry
from .const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL, DOMAIN, VERSION

# Keys to redact from diagnostics output
TO_REDACT = {
    CONF_HOST,
    "sn",
    "serial_number",
    "ip",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: Elios4YouConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data.coordinator

    # Gather configuration data
    config_data = {
        "entry_id": config_entry.entry_id,
        "version": config_entry.version,
        "domain": DOMAIN,
        "integration_version": VERSION,
        "data": async_redact_data(dict(config_entry.data), TO_REDACT),
        "options": {
            CONF_SCAN_INTERVAL: config_entry.options.get(CONF_SCAN_INTERVAL),
        },
    }

    # Gather device info
    device_data = {
        "name": config_entry.data.get(CONF_NAME),
        "port": config_entry.data.get(CONF_PORT),
        "manufacturer": coordinator.api.data.get("manufact"),
        "model": coordinator.api.data.get("model"),
        "serial_number": "**REDACTED**",
    }

    # Gather coordinator state
    coordinator_data = {
        "last_update_success": coordinator.last_update_success,
        "update_interval_seconds": coordinator.update_interval.total_seconds()
        if coordinator.update_interval
        else None,
    }

    # Gather sensor data (redact sensitive values)
    sensor_data = {}
    if coordinator.api.data:
        for key, value in coordinator.api.data.items():
            if key in TO_REDACT:
                sensor_data[key] = "**REDACTED**"
            else:
                sensor_data[key] = value

    return {
        "config": config_data,
        "device": device_data,
        "coordinator": coordinator_data,
        "sensors": sensor_data,
    }
