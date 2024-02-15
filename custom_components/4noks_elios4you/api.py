"""API Platform for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

import asyncio
import logging
import socket
from asyncio import IncompleteReadError
from datetime import datetime

import telnetlib3

from .const import MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


class ConnectionError(Exception):
    """Empty Error Class."""


class Elios4YouAPI:
    """Wrapper class."""

    def __init__(
        self,
        hass,
        name,
        host,
        port,
        scan_interval,
    ):
        """Initialize the Elios4You API Client."""
        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self._timeout = 5
        self._sensors = []
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

    async def async_get_data(self):
        """Read Data Function."""
        get_data_res = False
        if self.check_port():
            try:
                _LOGGER.debug(
                    f"async_get_data (WARNING): start open_connection {datetime.now()}"
                )
                # let's manage timeout for the connection
                reader, writer = await asyncio.wait_for(
                    telnetlib3.open_connection(self._host, self._port), self._timeout
                )
                _LOGGER.debug(
                    f"async_get_data (WARNING): start telnet_get_data {datetime.now()}"
                )
                dat_parsed = await self.telnet_get_data("@dat", reader, writer)
                if dat_parsed is not None:
                    _LOGGER.debug("async_get_data: parsing @dat data")
                    for key, value in dat_parsed.items():
                        # @dat returns only numbers as strings
                        # power/energy as float all others as int
                        if ("energy" in key) or ("power" in key):
                            self.data[key] = round(float(value), 2)
                        # don't create a utc_time sensor
                        elif key == "utc_time":
                            pass
                        else:
                            self.data[key] = int(value)
                else:
                    _LOGGER.debug("async_get_data (ERROR): @dat data is None")

                sta_parsed = await self.telnet_get_data("@sta", reader, writer)
                if dat_parsed is not None:
                    _LOGGER.debug("async_get_data (WARNING): parsing @sta data")
                    for key, value in sta_parsed.items():
                        # @sta returns only float numbers as strings
                        self.data[key] = round(float(value), 2)
                else:
                    _LOGGER.debug("async_get_data (ERROR): @sta data is None")

                inf_parsed = await self.telnet_get_data("@inf", reader, writer)
                if dat_parsed is not None:
                    _LOGGER.debug("async_get_data (WARNING): parsing @inf data")
                    for key, value in inf_parsed.items():
                        # @inf returns only strings
                        self.data[key] = str(value)
                else:
                    _LOGGER.debug("async_get_data (ERROR): @inf data is None")

                # Calculated sensor to combine TOP/BOTTOM fw versions
                self.data["swver"] = f"{self.data["fwtop"]} / {self.data["fwbtm"]}"

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
                get_data_res = True
            except TimeoutError:
                _LOGGER.debug(
                    "async_get_data (ERROR): Connection or operation timed out"
                )
                get_data_res = False
            except Exception as e:
                _LOGGER.debug(f"async_get_data (ERROR): An error occurred: {str(e)}")
                get_data_res = False
            finally:
                _LOGGER.debug("async_get_data (WARNING): closing telnet connection")
                reader.feed_eof()
        else:
            _LOGGER.debug(
                "async_get_data (ERROR): device not ready for telnet connection"
            )
            raise ConnectionError(f"device not active on {self._host}:{self._port}")
        # end async_get_data
        _LOGGER.debug(f"async_get_data: end async_get_data {datetime.now()}")
        return get_data_res

    async def telnet_get_data(self, cmd, reader, writer):
        """Send Telnet Commands and process output."""
        try:
            # cmd for telnetlib3.stream_writer.write()
            # string with LF
            cmd_send = cmd.lower() + "\n"
            # separator for telnetlib3.stream_reader.readuntil()
            # byte encoded string
            separator = "ready..."
            # get only command part without parameters
            cmd_main = cmd[0:4].lower()
            response = None
            output = {}

            _LOGGER.debug(
                f"telnet_get_data: cmd {cmd} cmd_send: {cmd_send} cmd_main: {cmd_main}"
            )

            # send the command
            _LOGGER.debug(
                f"telnet_get_data (WARNING): sending command {datetime.now()}"
            )
            writer.write(cmd_send)

            # read stream up to the "ready..." string
            _LOGGER.debug(
                f"telnet_get_data (WARNING): readline loop started at {datetime.now()}"
            )
            try:
                # sometimes telnetlib3 hangs on readuntil so we manage a timeout
                # response = await asyncio.wait_for(
                #     reader.readuntil(separator), timeout=self._timeout
                # )

                response = ""
                while True:
                    line = await asyncio.wait_for(
                        reader.readline(), timeout=self._timeout
                    )
                    if (
                        separator in line.strip()
                    ):  # Break the loop if separator string is encountered
                        break
                    response += line

            except IncompleteReadError as ex:
                _LOGGER.debug(
                    f"telnet_get_data (ERROR): only partial line could be read. Part: {ex.partial} {datetime.now()}"
                )
            except TimeoutError:
                _LOGGER.debug(
                    f"telnet_get_data (ERROR): read loop timed out at {datetime.now()}"
                )
            finally:
                _LOGGER.debug(
                    f"telnet_get_data (WARNING): read loop ended at {datetime.now()}"
                )

            # if we had a valid response we process data
            if response:
                # decode bytes to string using utf-8 and split each line as a list member
                lines = response.splitlines()
                # _LOGGER.debug(f"telnet_get_data (WARNING): lines {lines}")
                # _LOGGER.debug(f"telnet_get_data (WARNING): lines1-1 {lines[1:-1]}")
                # exclude first and last two lines
                for line in lines[1:-1]:
                    try:
                        # @inf @rel @hwr output use "=" separator
                        if (
                            cmd_main == "@inf"
                            or cmd_main == "@rel"
                            or cmd_main == "@hwr"
                        ):
                            key, value = line.split("=")
                        # @dat and @sta output use ";" separator
                        else:
                            key, value = line.split(";")[1:3]
                        # lower case and replace space with underscore
                        output[key.lower().replace(" ", "_")] = value.strip()

                    except ValueError:
                        _LOGGER.debug(
                            f"telnet_get_data (ERROR): Error parsing line: {line}"
                        )
                _LOGGER.debug(f"telnet_get_data (WARNING): success {output}")
            else:
                _LOGGER.debug("telnet_get_data (ERROR): response is None")
        except TimeoutError:
            _LOGGER.debug(
                f"telnet_get_data (ERROR): readuntil timed out at {datetime.now()}"
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
                    f"telnet_set_relay (WARNING): start open_connection {datetime.now()}"
                )
                # let's manage timeout for the connection
                reader, writer = await asyncio.wait_for(
                    telnetlib3.open_connection(self._host, self._port), self._timeout
                )
                rel_parsed = await self.telnet_get_data(
                    f"@rel 0 {to_state}", reader, writer
                )
                rel_parsed = await self.telnet_get_data("@rel", reader, writer)
                # if we had a valid response we process data
                if rel_parsed:
                    for key, value in rel_parsed.items():
                        rel_output[key] = value
                    _LOGGER.debug(f"telnet_set_relay: rel_output {rel_output}")
                    out_mode = int(rel_output["rel"])
                    _LOGGER.debug(
                        f"telnet_set_relay (WARNING): sent telnet cmd: @rel 0 {to_state} output: {out_mode}"
                    )
                    if out_mode == to_state:
                        _LOGGER.debug(
                            f"telnet_set_relay (WARNING): relay set success - to_state: {to_state} output: {out_mode}"
                        )
                        set_relay = True
                    else:
                        _LOGGER.debug(
                            f"telnet_set_relay (ERROR): relay set failure - to_state: {to_state} output: {out_mode}"
                        )
                        set_relay = False
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
                reader.feed_eof()
                _LOGGER.debug("telnet_set_relay (WARNING): end set_relay")
        else:
            _LOGGER.debug(
                f"telnet_set_relay (ERROR): Elios4you not active on {self._host}:{self._port}"
            )
            set_relay = False
        # end telnet_set_relay
        _LOGGER.debug(f"telnet_set_relay: end telnet_set_relay {datetime.now()}")
        return set_relay
