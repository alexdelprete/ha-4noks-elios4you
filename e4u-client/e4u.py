import telnetlib3
import asyncio

async def get_data(cmd, reader, writer):
    data = {}
    writer.write(cmd + "\n")                        # send the command
    response = await reader.readuntil(b"ready...")  # read stream up to the "ready..."" string (end of response)
    lines = response.decode('utf-8').splitlines()   # decode bytes to string using utf-8 and split each line as a list member
    for line in lines[2:-2]:                        # Exclude first and last two lines
        try:
            if cmd == "@inf":
                key, value = line.split('=')            # @inf data uses a different separator
            else:
                key, value = line.split(';')[1:3]       # @dat and @sta share the same data format
            data[key.lower().replace(' ', '_')] = value.strip()

        except ValueError:
            print(f"Error parsing line: {line}")

    return data

async def main():
    host = 'elios4u.axel.dom'   # IP or hostname
    port = 5001                 # Elios4You default port

    try:
        reader, writer = await telnetlib3.open_connection(host, port)

        dat_parsed = await get_data("@dat", reader, writer)
        print("\n -= DAT =-")
        for key, value in dat_parsed.items():
            print(f'{key}: {value}')

        inf_parsed = await get_data("@inf", reader, writer)
        print("\n -= INF =-")
        for key, value in inf_parsed.items():
            print(f'{key}: {value}')

        sta_parsed = await get_data("@sta", reader, writer)
        print("\n -= STA =-")
        for key, value in sta_parsed.items():
            print(f'{key}: {value}')

        print("\n")

    except asyncio.TimeoutError:
        print("Connection or operation timed out")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

    finally:
        if not writer.transport.is_closing():
            writer.close()
            # await writer.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())