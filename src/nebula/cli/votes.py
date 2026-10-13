"""House voting commands backed by VoteService."""

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


@app.command("collect-house")
def collect_house(
    year: Annotated[int, typer.Option("--year", min=1935)],
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
    """Collect a House voting year with optional persistence and resume."""
    stem = f"house-votes-{year}"
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
        lambda nebula: nebula.votes.house_year_result(
            year,
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
