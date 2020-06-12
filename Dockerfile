FROM python:3.6-alpine

WORKDIR /app
ADD . .
ARG DEPLOY_KEY

RUN apk add --no-cache --virtual build \
      build-base \
      libxslt-dev \
      openssh \
      git && \
    apk add --no-cache \
      libxslt \
      postgresql-dev && \
    mkdir -p /root/.ssh && \
    echo $DEPLOY_KEY | base64 -d > /root/.ssh/id_rsa && \
    chmod 0600 /root/.ssh/id_rsa && \
    ssh-keyscan git.bink.com > /root/.ssh/known_hosts && \
    pip install gunicorn pipenv && pipenv install --system --deploy --ignore-pipfile && \
    apk del --no-cache build

CMD ["/usr/local/bin/gunicorn", "-c", "gunicorn.py", "wsgi:app"]
