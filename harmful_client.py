import logging
import trio
from constants import DEBUG_LEVEL
from trio_websocket import open_websocket_url


async def send_message(message):
    try:
        async with open_websocket_url('ws://localhost:8000') as ws:
            logging.info('Request: %s', message)
            if message is not None:
                await ws.send_message(message)
            answer = await ws.get_message()
            logging.info('Response: %s', answer)
            return answer
    except OSError as ose:
        logging.error('Connection attempt failed: %s', ose)


def test_empty_message():
    pass


if __name__ == '__main__':
    logging.basicConfig(
        format='%(levelname)s:%(filename)s:[%(asctime)s] %(message)s',
        level=getattr(logging, DEBUG_LEVEL.upper()),
    )
    messages = [
        None,
        '',
        '{}',
        '{"this": ["is valid JSON"], "but": "wrong keys"}'
    ]
    while True:
        if len(messages):
            message = messages.pop()
        else:
            # message = None
            break
        trio.run(send_message, message)
