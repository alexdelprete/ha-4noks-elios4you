"""API Platform for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

import logging
import socket

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
        self._timeout = scan_interval - 1
        self._sensors = []
        self.data = {}
        # Initialize Elios4You data structure before first read
        self.data["produced_power"] = 1
        self.data["consumed_power"] = 1
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
        self.data["swver"] = f'{self.data["fwtop"]} / {self.data["fwbtm"]}'
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
            f"Check_Port: opening socket on {self._host}:{self._port} with a {sock_timeout}s timeout."
        )
        socket.setdefaulttimeout(sock_timeout)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_res = sock.connect_ex((self._host, self._port))
        # True if open, False if not
        is_open = sock_res == 0
        if is_open:
            sock.shutdown(socket.SHUT_RDWR)
            _LOGGER.debug(
                f"Check_Port (SUCCESS): port open on {self._host}:{self._port}"
            )
        else:
            _LOGGER.debug(
                f"Check_Port (ERROR): port not available on {self._host}:{self._port} - error: {sock_res}"
            )
        sock.close()
        return is_open

    async def async_get_data(self):
        """Read Data Function."""

        if self.check_port():
            try:
                reader, writer = await telnetlib3.open_connection(
                    self._host, self._port
                )

                dat_parsed = await self.telnet_get_data("@dat", reader, writer)
                for key, value in dat_parsed.items():
                    self.data[key] = value

                inf_parsed = await self.telnet_get_data("@inf", reader, writer)
                for key, value in inf_parsed.items():
                    self.data[key] = value

                sta_parsed = await self.telnet_get_data("@sta", reader, writer)
                for key, value in sta_parsed.items():
                    self.data[key] = value

            except TimeoutError:
                _LOGGER.debug("Connection or operation timed out")

            except Exception as e:
                _LOGGER.debug(f"An error occurred: {str(e)}")

            finally:
                if not writer.transport.is_closing():
                    writer.close()
                    # await writer.wait_closed()
        else:
            _LOGGER.debug("Elios4you not ready for telnet connection")
            raise ConnectionError(f"Elios4you not active on {self._host}:{self._port}")

    async def telnet_get_data(self, cmd, reader, writer):
        """Send Telnet Commands and process output."""
        try:
            cmd = cmd.lower()
            cmd_main = cmd[0:4]
            _LOGGER.debug(f"telnet_get_data: cmd {cmd} cmd_main: {cmd_main}")
            output = {}
            # send the command
            writer.write(cmd + "\n")
            # read stream up to the "ready..." string
            response = await reader.readuntil(b"ready...")
            # decode bytes to string using utf-8 and split each line as a list member
            lines = response.decode("utf-8").splitlines()
            # exclude first and last two lines
            for line in lines[2:-2]:
                try:
                    # @inf @rel @hwr output use "=" separator
                    if cmd_main == "@inf" or cmd_main == "@rel" or cmd_main == "@hwr":
                        key, value = line.split("=")
                    # @dat and @sta output use ";" separator
                    else:
                        key, value = line.split(";")[1:3]
                    # lower case and replace space with underscore
                    output[key.lower().replace(" ", "_")] = value.strip()

                except ValueError:
                    _LOGGER.debug(f"Error parsing line: {line}")
            _LOGGER.debug(f"telnet_get_data: success {output}")
        except Exception as ex:
            _LOGGER.debug(f"telnet_get_data: failed with error: {ex}")
        return output

    async def telnet_set_relay(self, state) -> bool:
        """Send Telnet Commands and process output."""
        set_relay = False
        if self.check_port():
            if state.lower() == "on":
                to_state = 1
            elif state.lower() == "off":
                to_state = 0
            else:
                return set_relay
            try:
                rel_output = {}
                reader, writer = await telnetlib3.open_connection(
                    self._host, self._port
                )
                rel_parsed = await self.telnet_get_data(
                    f"@rel 0 {to_state}", reader, writer
                )
                for key, value in rel_parsed.items():
                    rel_output[key] = value
                _LOGGER.debug(f"telnet_set_relay: sent telnet cmd: @rel 0 {to_state}")
                if rel_output["mode"] == to_state:
                    _LOGGER.debug(
                        f"telnet_set_relay: relay set success - to_state: {to_state} output: {rel_output["mode"]}"
                    )
                    set_relay = True
                else:
                    _LOGGER.debug(
                        f"telnet_set_relay: relay set failure - to_state: {to_state} output: {rel_output["mode"]}"
                    )
                    set_relay = False
            except Exception as ex:
                _LOGGER.debug(f"telnet_set_relay: failed with error: {ex}")
                set_relay = False
            finally:
                if not writer.transport.is_closing():
                    _LOGGER.debug("telnet_set_relay: closing telnet session")
                    writer.close()
                    # await writer.wait_closed()
            return set_relay
        else:
            _LOGGER.debug(f"Elios4you not active on {self._host}:{self._port}")
            return set_relay
