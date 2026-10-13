"""Congress.gov bill and amendment activity commands."""

from pathlib import Path
from typing import Annotated

import typer

from nebula import Nebula
from nebula.collection.checkpoints import FileCheckpointStore
from nebula.congress_gov.legislation_models import (
    CongressAction,
    CongressAmendment,
)
from nebula.storage.filesystem import FilesystemStorage

from .common import (
    FormatOption,
    OutputOption,
    OverwriteOption,
    QuietOption,
    VerboseOption,
    execute,
    execute_collection,
)
from .output import OutputFormat

app = typer.Typer(help="Retrieve Congress.gov bill and amendment activity.")


@app.command("bill")
def bill(
    congress: Annotated[int, typer.Argument(min=1)],
    bill_type: str,
    bill_number: Annotated[int, typer.Argument(min=1)],
    format: FormatOption = OutputFormat.JSON,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Retrieve one full bill record."""
    execute(
        lambda nebula: nebula.legislation.bill(
            congress, bill_type, bill_number
        ),
        output_format=format,
        output=output,
        overwrite=overwrite,
        quiet=quiet,
        verbose=verbose,
        default_stem=f"bill-{congress}-{bill_type}-{bill_number}",
        missing_message="Congress.gov bill was not found",
    )


@app.command("collect-bills")
def collect_bills(
    congress: Annotated[int, typer.Argument(min=1)],
    bill_type: str,
    page_size: Annotated[
        int, typer.Option("--page-size", min=1, max=250)
    ] = 250,
    format: FormatOption = OutputFormat.JSONL,
    output: OutputOption = None,
    overwrite: OverwriteOption = False,
    quiet: QuietOption = False,
    verbose: VerboseOption = False,
    resume: bool = typer.Option(
        False, "--resume", help="Resume a checkpoint."
    ),
    checkpoint: str | None = typer.Option(
        None, "--checkpoint", help="Checkpoint JSON path."
    ),
    preserve_raw: bool = typer.Option(
        False, "--preserve-raw", help="Store source response bytes."
    ),
) -> None:
    """Collect all bills of one type in a Congress."""
    stem = f"congress-bills-{congress}-{bill_type.lower()}"
    persistent = output is not None and format in {
        OutputFormat.JSON,
        OutputFormat.JSONL,
    }
    if (resume or checkpoint or preserve_raw) and not persistent:
        raise typer.BadParameter(
            "--resume, --checkpoint, and --preserve-raw require "
            "--output with JSON or JSONL format"
        )
    storage: FilesystemStorage | None = None
    checkpoint_store: FileCheckpointStore | None = None
    export_path: str | None = None
    if persistent and output is not None:
        destination = Path(output).expanduser()
        export = (
            destination / f"{stem}.{format.value}"
            if output.endswith("/") or destination.is_dir()
            else destination
        )
        storage = FilesystemStorage(
            export.parent / f".{export.stem}-collection"
        )
        checkpoint_store = FileCheckpointStore(
            checkpoint or storage.directory / "checkpoint.json"
        )
        export_path = str(export)
    execute_collection(
        lambda nebula: nebula.legislation.collect_bills_result(
            congress,
            bill_type,
            page_size=page_size,
            storage=storage,
            checkpoint_store=checkpoint_store,
            resume=resume,
            overwrite=overwrite,
            preserve_raw=preserve_raw,
            retain_records=not persistent,
        ),
        output_format=format,
        output=output,
        storage=storage,
        export_path=export_path,
        overwrite=overwrite,
        resume=resume,
        quiet=quiet,
        verbose=verbose,
        default_stem=stem,
    )


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
