import contextlib
import json
import logging

import trio
from trio_websocket import ConnectionClosed, serve_websocket

from constants import BROWSER_DELAY, DEBUG_LEVEL


logger = logging.getLogger(name=__name__)


def is_inside(bounds, bus):
    if not bounds:
        return False
    south_lat, north_lat, west_lng, east_lng = bounds.values()
    lat, lng, _ = bus.values()
    return south_lat < lat < north_lat and west_lng < lng < east_lng


async def recieve_bus_data(request, buses):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            bus = json.loads(message)
            busId = bus.pop('busId')
            buses[busId] = bus
        except ConnectionClosed:
            break


async def send_bus_data(ws, buses, bounds):
    while True:
        try:
            answer = {
                'msgType': 'Buses',
                'buses': [
                    {**{'busId': busId}, **bus_values}
                    for busId, bus_values in buses.items()
                    if is_inside(bounds, bus_values)
                ]
            }
            logger.debug(len(buses.values()))
            logger.debug(bounds)
            logger.debug(len(answer['buses']))
            await ws.send_message(json.dumps(answer))
            await trio.sleep(BROWSER_DELAY)
        except ConnectionClosed:
            break


async def listen_browser(ws, buses, bounds):
    while True:
        try:
            message = await ws.get_message()
            new_bounds = json.loads(message).get('data')
            for key, value in new_bounds.items():
                bounds[key] = value
            logger.info(bounds)
            bus_count = 0
            for bus_data in buses.values():
                if is_inside(bounds, bus_data):
                    bus_count += 1
            logger.info(f'Total {len(buses)} bus(es). {bus_count} bus(es) '
                        'inside the browser window')
        except ConnectionClosed:
            break


async def handle_browser(request, buses, bounds):
    ws = await request.accept()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws, buses, bounds)
        nursery.start_soon(send_bus_data, ws, buses, bounds)


async def main():
    loglevel = DEBUG_LEVEL
    logger.setLevel(getattr(logging, loglevel.upper()))
    format_str = '%(levelname)s:%(filename)s:[%(asctime)s] %(message)s'
    formatter = logging.Formatter(format_str)
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    buses = {}
    bounds = {}
    bus_get_data_handler = lambda request: recieve_bus_data(request, buses)
    bus_get_data_server = lambda: serve_websocket(bus_get_data_handler, '127.0.0.1', 8080, ssl_context=None)
    bus_send_data_handler = lambda request: handle_browser(request, buses, bounds)
    bus_send_data_server = lambda: serve_websocket(bus_send_data_handler, '127.0.0.1', 8000, ssl_context=None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(bus_get_data_server)
        nursery.start_soon(bus_send_data_server)


def test_is_inside():
    bounds = {'south_lat': 55.77966236981707, 'north_lat': 55.82317686868505, 'west_lng': 37.45831489562989, 'east_lng': 37.56071090698243}
    bus = {'lat': 55.809727230415, 'lng': 37.462571818793, 'route': '100'}
    assert is_inside(bounds, bus['lat'], bus['lng'])

    
if __name__ == '__main__':
    with contextlib.suppress(KeyboardInterrupt):
        trio.run(main)
