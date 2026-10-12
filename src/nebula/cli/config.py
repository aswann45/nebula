"""Validated configuration display and checks."""

import typer

from nebula.api import Nebula
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

app = typer.Typer(help="Inspect validated Nebula configuration.")


@app.command("show")
def show(
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Show effective settings with secrets redacted."""

    async def operation(nebula: Nebula) -> dict[str, object]:
        settings = Settings()
        return {
            "http": nebula.config.model_dump(mode="json"),
            "credentials": settings.model_dump(mode="json"),
        }

    execute(
        operation,
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem="nebula-config",
    )


@app.command("validate")
def validate(
    format: FormatOption = OutputFormat.TABLE,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Validate HTTP and credential settings without making requests."""

    async def operation(nebula: Nebula) -> dict[str, bool]:
        _ = Settings()
        _ = nebula.config
        return {"valid": True}

    execute(
        operation,
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem="nebula-config-validation",
    )
