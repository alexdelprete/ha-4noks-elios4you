"""Data Update Coordinator for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Elios4YouAPI
from .const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .helpers import log_debug
from .repairs import create_connection_issue, delete_connection_issue

_LOGGER = logging.getLogger(__name__)

# Number of consecutive failures before creating repair issue
FAILURES_BEFORE_REPAIR_ISSUE = 3


class Elios4YouCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize data update coordinator."""
        # get parameters from user config
        self.conf_name: str = str(config_entry.data.get(CONF_NAME, ""))
        self.conf_host: str = str(config_entry.data.get(CONF_HOST, ""))
        self.conf_port: int = int(config_entry.data.get(CONF_PORT, 5001))
        # Read from options first (v2), fall back to data for migration compatibility (v1)
        self.scan_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL,
            config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        # enforce scan_interval lower bound
        self.scan_interval = max(self.scan_interval, MIN_SCAN_INTERVAL)
        # calculate update interval for coordinator
        update_interval = timedelta(seconds=self.scan_interval)
        log_debug(
            _LOGGER,
            "__init__",
            "Scan interval configured",
            scan_interval=self.scan_interval,
            update_interval=update_interval,
        )

        # set update method and interval for coordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_method=self.async_update_data,  # type: ignore[arg-type]
            update_interval=update_interval,
        )

        self.last_update_time = datetime.now()
        self.last_update_success = True
        self._consecutive_failures = 0
        self._repair_issue_created = False
        self._entry_id = config_entry.entry_id

        self.api = Elios4YouAPI(
            hass,
            self.conf_name,
            self.conf_host,
            self.conf_port,
        )

        log_debug(_LOGGER, "__init__", "Coordinator config data", data=config_entry.data)
        log_debug(
            _LOGGER,
            "__init__",
            "Coordinator initialized",
            host=self.conf_host,
            port=self.conf_port,
            scan_interval=self.scan_interval,
        )

    async def async_update_data(self) -> bool:
        """Update data method."""
        log_debug(_LOGGER, "async_update_data", "Update started", time=datetime.now())
        try:
            self.last_update_status = await self.api.async_get_data()
            self.last_update_time = datetime.now()
            log_debug(
                _LOGGER,
                "async_update_data",
                "Update completed",
                time=self.last_update_time,
            )
            # Reset failure counter on success
            self._consecutive_failures = 0
            # Delete repair issue if it was created
            if self._repair_issue_created:
                delete_connection_issue(self.hass, self._entry_id)
                self._repair_issue_created = False
                log_debug(
                    _LOGGER,
                    "async_update_data",
                    "Connection restored, repair issue deleted",
                )
            return self.last_update_status
        except Exception as ex:
            self.last_update_status = False
            self._consecutive_failures += 1
            log_debug(
                _LOGGER,
                "async_update_data",
                "Coordinator update error",
                error=ex,
                consecutive_failures=self._consecutive_failures,
                time=self.last_update_time,
            )
            # Create repair issue after repeated failures
            if (
                self._consecutive_failures >= FAILURES_BEFORE_REPAIR_ISSUE
                and not self._repair_issue_created
            ):
                create_connection_issue(
                    self.hass,
                    self._entry_id,
                    self.conf_name,
                    self.conf_host,
                    self.conf_port,
                )
                self._repair_issue_created = True
                log_debug(
                    _LOGGER,
                    "async_update_data",
                    "Repair issue created after repeated failures",
                    failures=self._consecutive_failures,
                )
            raise UpdateFailed() from ex
