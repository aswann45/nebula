"""Source inventory and configuration status commands."""

import typer

from nebula.api import Nebula
from nebula.services.source_status import SourceStatusService
from nebula.settings import Settings

from .common import (
    FormatOption,
    OutputOption,
    OverwriteOption,
    QuietOption,
    VerboseOption,
    execute,
)
from .output import OutputFormat

app = typer.Typer(help="Inspect registered data sources.")


@app.command("list")
def list_sources(
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """List source names and supported operations without network access."""

    async def operation(nebula: Nebula) -> list[dict[str, object]]:
        registry = nebula.sources
        return [
            {"source": name, **registry.capabilities(name).model_dump()}
            for name in registry.names()
        ]

    execute(
        operation,
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem="nebula-sources",
    )


@app.command("status")
def status(
    check: bool = typer.Option(
        False, "--check", help="Perform live HTTP connectivity probes."
    ),
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Show configured availability; probe live sources only with --check."""

    async def operation(nebula: Nebula) -> object:
        service = SourceStatusService(
            nebula.sources, nebula.settings or Settings()
        )
        return await service.status(check=check)

    execute(
        operation,
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem="nebula-source-status",
    )
