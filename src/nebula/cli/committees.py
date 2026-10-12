"""Committee retrieval commands backed by CommitteeService."""

import typer

from .common import (
    FormatOption,
    OutputOption,
    OverwriteOption,
    QuietOption,
    VerboseOption,
    execute,
)
from .output import OutputFormat

app = typer.Typer(help="Retrieve congressional committees.")


def _current(
    format: OutputFormat,
    output: str | None,
    overwrite: bool,
    quiet: bool,
    verbose: bool,
) -> None:
    execute(
        lambda nebula: nebula.committees.current(),
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem="committees-current",
    )


@app.command("list")
def list_committees(
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """List current committees from the GitHub dataset."""
    _current(format, output, overwrite, quiet, verbose)


@app.command("current")
def current(
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Retrieve current committees from the GitHub dataset."""
    _current(format, output, overwrite, quiet, verbose)
