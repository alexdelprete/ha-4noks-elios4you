"""API Platform for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

import logging
import socket
import sys
from datetime import datetime

from .const import CONN_TIMEOUT, MANUFACTURER, MODEL
from .telnetlib import Telnet

_LOGGER = logging.getLogger(__name__)


class TelnetConnectionError(Exception):
    """Exception raised when telnet connection fails."""

    def __init__(self, host: str, port: int, timeout: int, message: str = "") -> None:
        """Initialize the exception."""
        self.host = host
        self.port = port
        self.timeout = timeout
        self.message = (
            message or f"Failed to connect to {host}:{port} (timeout: {timeout}s)"
        )
        super().__init__(self.message)


class TelnetCommandError(Exception):
    """Exception raised when telnet command fails."""

    def __init__(self, command: str, message: str = "") -> None:
        """Initialize the exception."""
        self.command = command
        self.message = message or f"Command '{command}' failed"
        super().__init__(self.message)


class E4Utelnet(Telnet):
    """Python2/3 compatibility.

    Override telnetlib methods: bytes vs str
    ref: https://stackoverflow.com/a/26101026
    """

    if sys.version > "3":

        def read_until(self, separator: str, timeout: int) -> str:
            """Override telnetlib.telnet read_until."""
            separator = bytes(separator, encoding="utf-8")
            received = super().read_until(separator, timeout)
            return str(received, encoding="utf-8")

        def read_all(self) -> str:
            """Override telnetlib.telnet read_all."""
            received = super().read_all()
            return str(received, encoding="utf-8")

        def write(self, buffer):
            """Override telnetlib.telnet write."""
            buffer = bytes(buffer + "\n", encoding="utf-8")
            super().write(buffer)

        def expect(self, list, timeout=None):
            """Override telnetlib.telnet expect."""
            for index, item in enumerate(list):
                list[index] = bytes(item, encoding="utf-8")
            match_index, match_object, match_text = super().expect(list, timeout)
            return match_index, match_object, str(match_text, encoding="utf-8")

        def is_open(self) -> bool:
            """Return state of connection."""
            return False if super().get_socket() is None else True

        def close(self) -> bool:
            """Close connection."""
            if self.is_open():
                _LOGGER.debug(
                    f"E4Utelnet.close() (WARNING): close connection) {datetime.now()}"
                )
                super().close()
            else:
                _LOGGER.debug(
                    f"E4Utelnet.close() (WARNING): connection already closed) {datetime.now()}"
                )
            return True

        def open(self, host: str, port: int, timeout: int) -> bool:
            """Open connection."""
            self.close()
            super().open(host=host, port=port, timeout=timeout)
            _LOGGER.debug(
                f"E4Utelnet.open() (WARNING): opened connection) {datetime.now()}"
            )
            return True


class Elios4YouAPI:
    """Wrapper class."""

    def __init__(self, hass, name, host, port):
        """Initialize the Elios4You API Client."""
        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self._timeout = CONN_TIMEOUT
        self._sensors = []
        self.E4Uclient = E4Utelnet()
        self.data = {}
        # Initialize Elios4You data structure before first read
        self.data["produced_power"] = 1
        self.data["consumed_power"] = 1
        self.data["self_consumed_power"] = 1
        self.data["bought_power"] = 1
        self.data["sold_power"] = 1
        self.data["daily_peak"] = 1
        self.data["monthly_peak"] = 1
        self.data["produced_energy"] = 1
        self.data["produced_energy_f1"] = 1
        self.data["produced_energy_f2"] = 1
        self.data["produced_energy_f3"] = 1
        self.data["consumed_energy"] = 1
        self.data["consumed_energy_f1"] = 1
        self.data["consumed_energy_f2"] = 1
        self.data["consumed_energy_f3"] = 1
        self.data["self_consumed_energy"] = 1
        self.data["self_consumed_energy_f1"] = 1
        self.data["self_consumed_energy_f2"] = 1
        self.data["self_consumed_energy_f3"] = 1
        self.data["bought_energy"] = 1
        self.data["bought_energy_f1"] = 1
        self.data["bought_energy_f2"] = 1
        self.data["bought_energy_f3"] = 1
        self.data["sold_energy"] = 1
        self.data["sold_energy_f1"] = 1
        self.data["sold_energy_f2"] = 1
        self.data["sold_energy_f3"] = 1
        self.data["alarm_1"] = 1
        self.data["alarm_2"] = 1
        self.data["power_alarm"] = 1
        self.data["relay_state"] = 1
        self.data["pwm_mode"] = 1
        self.data["pr_ssv"] = 1
        self.data["rel_ssv"] = 1
        self.data["rel_mode"] = 1
        self.data["rel_warning"] = 1
        self.data["rcap"] = 1
        self.data["utc_time"] = ""
        self.data["fwtop"] = ""
        self.data["fwbtm"] = ""
        self.data["sn"] = ""
        self.data["hwver"] = ""
        self.data["btver"] = ""
        self.data["hw_wifi"] = ""
        self.data["s2w_app_version"] = ""
        self.data["s2w_geps_version"] = ""
        self.data["s2w_wlan_version"] = ""
        # custom fields to reuse code structure
        self.data["manufact"] = MANUFACTURER
        self.data["model"] = MODEL

    @property
    def name(self):
        """Return the device name."""
        return self._name

    @property
    def host(self):
        """Return the device name."""
        return self._host

    def close(self) -> None:
        """Close the telnet connection."""
        if self.E4Uclient:
            self.E4Uclient.close()
            _LOGGER.debug("Closed telnet client connection")

    def check_port(self) -> bool:
        """Check if port is available."""
        sock_timeout = float(3)
        _LOGGER.debug(
            f"Check_Port: opening socket on {self._host}:{self._port} with a {sock_timeout}s timeout {datetime.now()}"
        )
        socket.setdefaulttimeout(sock_timeout)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_res = sock.connect_ex((self._host, self._port))
        # True if open, False if not
        is_open = sock_res == 0
        if is_open:
            sock.shutdown(socket.SHUT_RDWR)
            _LOGGER.debug(
                f"Check_Port (success): port open on {self._host}:{self._port} {datetime.now()}"
            )
        else:
            _LOGGER.debug(
                f"Check_Port (ERROR): port not available on {self._host}:{self._port} - error: {sock_res} {datetime.now()}"
            )
        sock.close()
        return is_open

    async def async_get_data(self) -> bool:
        """Read Data Function."""
        # Check if device is reachable
        if not self.check_port():
            _LOGGER.debug("Device not reachable on %s:%s", self._host, self._port)
            raise TelnetConnectionError(
                self._host, self._port, self._timeout, "Device port not reachable"
            )

        try:
            _LOGGER.debug("Opening telnet session to %s:%s", self._host, self._port)
            self.E4Uclient.open(self._host, self._port, self._timeout)

            _LOGGER.debug("Fetching device data")
            dat_parsed = self.telnet_get_data("@dat")
            if dat_parsed is None:
                raise TelnetCommandError("@dat", "Failed to retrieve @dat data")

            _LOGGER.debug("Parsing @dat data")
            for key, value in dat_parsed.items():
                # @dat returns only numbers as strings
                # power/energy as float all others as int
                try:
                    if ("energy" in key) or ("power" in key):
                        self.data[key] = round(float(value), 2)
                    elif key == "utc_time":
                        pass
                    else:
                        self.data[key] = int(value)
                except ValueError:
                    _LOGGER.debug("Value for %s could not be parsed: %s", key, value)
                    continue

            sta_parsed = self.telnet_get_data("@sta")
            if sta_parsed is None:
                raise TelnetCommandError("@sta", "Failed to retrieve @sta data")

            _LOGGER.debug("Parsing @sta data")
            for key, value in sta_parsed.items():
                # @sta returns only float numbers as strings
                try:
                    self.data[key] = round(float(value), 2)
                except ValueError:
                    _LOGGER.debug("Value for %s could not be parsed: %s", key, value)

            inf_parsed = self.telnet_get_data("@inf")
            if inf_parsed is None:
                raise TelnetCommandError("@inf", "Failed to retrieve @inf data")

            _LOGGER.debug("Parsing @inf data")
            for key, value in inf_parsed.items():
                # @inf returns only strings
                self.data[key] = str(value)

            # Calculated sensor to combine TOP/BOTTOM fw versions
            self.data["swver"] = f"{self.data['fwtop']} / {self.data['fwbtm']}"

            # Calculated sensors for self-consumption sensors
            self.data["self_consumed_power"] = round(
                (self.data["produced_power"] - self.data["sold_power"]), 2
            )

            self.data["self_consumed_energy"] = round(
                (self.data["produced_energy"] - self.data["sold_energy"]), 2
            )

            self.data["self_consumed_energy_f1"] = round(
                (self.data["produced_energy_f1"] - self.data["sold_energy_f1"]),
                2,
            )
            self.data["self_consumed_energy_f2"] = round(
                (self.data["produced_energy_f2"] - self.data["sold_energy_f2"]),
                2,
            )
            self.data["self_consumed_energy_f3"] = round(
                (self.data["produced_energy_f3"] - self.data["sold_energy_f3"]),
                2,
            )

            _LOGGER.debug("Data fetch completed successfully")
            return True

        except (TimeoutError, OSError) as err:
            _LOGGER.debug("Connection or operation timed out: %s", err)
            raise TelnetConnectionError(
                self._host, self._port, self._timeout, f"Connection error: {err}"
            ) from err
        except (TelnetConnectionError, TelnetCommandError):
            # Re-raise our custom exceptions
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error during data fetch: %s", err)
            raise TelnetCommandError(
                "async_get_data", f"Unexpected error: {err}"
            ) from err
        finally:
            _LOGGER.debug("Closing telnet connection")
            self.E4Uclient.close()

    def telnet_get_data(self, cmd: str):
        """Send Telnet Commands and process output."""
        try:
            cmd_main = cmd[0:4].lower()
            cmd_send = cmd.lower()
            output = {}
            response = None
            separator = "ready..."

            _LOGGER.debug(
                f"telnet_get_data: cmd {cmd} cmd_send: {cmd_send} cmd_main: {cmd_main}"
            )

            # send the command
            _LOGGER.debug(
                f"telnet_get_data (WARNING): sending command {datetime.now()}"
            )
            # send the command
            self.E4Uclient.write(cmd_send)

            try:
                response = ""
                _LOGGER.debug(
                    f"telnet_get_data (WARNING): read_until loop started (conn: {self.E4Uclient.is_open()}) at {datetime.now()}"
                )
                # read stream up to the "ready..."" string (end of response)
                response = self.E4Uclient.read_until(separator, self._timeout)
                _LOGGER.debug(
                    f"telnet_get_data (WARNING): read_until loop ended (conn: {self.E4Uclient.is_open()}) at {datetime.now()}"
                )
            except TimeoutError:
                _LOGGER.debug(
                    f"telnet_get_data (ERROR): read_until timed out at {datetime.now()}"
                )
            finally:
                _LOGGER.debug(
                    f"telnet_get_data (WARNING): read_until ended at {datetime.now()}"
                )

            # if we had a valid response we process data
            if response:
                # decode bytes to string using utf-8 and split each line as a list member
                lines = response.splitlines()
                # sometimes the first line is not the command but a line-feed
                if lines[0].lower() in ["@dat", "@sta", "@inf", "@rel", "@hwr"]:
                    lines_start = 1
                else:
                    # skip the possible LF in first line
                    lines_start = 2
                # skip last two lines (line-feed and read_until separator)
                lines_end = -2
                # exclude first X and last Y lines
                for line in lines[lines_start:lines_end]:
                    if cmd_main in ["@inf", "@rel", "@hwr"]:
                        # @inf data uses a different separator
                        key, value = line.split("=")
                    else:
                        # @dat and @sta share the same data format
                        key, value = line.split(";")[1:3]
                        # lower case and replace space with underscore
                    output[key.lower().replace(" ", "_")] = value.strip()
                _LOGGER.debug(f"telnet_get_data (WARNING): success {output}")
            else:
                _LOGGER.debug("telnet_get_data (ERROR): response is None")
        except TimeoutError:
            _LOGGER.debug(
                f"telnet_get_data (ERROR): read_until timed out at {datetime.now()}"
            )
        except Exception as ex:
            _LOGGER.debug(f"telnet_get_data (ERROR): failed with error: {ex}")
        finally:
            return output if response is not None else None

    async def telnet_set_relay(self, state) -> bool:
        """Send Telnet Commands and process output."""
        set_relay = False
        rel_parsed = None
        if self.check_port():
            if state.lower() == "on":
                to_state: int = 1
            elif state.lower() == "off":
                to_state: int = 0
            else:
                return set_relay
            try:
                rel_output = {}
                _LOGGER.debug(
                    f"telnet_set_relay (WARNING): open connection {datetime.now()}"
                )
                # open connection ensuring previous connections are closed
                self.E4Uclient.open(self._host, self._port, self._timeout)

                rel_parsed = self.telnet_get_data(f"@rel 0 {to_state}")
                rel_parsed = self.telnet_get_data("@rel")
                # if we had a valid response we process data
                if rel_parsed:
                    for key, value in rel_parsed.items():
                        rel_output[key] = value
                    _LOGGER.debug(f"telnet_set_relay: rel_output {rel_output}")
                    out_mode = int(rel_output["rel"])
                    _LOGGER.debug(
                        f"telnet_set_relay (WARNING): sent telnet cmd: @rel 0 {to_state} rel: {out_mode}"
                    )
                    if out_mode == to_state:
                        set_relay = True
                        # refresh relay_state value to avoid waiting for poll cycle
                        self.data["relay_state"] = out_mode
                        _LOGGER.debug(
                            f"telnet_set_relay (WARNING): set relay success - to_state: {to_state} - rel: {out_mode} - relay_state: {self.data['relay_state']}"
                        )
                    else:
                        set_relay = False
                        _LOGGER.debug(
                            f"telnet_set_relay (ERROR): set relay failure - to_state: {to_state} - rel: {out_mode} - relay_state: {self.data['relay_state']}"
                        )
                else:
                    _LOGGER.debug("telnet_set_relay (ERROR): rel_parsed is None")
            except TimeoutError:
                _LOGGER.debug(
                    "telnet_set_relay (ERROR): Connection or operation timed out"
                )
                set_relay = False
            except Exception as ex:
                _LOGGER.debug(f"telnet_set_relay (ERROR): failed with error: {ex}")
                set_relay = False
            finally:
                _LOGGER.debug("telnet_set_relay (WARNING): closing telnet session")
                self.E4Uclient.close()
                _LOGGER.debug("telnet_set_relay (WARNING): end set_relay")
        else:
            _LOGGER.debug(
                f"telnet_set_relay (ERROR): Elios4you not active on {self._host}:{self._port}"
            )
            set_relay = False
        # end telnet_set_relay
        _LOGGER.debug(f"telnet_set_relay: end telnet_set_relay {datetime.now()}")
        return set_relay
