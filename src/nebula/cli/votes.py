"""House voting commands backed by VoteService."""

from typing import Annotated

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

app = typer.Typer(help="Retrieve House roll-call votes.")


@app.command("house")
def house(
    year: Annotated[int, typer.Option("--year", min=1789)],
    roll_call: Annotated[
        int | None,
        typer.Option("--roll-call", min=1, help="One roll-call number."),
    ] = None,
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Retrieve one House vote or all listed votes for a year."""
    operation = (
        (lambda nebula: nebula.votes.house(year, roll_call))
        if roll_call is not None
        else (lambda nebula: nebula.votes.house_year(year))
    )
    execute(
        operation,
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem=f"house-votes-{year}",
        missing_message="House roll call was not found",
        progress_label="Retrieving House votes" if roll_call is None else None,
    )
