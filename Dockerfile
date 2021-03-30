FROM binkhq/python:3.9

WORKDIR /app
ADD . .

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV TZ=UTC

RUN apt-get update && apt-get -y install libxslt-dev zlib1g-dev gcc curl && \
    pip install --no-cache-dir pipenv==2018.11.26 gunicorn && \
    pipenv install --system --deploy --ignore-pipfile && \
    apt-get -y autoremove gcc && rm -rf /var/lib/apt/lists/*

ENTRYPOINT [ "/app/entrypoint.sh" ]
CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
                  "--access-logfile=-", "--bind=0.0.0.0:9000", "wsgi:app" ]
