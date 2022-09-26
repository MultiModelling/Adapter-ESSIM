FROM python:3.10-slim

ENV ENV=prod
ENV FLASK_APP=tno/mmvib_registry/main.py

RUN apt-get update && apt-get install -y curl git

# Install Python dependencies.
COPY requirements.txt /code/

WORKDIR /code
# To avoid warning from flask dotenv.
RUN touch .env
RUN pip install --no-cache-dir -r requirements.txt

# Only now copy the code into the container. Everything before this will be cached
# even with code changes.
COPY . /code

RUN pip install -e .
