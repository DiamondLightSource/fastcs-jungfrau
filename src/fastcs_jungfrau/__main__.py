"""Interface for ``python -m fastcs_jungfrau``."""

from pathlib import Path
from typing import Optional

import typer
from fastcs.launch import FastCS
from fastcs.transport.epics.ca.options import EpicsCAOptions
from fastcs.transport.epics.options import (
    EpicsGUIOptions,
    EpicsIOCOptions,
)
from softioc import device

# from slsdet import Jungfrau
from fastcs_jungfrau import __version__
from fastcs_jungfrau.jungfrau_controller import JungfrauController

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
):
    # fastcs does not pass blocking=True when it builds records for AttrW/AttrRW,
    # only for commands, so a caput to a setting completes as soon as the record
    # processes - before the handler has written to the detector. A client that
    # writes settings and then triggers a command can have the command reach the
    # detector first. Set softioc's global default so the write records are
    # created with PACT set and the put callback waits for the handler.
    # Must happen before any record is created. Fixed upstream in fastcs 0.12.
    device.SetBlocking(True)

    ui_path = OPI_PATH if OPI_PATH.is_dir() else Path.cwd()

    # Create a controller instance...
    controller = JungfrauController(config_file_path=config)

    # ...some IOC options...
    options = EpicsCAOptions(
        ca_ioc=EpicsIOCOptions(pv_prefix=pv_prefix),
        gui=EpicsGUIOptions(
            output_path=ui_path / "jungfrau.bob", title=f"Jungfrau - {pv_prefix}"
        ),
    )

    # ...and pass them both to FastCS
    launcher = FastCS(controller, [options])
    launcher.create_docs()
    launcher.create_gui()
    launcher.run()


# Run with 'python -m fastcs_jungfrau'
# (after activating the venv)
if __name__ == "__main__":
    app()
