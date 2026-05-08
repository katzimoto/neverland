from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from services.translation.client import LibreTranslateClient

TEST_URL = "http://localhost:5000"


def test_translate_success() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"translatedText": "Hello world"}

    with patch("httpx.Client.post", return_value=mock_response):
        result = client.translate("Hola mundo", source_lang="es")

    assert result == "Hello world"


def test_translate_auto_detect() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"translatedText": "Hello world"}

    with patch("httpx.Client.post", return_value=mock_response):
        result = client.translate("Hola mundo", source_lang=None)

    assert result == "Hello world"


def test_translate_timeout_fallback() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("timeout")):
        result = client.translate("Hola mundo", source_lang="es")

    assert result == "Hola mundo"


def test_translate_5xx_fallback() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=mock_response
    )

    with patch("httpx.Client.post", return_value=mock_response):
        result = client.translate("Hola mundo", source_lang="es")

    assert result == "Hola mundo"


def test_translate_invalid_json_fallback() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("invalid json")

    with patch("httpx.Client.post", return_value=mock_response):
        result = client.translate("Hola mundo", source_lang="es")

    assert result == "Hola mundo"


def test_translate_empty_text() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)

    result = client.translate("", source_lang="es")

    assert result == ""


def test_translate_whitespace_only() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)

    result = client.translate("   ", source_lang="es")

    assert result == "   "


def test_client_close() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)
    with patch.object(client._client, "close") as mock_close:
        client.close()
        mock_close.assert_called_once()
