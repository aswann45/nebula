"""Member retrieval commands backed by MemberService."""

from typing import Annotated, Literal

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

app = typer.Typer(help="Retrieve congressional member records.")


@app.command("get")
def get(
    bioguide_id: str,
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Retrieve one member by Bioguide ID from Congress.gov."""
    execute(
        lambda nebula: nebula.members.get(bioguide_id),
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem=f"member-{bioguide_id}",
    )


@app.command("list")
def list_members(
    chamber: Annotated[
        Literal["house", "senate"] | None,
        typer.Option("--chamber", help="Limit to one chamber."),
    ] = None,
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """List current legislators from the GitHub dataset."""
    execute(
        lambda nebula: nebula.members.list(chamber=chamber),
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem="members-current",
    )


@app.command("historical")
def historical(
    year: Annotated[int, typer.Option("--year", min=1789)],
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """List historical members serving through a minimum year."""
    execute(
        lambda nebula: nebula.members.historical(year),
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem=f"members-historical-{year}",
    )


@app.command("house-current")
def house_current(
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Retrieve the current House Clerk roster."""
    execute(
        lambda nebula: nebula.members.house_current(),
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem="members-house-current",
    )


@app.command("senate-current")
def senate_current(
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Retrieve the current Senate Clerk roster."""
    execute(
        lambda nebula: nebula.members.senate_current(),
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem="members-senate-current",
    )
