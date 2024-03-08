"""Elios4you Client."""

import asyncio
import sys

from lib.telnetlib import Telnet


class E4Utelnet(Telnet):  # noqa: D101
    if sys.version > "3":

        def read_until(self, expected, timeout=None):  # noqa: D102
            expected = bytes(expected, encoding="utf-8")
            received = super().read_until(expected, timeout)  # noqa: UP008
            return str(received, encoding="utf-8")

        def read_all(self):  # noqa: D102
            received = super().read_all()  # noqa: UP008
            return str(received, encoding="utf-8")

        def write(self, buffer):  # noqa: D102
            buffer = bytes(buffer + "\n", encoding="utf-8")
            super().write(buffer)  # noqa: UP008

        def expect(self, list, timeout=None):  # noqa: D102
            for index, item in enumerate(list):
                list[index] = bytes(item, encoding="utf-8")
            match_index, match_object, match_text = super().expect(  # noqa: UP008
                list, timeout
            )  # noqa: UP008
            return match_index, match_object, str(match_text, encoding="utf-8")


async def get_data(telnet: E4Utelnet, cmd: str):
    """."""
    data = {}
    response = ""
    separator = "ready..."
    cmd_main = cmd[0:4].lower()
    cmd_send = cmd.lower()

    # send the command
    telnet.write(cmd_send)
    # read stream up to the "ready..."" string (end of response)
    response = telnet.read_until(separator, timeout=3)
    if response:
        # decode bytes to string using utf-8 and split each line as a list member
        lines = response.splitlines()
        lines_start = (
            1 if lines[0].lower() in ["@dat", "@sta", "@inf", "@rel", "@hwr"] else 2
        )
        lines_end = -2
        print("=============================")  # noqa: T201
        print(f"lines {lines}")  # noqa: T201
        print(f"lines parsed {lines[lines_start:lines_end]}")  # noqa: T201
        for line in lines[lines_start:lines_end]:
            if cmd_main in ["@inf", "@rel", "@hwr"]:
                # @inf data uses a different separator
                key, value = line.split("=")
            else:
                # @dat and @sta share the same data format
                key, value = line.split(";")[1:3]
            data[key.lower().replace(" ", "_")] = value.strip()
    else:
        print("Response empty")  # noqa: T201
    return data


async def main():
    """."""
    host = "elios4u.axel.dom"  # IP or hostname
    port = 5001  # Elios4You default port

    try:
        telnet = E4Utelnet(host=host, port=port, timeout=5)

        dat_parsed = await get_data(telnet, "@dat")
        print("\n -= DAT =-")  # noqa: T201
        for key, value in dat_parsed.items():
            print(f"{key}: {value}")  # noqa: T201

        sta_parsed = await get_data(telnet, "@sta")
        print("\n -= STA =-")  # noqa: T201
        for key, value in sta_parsed.items():
            print(f"{key}: {value}")  # noqa: T201

        inf_parsed = await get_data(telnet, "@inf")
        print("\n -= INF =-")  # noqa: T201
        for key, value in inf_parsed.items():
            print(f"{key}: {value}")  # noqa: T201

        rel_parsed = await get_data(telnet, "@rel")
        print("\n -= REL =-")  # noqa: T201
        for key, value in rel_parsed.items():
            print(f"{key}: {value}")  # noqa: T201

        hwr_parsed = await get_data(telnet, "@hwr")
        print("\n -= HWR =-")  # noqa: T201
        for key, value in hwr_parsed.items():
            print(f"{key}: {value}")  # noqa: T201

        print("=============================\n")  # noqa: T201

    except TimeoutError:
        print("Connection or operation timed out")  # noqa: T201

    except Exception as e:
        print(f"An error occurred: {str(e)}")  # noqa: T201

    finally:
        if telnet.get_socket() is not None:
            print("\n Socket is OPEN: let's close it.")  # noqa: T201
            telnet.close()
        else:
            print("\n Socket is NOT OPEN.")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
