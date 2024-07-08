import json
import os
import random
import trio
from sys import stderr
from trio_websocket import open_websocket_url


LAT = 55.7476
LNG = 37.6415
ROUTES_FOLDER = 'routes/'
SEND_BUS_URL = 'ws://127.0.0.1:8080'
TICK = 1


async def generate_position(busId, route):
    return json.dumps({
        'busId': busId,
        'lat': LAT+random.uniform(0.0, 0.00019),
        'lng': LNG+random.uniform(0.0, 0.0009),
        'route': route
    })


async def run_bus(route, coordinates, url=SEND_BUS_URL):
    async with open_websocket_url(url) as ws:
        for lat, lng in coordinates:
            message = {
                'busId': f'{route}-0', 'lat': lat, 'lng': lng, 'route': route,
            }
            await ws.send_message(json.dumps(message, ensure_ascii=False))
            await trio.sleep(TICK)


def load_routes(folder=ROUTES_FOLDER):
    files = os.listdir(folder)
    for file_name in files:
        file_path = os.path.join(folder, file_name)
        with open(file_path, 'r') as file:
            route = json.load(file)
            yield route['name'], route['coordinates']


async def main():
    async with trio.open_nursery() as nursery:
        for route, coordinates in load_routes():
            try:
                nursery.start_soon(run_bus, route, coordinates, SEND_BUS_URL)
            except OSError as ose:
                print('Connection attempt failed: %s' % ose, file=stderr)


if __name__ == '__main__':
    trio.run(main)