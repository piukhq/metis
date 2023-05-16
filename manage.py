#!/usr/bin/env python
import os

from typer import Typer

import settings
from wsgi import app

try:
    import IPython
    import pytest
except Exception:
    print(
        "These command are meant to be used in a dev environment and requires the dev packages to be intalled. \n"
        "Please run pipenv sync --dev to install the required libraries."
    )
    exit(-1)


app.config.SWAGGER_UI_DOC_EXPANSION = "list"


cli = Typer(no_args_is_help=True)


@cli.command()
def runserver() -> None:
    """Run dev server"""
    # python decouple will load the env instead
    app.run(host=settings.DEV_HOST, port=settings.DEV_PORT, debug=settings.DEBUG, load_dotenv=False)


@cli.command()
def shell() -> None:
    """opens an ipython shell"""
    IPython.embed()


@cli.command()
def test() -> int:
    """Run the tests in app/tests/unit/."""
    HERE = os.path.abspath(os.path.dirname(__file__))
    UNIT_TEST_PATH = os.path.join(HERE, "app", "tests", "unit")

    return pytest.main([UNIT_TEST_PATH, "--verbose"])


if __name__ == "__main__":
    cli()
