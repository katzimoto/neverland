"""Folder filesystem connector."""

from __future__ import annotations

import hashlib
import mimetypes
from collections.abc import Iterator
from pathlib import Path

from services.connectors.base import ConnectorDocument, ConnectorField


class FolderConnector:
    """Walk a local directory and yield one ConnectorDocument per file."""

    @classmethod
    def fields(cls) -> list[ConnectorField]:
        return [
            ConnectorField(
                key="path",
                label="Folder path",
                placeholder="/data/my-documents",
            ),
        ]

    def __init__(self, path: str) -> None:
        self._path = path
        self._folder = Path(path) if path else Path("")

    def validate(self) -> None:
        if not self._path:
            raise ValueError("Source has no path configured")
        if not self._folder.exists():
            raise ValueError(f"Source path does not exist: {self._folder}")
        if not self._folder.is_dir():
            raise ValueError(f"Source path is not a directory: {self._folder}")

    def fetch_documents(self) -> Iterator[ConnectorDocument]:
        for file_path in sorted(self._folder.rglob("*")):
            if not file_path.is_file():
                continue
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type is None:
                mime_type = "application/octet-stream"
            yield ConnectorDocument(
                external_id=f"file:{file_path}",
                title=file_path.name,
                mime_type=mime_type,
                sha256=_sha256_file(file_path),
                source_language=None,
                path=str(file_path),
            )


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return *path*'s SHA-256 digest without loading the whole file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
