FROM python:3.6-alpine

WORKDIR /app
ADD . .

RUN apk add --no-cache --virtual build \
      build-base \
      libxslt-dev \
      openssh \
      git && \
    apk add --no-cache \
      binutils \
      libc-dev \
      libxslt \
      postgresql-dev && \
    mkdir -p /root/.ssh && mv /app/deploy_key /root/.ssh/id_rsa && \
    chmod 0600 /root/.ssh/id_rsa && \
    ssh-keyscan gitlab.com > /root/.ssh/known_hosts && \
    pip install gunicorn pipenv && pipenv install --system --deploy --ignore-pipfile && \
    apk del --no-cache build && \
