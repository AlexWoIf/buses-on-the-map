import json
import trio
from trio_websocket import serve_websocket, ConnectionClosed

import constants

async def echo_server(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            print(message)
            # for lat, lng in constants.bus156['coordinates']:
            #     answer = {
            #                 'msgType': 'Buses',
            #                 'buses': [
            #                     {
            #                         'busId': 'е262ва',
            #                         'lat': lat,
            #                         'lng': lng,
            #                         'route': '156'
            #                     }
            #                 ]
            #     }
            #     await ws.send_message(json.dumps(answer))
            #     await trio.sleep(0.5)

        except ConnectionClosed:
            break

async def main():
    await serve_websocket(echo_server, '127.0.0.1', 8080, ssl_context=None)


if __name__ == '__main__':
    trio.run(main)
