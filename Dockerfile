FROM ghcr.io/binkhq/python:3.9

WORKDIR /app
ADD . .

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV TZ=UTC

RUN    pipenv install --system --deploy --ignore-pipfile

ENTRYPOINT [ "linkerd-await", "--" ]
CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
                  "--access-logfile=-", "--bind=0.0.0.0:9000", "wsgi:app" ]
