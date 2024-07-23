import logging
import trio
from constants import DEBUG_LEVEL, SEND_BUS_URL
from trio_websocket import open_websocket_url


logger = logging.getLogger(name=__name__)


async def send_message(message):
    try:
        async with open_websocket_url(SEND_BUS_URL) as ws:
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
        'bus',
        '{"this": ["is valid JSON"], "but": "wrong keys"}',
        'test',
        '{"busId": "c790\u0441\u0441", "lng": 37.6, "route": "120"}',
        '{"busId": "a134aa", "lat": 55.7494, "lng": 37.621}',
    ]
    for message in messages:
        trio.run(send_message, message)
