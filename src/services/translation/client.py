"""LibreTranslate HTTP client with timeout, retry, and fallback."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class LibreTranslateClient:
    """Self-hosted LibreTranslate client with graceful fallback.

    On any network or server error the original text is returned unchanged
    so that ingestion never blocks on translation.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def translate(
        self,
        text: str,
        source_lang: str | None,
        target_lang: str = "en",
    ) -> str:
        """Translate *text* from *source_lang* to *target_lang*.

        Returns the original text when translation fails or when *text* is empty.
        """
        if not text.strip():
            return text

        payload = {
            "q": text,
            "source": source_lang if source_lang is not None else "auto",
            "target": target_lang,
        }

        try:
            response = self._client.post(
                f"{self._base_url}/translate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return str(data["translatedText"])
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.warning("Translation failed (%s), returning original", exc)
            return text
        except (ValueError, KeyError) as exc:
            logger.warning("Translation response malformed (%s), returning original", exc)
            return text

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()
