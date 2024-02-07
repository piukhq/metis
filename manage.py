#!/usr/bin/env python
import os
import sys

import uvicorn
from loguru import logger

from metis.settings import settings

try:
    import IPython
    import pytest
    from typer import Typer
except Exception:
    logger.warning(
        "These commands are meant to be used in a dev environment and require the dev packages to be installed. \n"
        "Please run poetry install --sync to install the required libraries."
    )
    sys.exit(-1)


cli = Typer(no_args_is_help=True)


@cli.command()
def runserver() -> None:
    """Run dev server"""
    uvicorn.run("asgi:app", host=settings.DEV_HOST, port=settings.DEV_PORT, reload=settings.METIS_DEBUG)


@cli.command()
def shell() -> None:
    """Run an ipython shell"""
    IPython.embed(colors="neutral")


@cli.command()
def test() -> int:
    """Run the tests in app/tests/unit/."""

    return pytest.main(
        [
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "tests"),
            "--verbose",
        ]
    )


if __name__ == "__main__":
    cli()
