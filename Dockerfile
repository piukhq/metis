FROM python:3.6

WORKDIR /app
ADD . .

RUN mkdir -p /root/.ssh && mv /app/deploy_key /root/.ssh/id_rsa && \
    chmod 0600 /root/.ssh/id_rsa && \
    ssh-keyscan gitlab.com > /root/.ssh/known_hosts && \
    pip install uwsgi pipenv && pipenv install --system --deploy --ignore-pipfile && \
    rm -rf /root/.ssh
