"""OMB apportionment commands backed by ApportionmentService."""

from pathlib import Path
from typing import Annotated

import typer

from nebula.collection.checkpoints import FileCheckpointStore
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
    """Download OMB records with optional persistence and resume."""
    stem = (
        f"omb-apportionments-{fiscal_year}"
        if fiscal_year is not None
        else "omb-apportionments"
    )
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
        if output.endswith("/") or destination.is_dir():
            export = destination / f"{stem}.{format.value}"
        else:
            export = destination
        storage = FilesystemStorage(
            export.parent / f".{export.stem}-collection"
        )
        checkpoint_store = FileCheckpointStore(
            checkpoint or storage.directory / "checkpoint.json"
        )
        export_path = str(export)
    execute_collection(
        lambda nebula: nebula.apportionments.collect_result(
            fiscal_year,
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
