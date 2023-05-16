#!/usr/bin/env python
import os
import sys

from loguru import logger

from metis import settings
from wsgi import app

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


app.config.SWAGGER_UI_DOC_EXPANSION = "list"


cli = Typer(no_args_is_help=True)


@cli.command()
def runserver() -> None:
    """Run dev server"""
    # python decouple will load the env instead
    app.run(host=settings.DEV_HOST, port=settings.DEV_PORT, debug=settings.DEBUG, load_dotenv=False)


@cli.command()
def shell() -> None:
    """Run an ipython shell with Flask App context"""
    context = app.make_shell_context()
    IPython.embed(header=f"User namespace initialised with {context}\n", user_ns=context, colors="neutral")


@cli.command()
def test() -> int:
    """Run the tests in app/tests/unit/."""

    return pytest.main(
        [
            os.path.join(os.path.abspath(os.path.dirname(__file__)), "tests", "unit"),
            "--verbose",
        ]
    )


if __name__ == "__main__":
    cli()
