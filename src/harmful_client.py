import logging
import trio
from constants import DEBUG_LEVEL
from trio_websocket import open_websocket_url


logger = logging.getLogger(name=__name__)


async def send_message(message):
    try:
        async with open_websocket_url('ws://localhost:8000') as ws:
            logger.info('Request: %s', message)
            await ws.send_message(str(message))
            answer = await ws.get_message()
            logger.info('Response: %s', answer)
    except OSError as ose:
        logger.error('Connection attempt failed: %s', ose)


if __name__ == '__main__':
    logger.setLevel(getattr(logging, DEBUG_LEVEL.upper()))
    format_str = '%(levelname)s:%(filename)s:[%(asctime)s] %(message)s'
    formatter = logging.Formatter(format_str)
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    logger.debug('Start logging')

    messages = [
        '{}',
        '{"this": ["is valid JSON"], "but": "wrong keys"}',
        'test',
        '{"msgType": "newBounds", "data": {"1": 37.54440307617188} }',
        '{"msgType": "test", "data": {"2": 37.61} }',
        '{"msgType": "test", "data": {"3": 53.72628839374007} }',
    ]
    for message in messages:
        trio.run(send_message, message)
