"""SMB / Windows file share connector."""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import tempfile
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import PurePosixPath
from typing import Any

import smbclient  # type: ignore[import-untyped]

from services.connectors.base import ConnectorDocument, ConnectorField

_CHUNK_SIZE = 1024 * 1024
_DEFAULT_RECURSIVE = True
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _RemoteFile:
    """SMB file candidate metadata."""

    remote_path: str
    unc_path: str
    size: int | None
    mtime: float | None


class SmbConnector:
    """List and download documents from an SMB share using service-account credentials."""

    label = "Smb"

    @classmethod
    def fields(cls) -> list[ConnectorField]:
        """Return SMB connector configuration fields."""
        return [
            ConnectorField(key="server", label="Server", placeholder="fileserver.local"),
            ConnectorField(key="share", label="Share", placeholder="department"),
            ConnectorField(
                key="base_path",
                label="Base path",
                required=False,
                placeholder="/legal/contracts",
            ),
            ConnectorField(key="domain", label="Domain", required=False, placeholder="CORP"),
            ConnectorField(key="username", label="Username"),
            ConnectorField(key="password", label="Password", sensitive=True),
            ConnectorField(
                key="recursive",
                label="Recursive",
                required=False,
                placeholder="true",
            ),
            ConnectorField(
                key="include_globs",
                label="Include globs",
                required=False,
                placeholder="**/*.pdf,**/*.docx",
            ),
            ConnectorField(
                key="exclude_globs",
                label="Exclude globs",
                required=False,
                placeholder="**/~$*,**/node_modules/**",
            ),
            ConnectorField(
                key="max_file_size_mb",
                label="Max file size (MB)",
                required=False,
                placeholder="100",
            ),
            ConnectorField(
                key="acl_sync_enabled",
                label="NTFS ACL sync enabled",
                required=False,
                placeholder="false",
            ),
        ]

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._server = str(config.get("server", "")).strip()
        self._share = str(config.get("share", "")).strip().strip("\\/")
        self._base_path = _normalise_remote_path(str(config.get("base_path", "")))
        self._domain = str(config.get("domain", "")).strip() or None
        self._username = str(config.get("username", "")).strip()
        self._password = str(config.get("password", ""))
        self._recursive = _parse_bool(str(config.get("recursive", "true")))
        self._include_globs = _parse_globs(config.get("include_globs"))
        self._exclude_globs = _parse_globs(config.get("exclude_globs"))
        self._max_file_size_bytes = self._parse_max_size(config.get("max_file_size_mb"))
        self._acl_sync_enabled = _parse_bool(str(config.get("acl_sync_enabled", "false"))) is True

    def validate(self) -> None:
        """Raise ``ValueError`` when required SMB configuration is missing or invalid."""
        missing = [
            key
            for key, value in {
                "server": self._server,
                "share": self._share,
                "username": self._username,
                "password": self._password,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"SMB connector requires {', '.join(missing)}")
        if self._recursive is None:
            raise ValueError("SMB connector recursive must be 'true' or 'false'")

    def fetch_documents(self) -> Iterator[ConnectorDocument]:
        """Yield SMB files as downloaded local temporary documents."""
        self.validate()
        try:
            smbclient.register_session(
                self._server,
                username=self._username,
                password=self._password,
                domain=self._domain,
            )
        except Exception as exc:
            raise self._sanitised_error("authenticate", exc) from exc

        try:
            for remote_file in self._list_files():
                if not self._matches_globs(remote_file.remote_path):
                    continue
                if (
                    remote_file.size is not None
                    and self._max_file_size_bytes is not None
                    and remote_file.size > self._max_file_size_bytes
                ):
                    continue
                yield self._download(remote_file)
        finally:
            with suppress(Exception):
                smbclient.close_session(self._server)

    def _list_files(self) -> Iterator[_RemoteFile]:
        base_unc = self._unc_path(self._base_path)
        yield from self._scan_directory(base_unc, self._base_path)

    def _scan_directory(self, unc_path: str, relative_dir: str) -> Iterator[_RemoteFile]:
        try:
            entries = smbclient.scandir(unc_path)
        except Exception as exc:
            raise self._sanitised_error("list files", exc) from exc

        try:
            for entry in entries:
                name = str(getattr(entry, "name", ""))
                if not name:
                    continue
                remote_path = _join_remote(relative_dir, name)
                try:
                    is_dir = bool(entry.is_dir())
                except Exception as exc:
                    raise self._sanitised_error("inspect file", exc) from exc
                if is_dir:
                    if self._recursive is True:
                        yield from self._scan_directory(self._unc_path(remote_path), remote_path)
                    continue
                stat = _entry_stat(entry)
                yield _RemoteFile(
                    remote_path=remote_path,
                    unc_path=self._unc_path(remote_path),
                    size=_stat_int(stat, "st_size"),
                    mtime=_stat_float(stat, "st_mtime"),
                )
        except ValueError:
            raise
        except Exception as exc:
            raise self._sanitised_error("list files", exc) from exc
        finally:
            close = getattr(entries, "close", None)
            if callable(close):
                close()

    def _matches_globs(self, remote_path: str) -> bool:
        name = PurePosixPath(remote_path).name
        if self._include_globs and not any(
            _glob_matches(remote_path, name, pattern) for pattern in self._include_globs
        ):
            return False
        return not any(_glob_matches(remote_path, name, pattern) for pattern in self._exclude_globs)

    def _download(self, remote_file: _RemoteFile) -> ConnectorDocument:
        title = PurePosixPath(remote_file.remote_path).name
        suffix = PurePosixPath(title).suffix
        digest = hashlib.sha256()
        try:
            with (
                smbclient.open_file(remote_file.unc_path, mode="rb") as source,
                tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as target,
            ):
                while True:
                    chunk = source.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    digest.update(chunk)
                    target.write(chunk)
                local_path = target.name
        except Exception as exc:
            raise self._sanitised_error("download file", exc) from exc

        mime_type, _ = mimetypes.guess_type(title)
        if mime_type is None:
            mime_type = "application/octet-stream"

        metadata: dict[str, Any] = {
            "server": self._server,
            "share": self._share,
            "remote_path": remote_file.remote_path,
            "size": remote_file.size,
            "mtime": remote_file.mtime,
        }
        if self._acl_sync_enabled:
            metadata["acl_data"] = self._read_acl(remote_file.unc_path)

        return ConnectorDocument(
            external_id=self._external_id(remote_file.remote_path),
            title=title,
            mime_type=mime_type,
            sha256=digest.hexdigest(),
            source_language=None,
            path=local_path,
            metadata=metadata,
        )

    def _read_acl(self, unc_path: str) -> list[dict[str, Any]] | None:
        """Return sanitized allow/deny ACE metadata or ``None`` on any ACL failure.

        The high-level ``smbclient`` API does not expose NTFS security descriptors
        directly. This method attempts the lower-level security-descriptor path
        when the installed ``smbprotocol`` build supports it, but never raises or
        logs raw paths, SIDs, credentials, or ACE payloads.
        """
        try:
            return self._query_acl(unc_path)
        except Exception as exc:
            logger.warning("SMB ACL read failed (%s)", type(exc).__name__)
            return None

    def _query_acl(self, unc_path: str) -> list[dict[str, Any]]:
        """Query and normalize a file security descriptor.

        This implementation intentionally accepts multiple smbprotocol object
        shapes so unit tests can monkeypatch deterministic descriptors without a
        live SMB server. Unsupported descriptor shapes raise ``ValueError`` so
        callers fail closed.
        """
        try:
            from smbprotocol.security_descriptor import AceType  # type: ignore[import-untyped]
        except Exception as exc:  # pragma: no cover - dependency capability guard
            raise ValueError("acl_support_unavailable") from exc

        query_security_descriptor = getattr(smbclient, "query_security_descriptor", None)
        if not callable(query_security_descriptor):
            raise ValueError("acl_query_unavailable")

        descriptor = query_security_descriptor(unc_path)
        entries = getattr(descriptor, "dacl", None)
        aces = getattr(entries, "aces", entries)
        if aces is None:
            raise ValueError("acl_dacl_missing")

        normalized: list[dict[str, Any]] = []
        for ace in aces:
            ace_type = getattr(ace, "ace_type", getattr(ace, "type", None))
            if ace_type in {getattr(AceType, "ACCESS_ALLOWED_ACE_TYPE", object()), "allow", 0}:
                normalized_type = "allow"
            elif ace_type in {getattr(AceType, "ACCESS_DENIED_ACE_TYPE", object()), "deny", 1}:
                normalized_type = "deny"
            else:
                raise ValueError("acl_ace_type_unsupported")
            sid = getattr(ace, "sid", None)
            if sid is None:
                sid_text = ""
            elif hasattr(sid, "to_str"):
                sid_text = sid.to_str()
            else:
                sid_text = str(sid)
            if not sid_text:
                raise ValueError("acl_sid_missing")
            access_mask = getattr(ace, "mask", getattr(ace, "access_mask", 0))
            normalized.append(
                {"type": normalized_type, "sid": sid_text, "access_mask": int(access_mask)}
            )
        return normalized

    def _unc_path(self, remote_path: str) -> str:
        base = f"\\\\{self._server}\\{self._share}"
        if not remote_path:
            return base
        unc_remote_path = remote_path.replace("/", "\\")
        return f"{base}\\{unc_remote_path}"

    def _external_id(self, remote_path: str) -> str:
        if not remote_path:
            return f"smb://{self._server}/{self._share}"
        return f"smb://{self._server}/{self._share}/{remote_path}"

    def _sanitised_error(self, action: str, exc: Exception) -> ValueError:
        return ValueError(
            f"SMB {action} failed for smb://{self._server}/{self._share} ({type(exc).__name__})"
        )

    @staticmethod
    def _parse_max_size(raw_value: Any) -> int | None:
        if raw_value is None or str(raw_value).strip() == "":
            return None
        try:
            megabytes = int(str(raw_value).strip())
        except ValueError as exc:
            raise ValueError("SMB connector max_file_size_mb must be an integer") from exc
        if megabytes < 0:
            raise ValueError("SMB connector max_file_size_mb must be non-negative")
        return megabytes * 1024 * 1024


def _parse_bool(raw_value: str) -> bool | None:
    value = raw_value.strip().lower()
    if value == "":
        return _DEFAULT_RECURSIVE
    if value in {"true", "1", "yes", "y", "on"}:
        return True
    if value in {"false", "0", "no", "n", "off"}:
        return False
    return None


def _parse_globs(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []
    return [pattern.strip() for pattern in str(raw_value).split(",") if pattern.strip()]


def _normalise_remote_path(raw_path: str) -> str:
    return raw_path.strip().replace("\\", "/").strip("/")


def _join_remote(parent: str, name: str) -> str:
    clean_name = _normalise_remote_path(name)
    if not parent:
        return clean_name
    return f"{parent}/{clean_name}"


def _entry_stat(entry: Any) -> Any:
    stat = getattr(entry, "stat", None)
    if callable(stat):
        return stat()
    return stat


def _stat_int(stat: Any, field: str) -> int | None:
    value = getattr(stat, field, None)
    return int(value) if value is not None else None


def _stat_float(stat: Any, field: str) -> float | None:
    value = getattr(stat, field, None)
    return float(value) if value is not None else None


def _glob_matches(remote_path: str, name: str, pattern: str) -> bool:
    if fnmatch(remote_path, pattern) or fnmatch(name, pattern):
        return True
    if pattern.startswith("**/"):
        return fnmatch(remote_path, pattern[3:]) or fnmatch(name, pattern[3:])
    return False
