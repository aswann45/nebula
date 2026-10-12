"""Shared CLI options, service execution, and safe error reporting."""

import asyncio
import contextlib
import sys
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from nebula import Nebula
from nebula.collection.models import CollectionResult
from nebula.core.exceptions import (
    ConfigurationError,
    DataValidationError,
    ParsingError,
    RequestError,
    StorageError,
)
from nebula.storage.filesystem import FilesystemStorage

from .output import OutputFormat, render, write_output

FormatOption = Annotated[
    OutputFormat, typer.Option("--format", "-f", help="Output format.")
]
OutputOption = Annotated[
    str | None,
    typer.Option("--output", "-o", help="Output file or directory."),
]
OverwriteOption = Annotated[
    bool, typer.Option("--overwrite", help="Replace an existing output file.")
]
QuietOption = Annotated[
    bool, typer.Option("--quiet", help="Hide progress and diagnostics.")
]
VerboseOption = Annotated[
    bool, typer.Option("--verbose", help="Show diagnostic context.")
]


def create_nebula() -> Nebula:
    """Create a facade; tests may replace this factory."""
    return Nebula()


def execute(
    operation: Callable[[Nebula], Awaitable[Any]],
    *,
    output_format: OutputFormat,
    output: str | None,
    overwrite: bool,
    quiet: bool,
    verbose: bool,
    default_stem: str,
    missing_message: str | None = None,
    progress_label: str | None = None,
) -> None:
    """Run a service operation and render or persist its result."""
    try:
        result = asyncio.run(_run_operation(operation, progress_label, quiet))
        if result is None and missing_message is not None:
            typer.echo(missing_message, err=True)
            raise typer.Exit(code=4)
        content = render(result, output_format)
        _display(
            content, output, output_format, overwrite, quiet, default_stem
        )
    except typer.Exit:
        raise
    except (
        ConfigurationError,
        ValidationError,
        RequestError,
        ParsingError,
        DataValidationError,
        StorageError,
    ) as exc:
        _handle_error(exc, verbose)


def execute_collection(
    operation: Callable[[Nebula], Awaitable[CollectionResult]],
    *,
    output_format: OutputFormat,
    output: str | None,
    storage: FilesystemStorage | None,
    export_path: str | None,
    overwrite: bool,
    resume: bool,
    quiet: bool,
    verbose: bool,
    default_stem: str,
) -> None:
    """Render records or export persisted ones, preserving partial work."""
    try:
        result = asyncio.run(
            _run_operation(operation, "Collecting resources", quiet)
        )
        if storage is not None and export_path is not None:
            path = storage.export(
                export_path,
                format=output_format.value,
                overwrite=overwrite or resume,
            )
            if not quiet:
                typer.echo(f"Wrote {path}", err=True)
        else:
            _display(
                render(result.records, output_format),
                output,
                output_format,
                overwrite,
                quiet,
                default_stem,
            )
        if result.failed:
            typer.echo(
                f"{result.failed} resource(s) failed; "
                "successful records were kept",
                err=True,
            )
            raise typer.Exit(code=6)
    except typer.Exit:
        raise
    except (
        ConfigurationError,
        ValidationError,
        RequestError,
        ParsingError,
        DataValidationError,
        StorageError,
    ) as exc:
        _handle_error(exc, verbose)


async def _run_operation(
    operation: Callable[[Nebula], Awaitable[Any]],
    progress_label: str | None,
    quiet: bool,
) -> Any:
    async with create_nebula() as nebula:
        show_progress = (
            progress_label is not None and not quiet and sys.stderr.isatty()
        )
        progress_task = (
            asyncio.create_task(_progress(progress_label))
            if show_progress and progress_label is not None
            else None
        )
        try:
            return await operation(nebula)
        finally:
            if progress_task is not None:
                progress_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await progress_task
                typer.echo("\r" + " " * 60 + "\r", err=True, nl=False)


def _display(
    content: str,
    output: str | None,
    output_format: OutputFormat,
    overwrite: bool,
    quiet: bool,
    default_stem: str,
) -> None:
    if output is None:
        typer.echo(content, nl=False)
        return
    path = write_output(
        content,
        output,
        output_format=output_format,
        overwrite=overwrite,
        default_stem=default_stem,
    )
    if not quiet:
        typer.echo(f"Wrote {path}", err=True)


def _handle_error(exc: Exception, verbose: bool) -> None:
    if isinstance(exc, ValidationError):
        _fail_message("Configuration validation failed", 3, verbose)
    if isinstance(exc, ConfigurationError):
        _fail(exc, 3, verbose)
    if isinstance(exc, RequestError):
        _fail(exc, 4, verbose)
    if isinstance(exc, (ParsingError, DataValidationError)):
        _fail(exc, 5, verbose)
    _fail(exc, 7, verbose)


def _fail(exc: Exception, code: int, verbose: bool) -> None:
    """Report a known failure without printing a traceback or secrets."""
    prefix = f"{type(exc).__name__}: " if verbose else ""
    typer.echo(f"{prefix}{exc}", err=True)
    raise typer.Exit(code=code) from None


def _fail_message(message: str, code: int, verbose: bool) -> None:
    """Report a fixed message when exception details may hold secrets."""
    prefix = "ValidationError: " if verbose else ""
    typer.echo(f"{prefix}{message}", err=True)
    raise typer.Exit(code=code) from None


async def _progress(label: str) -> None:
    """Show an animated indicator only on interactive stderr."""
    marks = "|/-\\"
    index = 0
    while True:
        typer.echo(
            f"\r{label} {marks[index % len(marks)]}", err=True, nl=False
        )
        index += 1
        await asyncio.sleep(0.2)
