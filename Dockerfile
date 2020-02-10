FROM python:3.8.1-buster

WORKDIR /app

# install global packages
RUN apt update -y && \
  apt install -y curl && \
  curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python && \
  /root/.poetry/bin/poetry config virtualenvs.create false

# install project dependencies
ARG installargs
COPY ./poetry.lock ./pyproject.toml /app/
RUN /root/.poetry/bin/poetry install -n $installargs

COPY . /app/
