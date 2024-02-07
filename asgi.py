import uvicorn

from metis import create_app
from metis.settings import settings

app = create_app()


if __name__ == "__main__":
    uvicorn.run("asgi:app", host=settings.DEV_HOST, port=settings.DEV_PORT, reload=settings.METIS_DEBUG)
