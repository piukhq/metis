FROM binkhq/python:3.6

WORKDIR /app
ADD . .

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN pip install --no-cache-dir pipenv==2018.11.26 gunicorn && \
    pipenv install --system --deploy --ignore-pipfile

CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
                  "--access-logfile=-", "--bind=0.0.0.0:9000", "wsgi:app" ]
