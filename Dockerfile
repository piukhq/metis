FROM ghcr.io/binkhq/python:3.11-pipenv

WORKDIR /app
ADD . .

RUN pipenv install --system --deploy --ignore-pipfile

ENTRYPOINT [ "linkerd-await", "--" ]
CMD [ "gunicorn", "--error-logfile=-", "--access-logfile=-", \
                  "--logger-class=app.reporting.CustomGunicornLogger", \
                  "--bind=0.0.0.0:9000", "wsgi:app" ]
