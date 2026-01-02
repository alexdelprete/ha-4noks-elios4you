"""Data Update Coordinator for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from datetime import datetime, timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import Elios4YouAPI, TelnetCommandError, TelnetConnectionError
from .const import (
    CONF_ENABLE_REPAIR_NOTIFICATION,
    CONF_FAILURES_THRESHOLD,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_RECOVERY_SCRIPT,
    CONF_SCAN_INTERVAL,
    DEFAULT_ENABLE_REPAIR_NOTIFICATION,
    DEFAULT_FAILURES_THRESHOLD,
    DEFAULT_RECOVERY_SCRIPT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .helpers import log_debug, log_info, log_warning
from .repairs import create_connection_issue, create_recovery_notification, delete_connection_issue

_LOGGER = logging.getLogger(__name__)


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
        self._recovery_script_executed = False
        self._entry_id = config_entry.entry_id

        # Device trigger tracking
        self.device_id: str | None = None
        self._failure_start_time: float | None = None
        self._last_error_type: str | None = None
        self._script_executed_time: float | None = None

        # Repair notification options from config
        self._enable_repair_notification = config_entry.options.get(
            CONF_ENABLE_REPAIR_NOTIFICATION, DEFAULT_ENABLE_REPAIR_NOTIFICATION
        )
        self._failures_threshold = config_entry.options.get(
            CONF_FAILURES_THRESHOLD, DEFAULT_FAILURES_THRESHOLD
        )
        self._recovery_script = config_entry.options.get(
            CONF_RECOVERY_SCRIPT, DEFAULT_RECOVERY_SCRIPT
        )

        log_debug(
            _LOGGER,
            "__init__",
            "Repair notification options",
            enabled=self._enable_repair_notification,
            threshold=self._failures_threshold,
            recovery_script=self._recovery_script,
        )

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
            # Handle recovery after repair issue was created
            if self._repair_issue_created:
                # Calculate downtime and format times using locale-aware format
                downtime_seconds = 0
                if self._failure_start_time:
                    downtime_seconds = int(time.time() - self._failure_start_time)

                # Format times using locale-aware format (%X)
                ended_at = dt_util.as_local(dt_util.utcnow()).strftime("%X")
                started_at = ""
                if self._failure_start_time:
                    started_at = dt_util.as_local(
                        dt_util.utc_from_timestamp(self._failure_start_time)
                    ).strftime("%X")
                downtime = self._format_downtime(downtime_seconds)

                # Get script execution time if script was executed
                script_executed_at = None
                if self._recovery_script_executed and self._script_executed_time:
                    script_executed_at = dt_util.as_local(
                        dt_util.utc_from_timestamp(self._script_executed_time)
                    ).strftime("%X")

                # Fire device_recovered event
                self._fire_device_event(
                    "device_recovered",
                    {
                        "previous_failures": self._consecutive_failures,
                        "downtime_seconds": downtime_seconds,
                    },
                )

                delete_connection_issue(self.hass, self._entry_id)
                log_info(
                    _LOGGER,
                    "async_update_data",
                    "Connection restored, repair issue deleted",
                    downtime_seconds=downtime_seconds,
                )

                # Always create recovery notification (with or without script info)
                create_recovery_notification(
                    self.hass,
                    self._entry_id,
                    self.conf_name,
                    started_at=started_at,
                    ended_at=ended_at,
                    downtime=downtime,
                    script_name=self._recovery_script if self._recovery_script_executed else None,
                    script_executed_at=script_executed_at,
                )
                log_info(
                    _LOGGER,
                    "async_update_data",
                    "Recovery notification created",
                    started_at=started_at,
                    ended_at=ended_at,
                    downtime=downtime,
                    script=self._recovery_script if self._recovery_script_executed else None,
                )

                # Reset tracking variables
                self._repair_issue_created = False
                self._failure_start_time = None
                self._last_error_type = None
                self._recovery_script_executed = False
                self._script_executed_time = None

            # Reset failure counter on success
            self._consecutive_failures = 0
        except Exception as ex:
            self.last_update_status = False
            self._consecutive_failures += 1

            # Determine error type for device trigger
            if isinstance(ex, TelnetConnectionError):
                self._last_error_type = "device_unreachable"
            elif isinstance(ex, TelnetCommandError):
                self._last_error_type = "device_not_responding"
            else:
                self._last_error_type = "device_unreachable"  # Default to unreachable

            log_debug(
                _LOGGER,
                "async_update_data",
                "Coordinator update error",
                error=ex,
                error_type=self._last_error_type,
                consecutive_failures=self._consecutive_failures,
                time=self.last_update_time,
            )

            # Create repair issue and fire device trigger after threshold reached
            if (
                self._consecutive_failures >= self._failures_threshold
                and not self._repair_issue_created
            ):
                # Record failure start time for downtime tracking
                self._failure_start_time = time.time()

                # Fire device trigger event
                self._fire_device_event(
                    self._last_error_type,
                    {
                        "error": str(ex),
                        "failures_threshold": self._failures_threshold,
                    },
                )

                # Create repair issue (if enabled)
                if self._enable_repair_notification:
                    create_connection_issue(
                        self.hass,
                        self._entry_id,
                        self.conf_name,
                        self.conf_host,
                        self.conf_port,
                    )
                    log_info(
                        _LOGGER,
                        "async_update_data",
                        "Repair issue created after repeated failures",
                        failures=self._consecutive_failures,
                        threshold=self._failures_threshold,
                    )

                self._repair_issue_created = True

                # Execute recovery script if configured
                if self._recovery_script:
                    await self._execute_recovery_script()

            raise UpdateFailed from ex

        return self.last_update_status

    async def _execute_recovery_script(self) -> None:
        """Execute the configured recovery script."""
        if not self._recovery_script:
            return

        try:
            # Extract script name from entity_id (e.g., "script.restart_wifi" -> "restart_wifi")
            script_name = self._recovery_script.replace("script.", "")

            log_info(
                _LOGGER,
                "_execute_recovery_script",
                "Executing recovery script",
                script=self._recovery_script,
                device_name=self.conf_name,
                host=self.conf_host,
            )

            # Call the script with device information as variables
            await self.hass.services.async_call(
                domain="script",
                service=script_name,
                service_data={
                    "device_name": self.conf_name,
                    "host": self.conf_host,
                    "port": self.conf_port,
                    "serial_number": self.api.data.get("sn", ""),
                    "mac_address": self.api.data.get("mac", ""),
                    "failures_count": self._consecutive_failures,
                },
                blocking=False,  # Don't wait for script completion
            )

            self._recovery_script_executed = True
            self._script_executed_time = time.time()
            log_info(
                _LOGGER,
                "_execute_recovery_script",
                "Recovery script executed successfully",
                script=self._recovery_script,
            )
        except HomeAssistantError as err:
            log_warning(
                _LOGGER,
                "_execute_recovery_script",
                "Failed to execute recovery script",
                script=self._recovery_script,
                error=str(err),
            )

    def _format_downtime(self, seconds: int) -> str:
        """Format downtime in compact format (e.g., '5m 23s')."""
        if seconds < 60:
            return f"{seconds}s"
        minutes, secs = divmod(seconds, 60)
        if minutes < 60:
            return f"{minutes}m {secs}s" if secs else f"{minutes}m"
        hours, mins = divmod(minutes, 60)
        if mins:
            return f"{hours}h {mins}m"
        return f"{hours}h"

    def _fire_device_event(self, event_type: str, extra_data: dict[str, Any] | None = None) -> None:
        """Fire a device event on the HA event bus for device triggers."""
        if not self.device_id:
            log_debug(
                _LOGGER,
                "_fire_device_event",
                "Cannot fire event, device_id not set",
                event_type=event_type,
            )
            return

        event_data: dict[str, Any] = {
            "device_id": self.device_id,
            "type": event_type,
            "device_name": self.conf_name,
            "host": self.conf_host,
            "port": self.conf_port,
            "serial_number": self.api.data.get("sn", ""),
            "mac_address": self.api.data.get("mac", ""),
        }
        if extra_data:
            event_data.update(extra_data)

        self.hass.bus.async_fire(f"{DOMAIN}_event", event_data)
        log_debug(
            _LOGGER,
            "_fire_device_event",
            "Device event fired",
            event_type=event_type,
            device_id=self.device_id,
        )
