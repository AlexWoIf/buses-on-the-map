FROM python:3.12-slim-bookworm

WORKDIR /usr/src/app

RUN --mount=type=bind,source=./requirements.txt,target=/tmp/requirements.txt \
    pip install --no-cache-dir --requirement /tmp/requirements.txt
COPY routes .
COPY *.py .

CMD ["python", "server.py"]