import contextlib
import json
import logging
import os
import random
from functools import wraps
from itertools import cycle, islice
from sys import stderr

import asyncclick as click
import trio
from trio_websocket import ConnectionClosed, HandshakeError, open_websocket_url

from constants import (DEBUG_LEVEL, EMULATOR_DELAY, NUM_BUSES, NUM_CHANNELS,
                       ROUTES_FOLDER, SEND_BUS_URL)


logger = logging.getLogger(name=__name__)


def retry(handler):
    @wraps(handler)
    async def _wrapper(*args, **kwargs):
        retry = 0
        while True:
            try:
                logger.debug('Try handler')
                await handler(*args, **kwargs)
                logger.debug('Handler finished')
                retry = 0
                break
            except* (HandshakeError, ConnectionClosed) as exc_group:
                logger.error(f'Error {type(exc_group)}. Sleeping {retry}sec(s)')
                await trio.sleep(retry)
                retry = (retry + 1) * 2 if retry < 10 else 10
    return _wrapper


@retry
async def send_updates(receive_channel, server_address):
    async with open_websocket_url(server_address) as ws:
        while  True:
            async for message in receive_channel:
                await ws.send_message(message)

    
async def run_bus(busId, route, coordinates, send_channel, refresh_timeout):
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
            await trio.sleep(refresh_timeout)


def load_routes(buses_per_route, routes_number=0, emulator_id='',
                folder=ROUTES_FOLDER):
    files = os.listdir(folder)
    for file_count, file_name in enumerate(files):
        if routes_number > 0 and routes_number == file_count:
            break
        file_path = os.path.join(folder, file_name)
        with open(file_path, 'r') as file:
            route = json.load(file)
            for counter in range(buses_per_route):
                busId = f'{route["name"]}-{counter}'
                yield busId, route['name'], route['coordinates']

'''
- `server` - адрес сервера
- `routes_number` — количество маршрутов
- `buses_per_route` — количество автобусов на каждом маршруте
- `websockets_number` — количество открытых веб-сокетов
- `emulator_id` — префикс к busId на случай запуска нескольких экземпляров имитатора
- `refresh_timeout` — задержка в обновлении координат сервера
- `v` — настройка логирования
'''

@click.command()
@click.option('--server', default=SEND_BUS_URL, help='Адрес сервера.')
@click.option('--routes_number', default=0, help='Количество маршрутов.')
@click.option('--buses_per_route', default=NUM_BUSES, help='Количество '
              'автобусов на каждом маршруте.')
@click.option('--websockets_number', default=NUM_CHANNELS, help='Количество '
              'открытых веб-сокетов.')
@click.option('--emulator_id', default='', help='Префикс к busId на случай '
              'запуска нескольких экземпляров имитатора')
@click.option('--refresh_timeout', default=EMULATOR_DELAY, help='Задержка в '
              'обновлении координат сервера')
@click.option('--v', default=DEBUG_LEVEL, help='Уровень логгирования')
async def main(**kwargs):
    websockets_number = kwargs['websockets_number']
    server = kwargs['server']
    buses_per_route = kwargs['buses_per_route']
    refresh_timeout = kwargs['refresh_timeout']
    routes_number = kwargs['routes_number']
    emulator_id = kwargs['emulator_id']
    loglevel = kwargs['v']

    logger.setLevel(getattr(logging, loglevel.upper()))
    format_str = '%(levelname)s:%(filename)s:[%(asctime)s] %(message)s'
    formatter = logging.Formatter(format_str)
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    logger.debug(kwargs)

    async with trio.open_nursery() as nursery:
        send_channels = []
        for _ in range(websockets_number):
            send_channel, receive_channel = trio.open_memory_channel(0)
            send_channels.append(send_channel)
            try:
                nursery.start_soon(send_updates, receive_channel, server)
            except OSError as ose:
                print('Connection attempt failed: %s' % ose, file=stderr)
        for busId, route, coordinates in load_routes(buses_per_route,
                                                     routes_number,
                                                     emulator_id):
            send_channel = random.choices(send_channels)[0]
            nursery.start_soon(run_bus, busId, route, coordinates,
                               send_channel, refresh_timeout)



if __name__ == '__main__':
    with contextlib.suppress(KeyboardInterrupt):
        main(_anyio_backend='trio')