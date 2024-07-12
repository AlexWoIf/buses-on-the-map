import contextlib
import json
import logging
from dataclasses import asdict

import trio
from trio_websocket import ConnectionClosed, serve_websocket

from constants import BROWSER_DELAY, DEBUG_LEVEL
from models import Bus, WindowBounds


logger = logging.getLogger(name=__name__)


async def recieve_bus_data(request, buses):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            bus = Bus(*json.loads(message).values())
            busId = bus.busId
            buses[busId] = bus
        except ConnectionClosed:
            break


async def send_bus_data(ws, buses, bounds):
    while True:
        try:
            answer = {
                'msgType': 'Buses',
                'buses': [
                    asdict(bus) for bus in buses.values()
                    if bus.is_inside(bounds)
                ]
            }
            await ws.send_message(json.dumps(answer))
            await trio.sleep(BROWSER_DELAY)
        except ConnectionClosed:
            break


async def listen_browser(ws, bounds):
    while True:
        try:
            message = await ws.get_message()
            new_bounds = json.loads(message).get('data')
            bounds.update(new_bounds)
        except ConnectionClosed:
            break


async def handle_browser(request, buses):
    ws = await request.accept()
    bounds = WindowBounds()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws, bounds)
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
    bus_get_data_handler = lambda request: recieve_bus_data(request, buses)
    bus_get_data_server = lambda: serve_websocket(bus_get_data_handler, '127.0.0.1', 8080, ssl_context=None)
    bus_send_data_handler = lambda request: handle_browser(request, buses)
    bus_send_data_server = lambda: serve_websocket(bus_send_data_handler, '127.0.0.1', 8000, ssl_context=None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(bus_get_data_server)
        nursery.start_soon(bus_send_data_server)

    
if __name__ == '__main__':
    with contextlib.suppress(KeyboardInterrupt):
        trio.run(main)
