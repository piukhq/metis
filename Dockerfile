FROM ghcr.io/binkhq/python:3.11-poetry as build
WORKDIR /src
ADD . .
RUN poetry build

FROM ghcr.io/binkhq/python:3.11 as main
WORKDIR /app
COPY --from=build /src/dist/*.whl .
COPY --from=build /src/wsgi.py .
COPY --from=build /src/visa_handback_files ./visa_handback_files

RUN export wheel=$(find -type f -name "*.whl") && \
    pip install "$wheel" && \
    rm $wheel

ENTRYPOINT [ "linkerd-await", "--" ]
CMD [ "gunicorn", "--error-logfile=-", "--access-logfile=-", \
                  "--logger-class=metis.reporting.CustomGunicornLogger", \
                  "--bind=0.0.0.0:9000", "wsgi:app" ]
