FROM ghcr.io/binkhq/python:3.11-poetry as build
WORKDIR /src
ADD . .
RUN poetry build

FROM ghcr.io/binkhq/python:3.11 as main
ARG PIP_INDEX_URL
WORKDIR /app
COPY --from=build /src/dist/*.whl .
COPY --from=build /src/wsgi.py .

RUN export wheel=$(find -type f -name "*.whl") && \
    pip install "$wheel" && \
    rm $wheel

ENTRYPOINT [ "linkerd-await", "--" ]
CMD [ "gunicorn", "--error-logfile=-", "--access-logfile=-", \
                  "--logger-class=metis.reporting.CustomGunicornLogger", \
                  "--bind=0.0.0.0:9000", "wsgi:app" ]
