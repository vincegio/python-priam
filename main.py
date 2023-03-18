import asyncio
import bleak
import asyncio
import time
import datetime
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice


class SupportLevel:
    ECO = 1
    TOUR = 2
    BOOST = 3


class StatusData:
    def __init__(self, raw: bytes, battery_volts: int):
        self.raw = raw
        self.battery_volts = battery_volts


async def initiate_listeners(client):
    print("Initiating listeners")

    def output(data):
        with open("notifications.txt", "a") as f:
            f.write(f"{datetime.datetime.now().isoformat()} - {data}\n")
            f.flush()

    async def notification_handler(sender, data):
        hex_string = ''.join('{:02x}'.format(x) for x in data)
        # This function will be called when notifications are received
        output(
            f"Received notification on {sender.uuid}: {data} - {hex_string}")

    async def status_handler(sender, data):

        battery_volts = (data[3] & 255) * 2
        status_data = StatusData(data, battery_volts)

        min_voltage = 315
        max_voltage = 380

        def calculate_battery_percentage(voltage):
            voltage_range = max_voltage - min_voltage
            voltage_above_min = voltage - min_voltage
            battery_percentage = voltage_above_min / voltage_range * 100
            return max(min(battery_percentage, 100), 0)

        battery_percentage = calculate_battery_percentage(
            status_data.battery_volts)
        output(
            f"Battery percentage: {round(battery_percentage)}, raw: {''.join([format(b, '02x') for b in data])}")

    async def rocking_handler(_, data):
        rocking_error = "none"
        if len(data) < 4:
            return None

        elif (data[0] ^ 128) != 20:
            rocking_error = "unknown"
        else:
            rocking_error = "brake not eng."

        def p(b2, b3, z):
            if z:
                return ((b2 & 255) << 8) | (b3 & 255)
            return (b2 & 255) | ((b3 & 255) << 8)

        intensity = data[0] & 0xF
        time_left = p(data[1], data[2], False)
        set_time = p(data[3], data[4], False)
        disc = bool(data[0] & 0b00010000)

        output(
            f"Rock! error: {rocking_error}, intensity: {intensity}, time_left: {time_left}, set_time:{set_time}, disc: {disc} - raw: {''.join([format(b, '02x') for b in data])}")

    await client.start_notify("a1fc0102-78d3-40c2-9b6f-3c5f7b2797df", status_handler)
    await client.start_notify(
        "a1fc0103-78d3-40c2-9b6f-3c5f7b2797df", notification_handler)
    await client.start_notify(
        "a1fc0104-78d3-40c2-9b6f-3c5f7b2797df", rocking_handler)
    while True:
        await asyncio.sleep(1)


async def get_input(prompt: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input, prompt)


async def initiate_interaction(client):
    print("Initiating interaction")

    while True:
        try:
            mode = int(await get_input("Mode (1: rocking, 2: spport level): "))
            match mode:
                case 1:
                    duration = 55
                    rocking_intensity = int(await get_input(
                        "Enter a value for 'rocking_intensity' (0: OFF, 1: HIGH, 2: MED, 3: LOW): "))
                    if rocking_intensity < 0 or rocking_intensity > 3:
                        raise ValueError
                    stop_on_disconnect = False
                    d = rocking_intensity
                    if stop_on_disconnect:
                        d |= 16
                    bArr = bytes(
                        [(duration & 65535), ((duration >> 8) & 65535)])
                    bArr2 = bytes([d, bArr[0], bArr[1]])
                    hex_str = ''.join([format(b, '02x') for b in bArr2])

                    print("Got hex, trying to rock: ", hex_str)
                    await client.write_gatt_char("a1fc0104-78d3-40c2-9b6f-3c5f7b2797df", bArr2)
                    print(f"Sent...")
                    print("---")
                case 2:
                    support_level = int(
                        await get_input("Enter a value for 'drive_mode' (1: ECO, 2: TOUR, 3: BOOST???): "))
                    if support_level < 1 or support_level > 3:
                        raise ValueError

                    bArr = bytes([support_level])
                    hex_str = ''.join([format(b, '02x') for b in bArr])
                    print("Got hex, trying to blaze: ", hex_str)
                    await client.write_gatt_char("a1fc0103-78d3-40c2-9b6f-3c5f7b2797df", bArr)
                    print("Sent...")
                    print("---")
        except ValueError:
            print("Invalid input. Please enter a valid value.")


async def main():
    device: BLEDevice = None
    while not device:
        devices = await BleakScanner.discover()

        for d in devices:
            if d.metadata.get("manufacturer_data", {}).get(1933, None) is None:
                continue
            device = d

        time.sleep(1)

    print(f"Found {device.name} ({device.address}), connecting...")

    async with BleakClient(device.address) as client:
        print("Are we connected?", client.is_connected)
        while not client.is_connected:
            print("Not connected, sleep")
            await asyncio.sleep(0.1)

        listeners = asyncio.create_task(initiate_listeners(client))
        interaction = asyncio.create_task(initiate_interaction(client))
        done, _ = await asyncio.wait([listeners, interaction],
                                     return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            if task.exception():
                print(f"Task {task} raised an exception: {task.exception()}")

asyncio.run(main())
