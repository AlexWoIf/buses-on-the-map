import json
import os
import random
import trio
from itertools import islice, cycle
from sys import stderr
from trio_websocket import open_websocket_url


LAT = 55.7476
LNG = 37.6415
ROUTES_FOLDER = 'routes/'
SEND_BUS_URL = 'ws://127.0.0.1:8080'
TICK = 0.1
NUM_BUSES = 40
NUM_CHANNELS = 40

async def send_updates(receive_channel, server_address=SEND_BUS_URL):
    async with open_websocket_url(server_address) as ws:
        async with receive_channel:
            async for message in receive_channel:
                # print(message)
                await ws.send_message(message)
                await trio.sleep(TICK)

    
async def run_bus(busId, route, coordinates, send_channel):
    async with send_channel:
        slice = random.randrange(0, len(coordinates))
        coordinates = cycle(coordinates[slice:] + coordinates[:slice])
        for lat, lng in coordinates:
            message = {
                'busId': busId,
                'lat': lat,
                'lng': lng,
                'route': route,
            }
            await send_channel.send(json.dumps(message, ensure_ascii=False))


def load_routes(folder=ROUTES_FOLDER):
    files = os.listdir(folder)
    for file_name in files:
        file_path = os.path.join(folder, file_name)
        with open(file_path, 'r') as file:
            route = json.load(file)
            for counter in range(NUM_BUSES):
                busId = f'{route["name"]}-{counter}'
                yield busId, route['name'], route['coordinates']


async def main():
    async with trio.open_nursery() as nursery:
        send_channels = []
        for _ in range(NUM_CHANNELS):
            send_channel, receive_channel = trio.open_memory_channel(0)
            send_channels.append(send_channel)
            try:
                nursery.start_soon(send_updates, receive_channel, SEND_BUS_URL)
            except OSError as ose:
                print('Connection attempt failed: %s' % ose, file=stderr)
        for busId, route, coordinates in load_routes():
            send_channel = random.choices(send_channels)[0]
            # send_channel = send_channels[0]
            nursery.start_soon(run_bus, busId, route, coordinates, send_channel)


def test_load_routes():
    for count, (busId, route, _) in enumerate(load_routes()):
        assert busId == f'{route}-{count%NUM_BUSES}'
        if count == 30:
            break


if __name__ == '__main__':
    trio.run(main)