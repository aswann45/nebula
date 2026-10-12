"""Storage contracts and filesystem-backed collection persistence."""

from .base import RecordStorage
from .filesystem import FilesystemStorage

__all__ = ["FilesystemStorage", "RecordStorage"]
