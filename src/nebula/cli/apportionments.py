"""OMB apportionment commands backed by ApportionmentService."""

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

app = typer.Typer(help="Discover and retrieve OMB apportionments.")


@app.command("list")
def list_apportionments(
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """List OMB JSON resources in the published index."""
    execute(
        lambda nebula: nebula.apportionments.list(),
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem="omb-apportionments-index",
    )


@app.command("get")
def get(
    url: Annotated[str, typer.Argument(help="JSON resource URL or path.")],
    format: FormatOption = OutputFormat.JSON,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Retrieve one OMB apportionment by JSON resource URL."""
    execute(
        lambda nebula: nebula.apportionments.get(url),
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem="omb-apportionment",
        missing_message="OMB apportionment was not found",
    )


@app.command("collect")
def collect(
    fiscal_year: Annotated[
        int | None, typer.Option("--fiscal-year", min=1900)
    ] = None,
    format: FormatOption = OutputFormat.JSONL,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Download OMB records, optionally keeping one fiscal year."""
    stem = (
        f"omb-apportionments-{fiscal_year}"
        if fiscal_year is not None
        else "omb-apportionments"
    )
    execute(
        lambda nebula: nebula.apportionments.collect(fiscal_year),
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem=stem,
        progress_label="Retrieving OMB apportionments",
    )
