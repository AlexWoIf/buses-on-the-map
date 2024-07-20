import contextlib
import json
import logging
from dataclasses import asdict
from functools import partial

import asyncclick as click
import trio
from trio_websocket import ConnectionClosed, serve_websocket

from constants import BROWSER_DELAY, DEBUG_LEVEL
from models import Bus, WindowBounds


logger = logging.getLogger(name=__name__)


async def recieve_bus_data(buses, request):
    ws = await request.accept()
    try:
        while True:
            message = await ws.get_message()
            bus = Bus(*json.loads(message).values())
            busId = bus.busId
            buses[busId] = bus
    except ConnectionClosed:
        logger.debug('Connection on bus collector port was closed')


async def send_buses(ws, buses, bounds):
    answer = {'msgType': 'Buses',
              'buses': [asdict(bus) for bus in buses.values() 
                        if bus.is_inside(bounds)], }
    if len(answer['buses']):
        logger.debug(f'Send buses: {len(answer['buses'])} bus(es)')
        await ws.send_message(json.dumps(answer))
    logger.debug(f'Delay: {BROWSER_DELAY}sec')
    await trio.sleep(BROWSER_DELAY)
    

async def send_error(ws, bounds):
    answer = {'msgType': 'Errors',
              'errors': bounds.error, }
    logger.debug(f'Send error: {bounds.error}')
    await ws.send_message(json.dumps(answer))
    logger.debug(f'Delay: 0sec')
    return
    

async def send_answer_to_browser(ws, buses, bounds):
    while True:
        if bounds.error:
            await send_error(ws, bounds)
        else:
            await send_buses(ws, buses, bounds)


def get_bounds_from(message):
    message_decoded = json.loads(message)
    if message_decoded['msgType'] != 'newBounds':
        raise KeyError('Wrong message type')
    return message_decoded['data']


async def listen_to_browser(ws, bounds):
    while True:
        message = await ws.get_message()
        logger.debug(f'{message=}')
        try:
            new_bounds = get_bounds_from(message)
            bounds.update(new_bounds)
            await ws.send_message('Message recieved')
        except json.JSONDecodeError as exc:
            logger.error(f'Decode error: {exc=}')
            bounds.error = 'Not a valid JSON provided'
        except KeyError as exc:
            logger.error(f'Key doesn\'t exist: {exc=}')
            bounds.error = f'Required key not specified {exc}'


async def handle_browser(buses, request):
    ws = await request.accept()
    bounds = WindowBounds()
    try:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(listen_to_browser, ws, bounds)
            nursery.start_soon(send_answer_to_browser, ws, buses, bounds)
    except* ConnectionClosed:
        logger.debug('Connection on browsers port was closed')


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

    bus_get_data_handler = partial(recieve_bus_data, buses)

    bus_send_data_handler = partial(handle_browser, buses)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket, bus_get_data_handler,
                           '127.0.0.1', bus_port, None)
        nursery.start_soon(serve_websocket, bus_send_data_handler,
                           '127.0.0.1', browser_port, None)

    
if __name__ == '__main__':
    with contextlib.suppress(KeyboardInterrupt):
        main(_anyio_backend='trio')
