import contextlib
import json
import logging
from dataclasses import asdict

import asyncclick as click
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


def get_bounds_from(message):
    return json.loads(message)['data']


async def handle_empty_message(ws):
    try:
        answer = {'msgType': 'Errors', 'errors': ['Requires valid JSON']}
        await ws.send_message(json.dumps(answer))
    except ConnectionClosed:
        pass


async def handle_wrong_message(ws):
    try:
        answer = {'msgType': 'Errors', 'errors': ['Requires msgType specified']}
        await ws.send_message(json.dumps(answer))
    except ConnectionClosed:
        pass


async def listen_browser(ws, bounds):
    while True:
        try:
            message = await ws.get_message()
            new_bounds = get_bounds_from(message)
            bounds.update(new_bounds)
        except ConnectionClosed:
            break
        except json.JSONDecodeError as exc:
            logger.error(exc)
            await handle_empty_message(ws)
        except KeyError as exc:
            logger.error(exc)
            await handle_wrong_message(ws)


async def handle_browser(request, buses):
    ws = await request.accept()
    bounds = WindowBounds()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws, bounds)
        nursery.start_soon(send_bus_data, ws, buses, bounds)


'''
bus_port - порт для имитатора автобусов
browser_port - порт для браузера
v — настройка логирования
'''
@click.command()
@click.option('--bus_port', default=8080, help='Порт для имитатора автобусов')
@click.option('--browser_port', default=8000, help='Порт для браузера')
@click.option('-v', default=DEBUG_LEVEL, help='Порт для браузера')
async def main(**kwargs):
    bus_port = kwargs['bus_port']
    browser_port = kwargs['browser_port']
    loglevel = kwargs['v']
    logger.setLevel(getattr(logging, loglevel.upper()))
    format_str = '%(levelname)s:%(filename)s:[%(asctime)s] %(message)s'
    formatter = logging.Formatter(format_str)
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    buses = {}

    def bus_get_data_handler(request): return recieve_bus_data(request, buses)

    def bus_get_data_server():
        return serve_websocket(bus_get_data_handler, '127.0.0.1',
                               bus_port, ssl_context=None)

    def bus_send_data_handler(request): return handle_browser(request, buses)

    def bus_send_data_server():
        return serve_websocket(bus_send_data_handler, '127.0.0.1',
                               browser_port, ssl_context=None)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(bus_get_data_server)
        nursery.start_soon(bus_send_data_server)

    
if __name__ == '__main__':
    with contextlib.suppress(KeyboardInterrupt):
        main(_anyio_backend='trio')
