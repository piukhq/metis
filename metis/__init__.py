from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from metis.api.resources import auth_router, healthz_router
from metis.prometheus import init_metrics_collection
from metis.version import __version__


def create_app() -> FastAPI:
    app = FastAPI(title="Metis", version=__version__)
    app.include_router(healthz_router)
    app.include_router(auth_router)

    init_metrics_collection()

    openapi_schema = get_openapi(
        title="Metis",
        version=__version__,
        routes=app.routes,
    )
    # removes default Pydantic 422 ValidationError from OpenAPI spec for specified endpoints
    for path, method_item in openapi_schema.get("paths", {}).items():
        if any(item in path for item in ("/payment_card", "/foundation")):
            for _, param in method_item.items():
                if "422" in (responses := param.get("responses", {})):
                    del responses["422"]

    app.openapi_schema = openapi_schema
    return app
