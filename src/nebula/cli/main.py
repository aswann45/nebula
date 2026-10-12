"""Installable Typer entry point for supported Nebula operations."""

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated

import typer

from . import apportionments, committees, config, members, sources, votes

app = typer.Typer(
    help="Retrieve and inspect government and legislative source data.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(members.app, name="members")
app.add_typer(committees.app, name="committees")
app.add_typer(votes.app, name="votes")
app.add_typer(apportionments.app, name="apportionments")
app.add_typer(sources.app, name="sources")
app.add_typer(config.app, name="config")


def _version_callback(value: bool) -> None:
    if value:
        try:
            package_version = version("nebula")
        except PackageNotFoundError:
            project = Path(__file__).parents[3] / "pyproject.toml"
            package_version = tomllib.loads(project.read_text())["project"][
                "version"
            ]
        typer.echo(package_version)
        raise typer.Exit()


@app.callback()
def main(
    version_flag: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the installed Nebula version.",
        ),
    ] = False,
) -> None:
    """Select a command or show the installed package version."""


if __name__ == "__main__":
    app()
