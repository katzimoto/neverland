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


def test_translate_retries_on_timeout_then_succeeds() -> None:
    """Retry once on timeout, then succeed."""
    client = LibreTranslateClient(base_url=TEST_URL, max_retries=1)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"translatedText": "Hello world"}

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.TimeoutException("timeout")
        return mock_response

    with patch("httpx.Client.post", side_effect=side_effect):
        result = client.translate("Hola mundo", source_lang="es")

    assert result == "Hello world"
    assert call_count == 2


def test_translate_retries_on_5xx_then_falls_back() -> None:
    """Retry once on 5xx, then fallback on second failure."""
    client = LibreTranslateClient(base_url=TEST_URL, max_retries=1)
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=mock_response
    )

    with patch("httpx.Client.post", return_value=mock_response):
        result = client.translate("Hola mundo", source_lang="es")

    assert result == "Hola mundo"


def test_translate_5xx_fallback_no_retries() -> None:
    """With zero retries, fallback immediately on 5xx."""
    client = LibreTranslateClient(base_url=TEST_URL, max_retries=0)
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=mock_response
    )

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_response

    with patch("httpx.Client.post", side_effect=side_effect):
        result = client.translate("Hola mundo", source_lang="es")

    assert result == "Hola mundo"
    assert call_count == 1


def test_translate_invalid_json_fallback() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("invalid json")

    with patch("httpx.Client.post", return_value=mock_response):
        result = client.translate("Hola mundo", source_lang="es")

    assert result == "Hola mundo"


def test_translate_connection_error_fallback() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)

    with patch("httpx.Client.post", side_effect=httpx.ConnectError("connection refused")):
        result = client.translate("Hola mundo", source_lang="es")

    assert result == "Hola mundo"


def test_translate_network_error_fallback() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)

    with patch("httpx.Client.post", side_effect=httpx.NetworkError("network down")):
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


# Chinese text tests


def test_translate_chinese_success() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"translatedText": "Hello world"}

    with patch("httpx.Client.post", return_value=mock_response):
        result = client.translate("你好世界", source_lang="zh")

    assert result == "Hello world"


def test_translate_chinese_auto_detect() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"translatedText": "Hello world"}

    with patch("httpx.Client.post", return_value=mock_response):
        result = client.translate("你好世界", source_lang=None)

    assert result == "Hello world"


def test_translate_chinese_empty() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)

    result = client.translate("", source_lang="zh")

    assert result == ""


def test_translate_chinese_timeout_fallback() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("timeout")):
        result = client.translate("你好世界", source_lang="zh")

    assert result == "你好世界"


def test_translate_chinese_connection_error_fallback() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)

    with patch("httpx.Client.post", side_effect=httpx.ConnectError("connection refused")):
        result = client.translate("你好世界", source_lang="zh")

    assert result == "你好世界"


def test_translate_chinese_long_text() -> None:
    client = LibreTranslateClient(base_url=TEST_URL)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"translatedText": "Hello world"}

    long_text = "你好世界。" * 100
    with patch("httpx.Client.post", return_value=mock_response):
        result = client.translate(long_text, source_lang="zh")

    assert result == "Hello world"
