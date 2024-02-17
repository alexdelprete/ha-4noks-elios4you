"""Elios4you Client."""

import asyncio

import telnetlib3


async def get_data(cmd, reader, writer):
    """."""
    data = {}
    separator = "ready..."
    # send the command
    writer.write(cmd + "\n")
    # read stream up to the "ready..."" string (end of response)
    # response = await reader.readuntil(b"ready...")
    response = ""
    while True:
        line = await asyncio.wait_for(reader.readline(), timeout=5)
        # if not line.strip():  # Break the loop if an empty line is encountered
        if separator in line.strip():
            break
        response += line
    if response:
        # decode bytes to string using utf-8 and split each line as a list member
        lines = response.splitlines()
        # print(f"lines {lines}")  # noqa: T201
        # print(f"lines 1-1 {lines[1:-1]}")  # noqa: T201
        # Exclude first two lines
        for line in lines[1:-1]:
            try:
                if cmd == "@inf" or cmd == "@rel" or cmd == "@hwr":
                    # @inf data uses a different separator
                    key, value = line.split("=")
                else:
                    # @dat and @sta share the same data format
                    key, value = line.split(";")[1:3]
                data[key.lower().replace(" ", "_")] = value.strip()

            except ValueError:
                print(f"Error parsing line: {line}")  # noqa: T201
    else:
        print("Response empty")  # noqa: T201
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

        rel_parsed = await get_data("@rel", reader, writer)
        print("\n -= REL =-")  # noqa: T201
        for key, value in rel_parsed.items():
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
            reader.feed_eof()


if __name__ == "__main__":
    asyncio.run(main())
