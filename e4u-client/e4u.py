"""Elios4you Client."""

import asyncio

import telnetlib3


async def get_data(cmd, reader, writer):
    """."""
    data = {}
    # send the command
    writer.write(cmd + "\n")
    # read stream up to the "ready..."" string (end of response)
    response = await reader.readuntil(b"ready...")
    # decode bytes to string using utf-8 and split each line as a list member
    lines = response.decode("utf-8").splitlines()
    # Exclude first and last two lines
    for line in lines[2:-2]:
        try:
            if cmd == "@inf" or cmd == "@hwr":
                # @inf data uses a different separator
                key, value = line.split("=")
            else:
                # @dat and @sta share the same data format
                key, value = line.split(";")[1:3]
            data[key.lower().replace(" ", "_")] = value.strip()

        except ValueError:
            print(f"Error parsing line: {line}")  # noqa: T201

    return data


async def main():
    """."""
    host = "elios4u.axel.dom"  # IP or hostname
    port = 5001  # Elios4You default port

    try:
        reader, writer = await telnetlib3.open_connection(host, port)

        dat_parsed = await get_data("@dat", reader, writer)
        print("\n -= DAT =-")  # noqa: T201
        for key, value in dat_parsed.items():
            print(f"{key}: {value}")  # noqa: T201

        sta_parsed = await get_data("@sta", reader, writer)
        print("\n -= STA =-")  # noqa: T201
        for key, value in sta_parsed.items():
            print(f"{key}: {value}")  # noqa: T201

        inf_parsed = await get_data("@inf", reader, writer)
        print("\n -= INF =-")  # noqa: T201
        for key, value in inf_parsed.items():
            print(f"{key}: {value}")  # noqa: T201

        hwr_parsed = await get_data("@hwr", reader, writer)
        print("\n -= HWR =-")  # noqa: T201
        for key, value in hwr_parsed.items():
            print(f"{key}: {value}")  # noqa: T201

        print("\n")  # noqa: T201

    except TimeoutError:
        print("Connection or operation timed out")  # noqa: T201

    except Exception as e:
        print(f"An error occurred: {str(e)}")  # noqa: T201

    finally:
        if not writer.transport.is_closing():
            writer.close()
            # await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
