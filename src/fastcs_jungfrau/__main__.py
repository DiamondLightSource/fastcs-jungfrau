"""Interface for ``python -m fastcs_jungfrau``."""

from pathlib import Path
from typing import Optional

import typer
from fastcs.connections import IPConnectionSettings
from fastcs.launch import FastCS
from fastcs.logging import LogLevel, configure_logging
from fastcs.transports.epics import (
    EpicsGUIOptions,
    EpicsIOCOptions,
)
from fastcs.transports.epics.ca import EpicsCATransport

from fastcs_jungfrau import __version__
from fastcs_jungfrau.controllers.jungfrau_controller import JungfrauController
from fastcs_jungfrau.controllers.jungfrau_odin_controller import JungfrauOdinController

__all__ = ["main"]

app = typer.Typer()

OPI_PATH = Path("/epics/opi")


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    # TODO: typer does not support `bool | None` yet
    # https://github.com/tiangolo/typer/issues/533
    version: Optional[bool] = typer.Option(  # noqa
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Print the version and exit",
    ),
):
    pass


@app.command()
def ioc(
    pv_prefix: str = typer.Argument(),
    config: str = typer.Option(help="Path to the config file"),
    odin_ip: str | None = typer.Option(None, help="IP address of odin control server"),
    odin_port: int = typer.Option(8888, help="Port of odin control server"),
):
    # Configure logging
    configure_logging(LogLevel.TRACE)

    ui_path = OPI_PATH if OPI_PATH.is_dir() else Path.cwd()

    if odin_ip is None:
        # Create a controller instance...
        controller = JungfrauController(config_file_path=config)
    else:
        controller = JungfrauOdinController(
            config_file_path=config,
            odin_connection_settings=IPConnectionSettings(ip=odin_ip, port=odin_port),
        )

    # ...some IOC options...
    options = EpicsCATransport(
        epicsca=EpicsIOCOptions(pv_prefix=pv_prefix),
        gui=EpicsGUIOptions(
            output_path=ui_path / "jungfrau.bob", title=f"Jungfrau - {pv_prefix}"
        ),
    )

    # ...and pass them both to FastCS
    launcher = FastCS(controller, [options])
    launcher.run()


# Run with 'python -m fastcs_jungfrau'
# (after activating the venv)
if __name__ == "__main__":
    app()
