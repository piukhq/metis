FROM ghcr.io/binkhq/python:3.11-poetry as build
WORKDIR /src
ADD . .
RUN poetry build

FROM ghcr.io/binkhq/python:3.11 as main
ARG PIP_INDEX_URL=https://269fdc63-af3d-4eca-8101-8bddc22d6f14:b694b5b1-f97e-49e4-959e-f3c202e3ab91@pypi.gb.bink.com/simple
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
