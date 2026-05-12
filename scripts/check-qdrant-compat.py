#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILES = (
    ROOT / "docker-compose.yml",
    ROOT / "docker-compose.airgap.yml",
)
PYPROJECT = ROOT / "pyproject.toml"

QDRANT_IMAGE_RE = re.compile(
    r"^\s*image:\s*qdrant/qdrant:v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\s*$",
    re.MULTILINE,
)
SPEC_RE = re.compile(r"^(?P<op><=|>=|==|<|>|~=)\s*(?P<major>\d+)\.(?P<minor>\d+)(?:\.\d+)?$")


def fail(message: str) -> None:
    print(f"qdrant compatibility check failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def qdrant_server_versions() -> set[tuple[int, int, int]]:
    versions: set[tuple[int, int, int]] = set()

    for compose_file in COMPOSE_FILES:
        text = compose_file.read_text(encoding="utf-8")
        matches = list(QDRANT_IMAGE_RE.finditer(text))
        if len(matches) != 1:
            fail(
                f"{compose_file.relative_to(ROOT)} must contain exactly one pinned "
                "qdrant/qdrant:vMAJOR.MINOR.PATCH image"
            )

        match = matches[0]
        versions.add(
            (
                int(match.group("major")),
                int(match.group("minor")),
                int(match.group("patch")),
            )
        )

    if len(versions) != 1:
        rendered = ", ".join(
            f"v{major}.{minor}.{patch}" for major, minor, patch in sorted(versions)
        )
        fail(f"Compose files disagree on Qdrant server image version: {rendered}")

    return versions


def qdrant_client_requirement() -> str:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dependencies = data.get("project", {}).get("dependencies", [])
    matches = [
        dependency
        for dependency in dependencies
        if dependency.lower().startswith("qdrant-client")
    ]

    if len(matches) != 1:
        fail("pyproject.toml must contain exactly one qdrant-client dependency")

    return matches[0]


def parsed_specifiers(requirement: str) -> set[tuple[str, int, int]]:
    spec = requirement[len("qdrant-client") :].strip()
    if not spec:
        fail("qdrant-client dependency must include explicit version bounds")

    parsed: set[tuple[str, int, int]] = set()
    for raw_part in spec.split(","):
        part = raw_part.strip()
        if not part:
            continue

        match = SPEC_RE.match(part)
        if not match:
            fail(f"unsupported qdrant-client specifier {part!r} in {requirement!r}")

        parsed.add(
            (
                match.group("op"),
                int(match.group("major")),
                int(match.group("minor")),
            )
        )

    return parsed


def main() -> None:
    ((server_major, server_minor, server_patch),) = qdrant_server_versions()
    requirement = qdrant_client_requirement()
    specifiers = parsed_specifiers(requirement)

    expected_lower = (">=", server_major, server_minor)
    expected_upper = ("<", server_major, server_minor + 2)

    missing: list[str] = []
    if expected_lower not in specifiers:
        missing.append(f">={server_major}.{server_minor}")
    if expected_upper not in specifiers:
        missing.append(f"<{server_major}.{server_minor + 2}")

    if missing:
        fail(
            "qdrant-client must be bounded to the Compose server compatibility "
            f"window for qdrant/qdrant:v{server_major}.{server_minor}.{server_patch}; "
            f"expected qdrant-client{','.join(missing)}, found {requirement!r}"
        )

    print(
        "Qdrant dependency contract OK: "
        f"server qdrant/qdrant:v{server_major}.{server_minor}.{server_patch}, "
        f"client {requirement}"
    )


if __name__ == "__main__":
    main()
