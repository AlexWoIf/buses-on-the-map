import json
import trio
from trio_websocket import serve_websocket, ConnectionClosed


TICK = 0.5


async def recieve_bus_data(request, buses):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            bus = json.loads(message)
            busId = bus.pop('busId')
            buses[busId] = bus
            print(f'Total {len(buses)} buses')
        except ConnectionClosed:
            break


async def send_bus_data(request, buses):
    ws = await request.accept()
    while True:
        try:
            answer = {
                'msgType': 'Buses',
                'buses': [
                    {**{'busId': busId}, **bus_values}
                    for busId, bus_values in buses.items()
                ]
            }
            # print(answer)
            await ws.send_message(json.dumps(answer))
            await trio.sleep(TICK)
        except ConnectionClosed:
            break


async def main():
    buses = {}
    bus_get_data_handler = lambda request: recieve_bus_data(request, buses)
    bus_get_data_server = lambda: serve_websocket(bus_get_data_handler, '127.0.0.1', 8080, ssl_context=None)
    bus_send_data_handler = lambda request: send_bus_data(request, buses)
    bus_send_data_server = lambda: serve_websocket(bus_send_data_handler, '127.0.0.1', 8000, ssl_context=None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(bus_get_data_server)
        nursery.start_soon(bus_send_data_server)


if __name__ == '__main__':
    trio.run(main)
