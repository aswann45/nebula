"""Congress.gov bill and amendment activity commands."""

from typing import Annotated

import typer

from nebula import Nebula
from nebula.congress_gov.legislation_models import (
    CongressAction,
    CongressAmendment,
)

from .common import (
    FormatOption,
    OutputOption,
    OverwriteOption,
    QuietOption,
    VerboseOption,
    execute,
)
from .output import OutputFormat

app = typer.Typer(help="Retrieve Congress.gov bill and amendment activity.")


@app.command("bill-actions")
def bill_actions(
    congress: Annotated[int, typer.Argument(min=1)],
    bill_type: str,
    bill_number: Annotated[int, typer.Argument(min=1)],
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    limit: Annotated[int, typer.Option("--limit", min=1, max=250)] = 250,
    format: FormatOption = OutputFormat.JSON,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Retrieve one page of a bill's actions."""

    async def operation(nebula: Nebula) -> list[CongressAction]:
        page = await nebula.legislation.bill_actions(
            congress, bill_type, bill_number, offset=offset, limit=limit
        )
        return page.actions

    execute(
        operation,
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem=f"bill-{congress}-{bill_type}-{bill_number}-actions",
    )


@app.command("bill-amendments")
def bill_amendments(
    congress: Annotated[int, typer.Argument(min=1)],
    bill_type: str,
    bill_number: Annotated[int, typer.Argument(min=1)],
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    limit: Annotated[int, typer.Option("--limit", min=1, max=250)] = 250,
    format: FormatOption = OutputFormat.JSON,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Retrieve one page of amendments to a bill."""

    async def operation(nebula: Nebula) -> list[CongressAmendment]:
        page = await nebula.legislation.bill_amendments(
            congress, bill_type, bill_number, offset=offset, limit=limit
        )
        return page.amendments

    execute(
        operation,
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem=f"bill-{congress}-{bill_type}-{bill_number}-amendments",
    )


@app.command("amendment-actions")
def amendment_actions(
    congress: Annotated[int, typer.Argument(min=1)],
    amendment_type: str,
    amendment_number: Annotated[int, typer.Argument(min=1)],
    offset: Annotated[int, typer.Option("--offset", min=0)] = 0,
    limit: Annotated[int, typer.Option("--limit", min=1, max=250)] = 250,
    format: FormatOption = OutputFormat.JSON,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Retrieve one page of an amendment's actions."""

    async def operation(nebula: Nebula) -> list[CongressAction]:
        page = await nebula.legislation.amendment_actions(
            congress,
            amendment_type,
            amendment_number,
            offset=offset,
            limit=limit,
        )
        return page.actions

    execute(
        operation,
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem=(
            f"amendment-{congress}-{amendment_type}-{amendment_number}-actions"
        ),
    )
