from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from services.connectors.folder import FolderConnector


def test_folder_connector_logs_file_read_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unreadable = tmp_path / "unreadable.txt"
    unreadable.write_text("content")
    original_read_bytes = Path.read_bytes

    def fake_read_bytes(path: Path) -> bytes:
        if path == unreadable:
            raise OSError("permission denied")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)

    with (
        patch("services.connectors.folder.logger") as mock_logger,
        pytest.raises(OSError, match="permission denied"),
    ):
        list(FolderConnector(str(tmp_path)).fetch_documents())

    mock_logger.exception.assert_called_once()
    call_args = mock_logger.exception.call_args
    message = call_args[0][0]
    assert "Folder connector failed to read file" in message
    assert str(unreadable) in message
    assert str(tmp_path) in message
