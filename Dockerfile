FROM ghcr.io/binkhq/python:3.11 as build

WORKDIR /src
ADD . .

ENV VENV /app/venv
ARG AZURE_DEVOPS_PAT
ENV VIRTUAL_ENV=$VENV
ENV PATH=$VENV/bin:$PATH

RUN pip install poetry==1.7.1
RUN poetry config http-basic.azure jeff $AZURE_DEVOPS_PAT
RUN python -m venv $VENV
RUN poetry install --without=dev --no-root
RUN poetry build
RUN pip install dist/*.whl

FROM ghcr.io/binkhq/python:3.11 as main

WORKDIR /app
ENV VENV /app/venv
ENV PATH="$VENV/bin:$PATH"
COPY --from=build $VENV $VENV
COPY --from=build /src/asgi.py .

ENTRYPOINT [ "linkerd-await", "--" ]
CMD [ "gunicorn", "--error-logfile=-", "--access-logfile=-", \
                  "--worker-class=uvicorn.workers.UvicornWorker", \
                  "--logger-class=metis.reporting.CustomGunicornLogger", \
                  "--bind=0.0.0.0:9000", "asgi:app" ]
