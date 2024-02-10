"""API Platform for ABB Power-One PVI SunSpec.

https://github.com/alexdelprete/ha-abb-powerone-pvi-sunspec
"""

import logging
import socket

import telnetlib3

_LOGGER = logging.getLogger(__name__)


class ConnectionError(Exception):
    """Empty Error Class."""

    pass


class ABBPowerOneFimerAPI:
    """Thread safe wrapper class for pymodbus."""

    def __init__(
        self,
        hass,
        name,
        host,
        port,
        scan_interval,
    ):
        """Initialize the Modbus API Client."""
        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self._timeout = scan_interval - 1
        self._sensors = []
        self.data = {}
        # Initialize ModBus data structure before first read
        self.data["accurrent"] = 1
        self.data["accurrenta"] = 1
        self.data["accurrentb"] = 1
        self.data["accurrentc"] = 1
        self.data["acvoltageab"] = 1
        self.data["acvoltagebc"] = 1
        self.data["acvoltageca"] = 1
        self.data["acvoltagean"] = 1
        self.data["acvoltagebn"] = 1
        self.data["acvoltagecn"] = 1
        self.data["acpower"] = 1
        self.data["acfreq"] = 1
        self.data["comm_options"] = 1
        self.data["comm_manufact"] = ""
        self.data["comm_model"] = ""
        self.data["comm_version"] = ""
        self.data["comm_sernum"] = ""
        self.data["mppt_nr"] = 1
        self.data["dccurr"] = 1
        self.data["dcvolt"] = 1
        self.data["dcpower"] = 1
        self.data["dc1curr"] = 1
        self.data["dc1volt"] = 1
        self.data["dc1power"] = 1
        self.data["dc2curr"] = 1
        self.data["dc2volt"] = 1
        self.data["dc2power"] = 1
        self.data["invtype"] = ""
        self.data["status"] = ""
        self.data["statusvendor"] = ""
        self.data["totalenergy"] = 1
        self.data["tempcab"] = 1
        self.data["tempoth"] = 1

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
        is_open = sock_res == 0  # True if open, False if not
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

        try:
            reader, writer = await telnetlib3.open_connection(self._host, self._port)

            dat_parsed = await self.read_from_telnet("@dat", reader, writer)
            for key, value in dat_parsed.items():
                self.data[key] = value

            inf_parsed = await self.read_from_telnet("@inf", reader, writer)
            for key, value in inf_parsed.items():
                self.data[key] = value

            sta_parsed = await self.read_from_telnet("@sta", reader, writer)
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

    async def read_from_telnet(cmd, reader, writer):
        """Send Telnet Commands and process output."""
        try:
            output = {}
            # send the command
            writer.write(cmd + "\n")
            # read stream up to the "ready..." string
            response = await reader.readuntil(b"ready...")
            # decode bytes to string using utf-8 and split each line as a list member
            lines = response.decode("utf-8").splitlines()
            for line in lines[2:-2]:  # Exclude first and last two lines
                try:
                    if cmd == "@inf":
                        # @inf output uses a different separator
                        key, value = line.split("=")
                    else:
                        # @dat and @sta share the same output format
                        key, value = line.split(";")[1:3]
                    output[key.lower().replace(" ", "_")] = value.strip()

                except ValueError:
                    _LOGGER.debug(f"Error parsing line: {line}")
            _LOGGER.debug(f"read_from_telnet: success {output}")
        except Exception as ex:
            _LOGGER.debug(f"read_from_telnet: failed with error: {ex}")
        return output
