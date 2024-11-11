# syntax=docker/dockerfile:1
# REVIEW: I need to learn docker and how to test it locally.
ARG PYTHON_VERSION=3.11.6
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG UID=10001
RUN adduser --disabled-password --gecos "" --home "/home/appuser" --shell "/sbin/nologin" --uid "${UID}" appuser

RUN apt-get update && \
    apt-get install -y gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

USER appuser
RUN mkdir -p /home/appuser/.cache
WORKDIR /home/appuser

COPY requirements.txt .
RUN python -m pip install --user --no-cache-dir -r requirements.txt

COPY . .

RUN python main.py download-files

CMD ["python", "main.py", "start"]
