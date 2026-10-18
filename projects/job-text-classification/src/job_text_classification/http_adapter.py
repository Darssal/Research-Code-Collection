"""Optional service adapter, not a retrieval/indexing implementation."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import LABELS
from .data import Record, public_prediction

PROMPT = "请判断以下虚构或已获授权的招聘文本，只输出人工智能、环保或否。招聘文本："


class HttpServiceAdapter:
    def __init__(self, url: str, api_key: str, *, timeout: float = 20, attempts: int = 3, retry_delay: float = 0.2):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("API URL must be an HTTP(S) endpoint without embedded credentials")
        if not api_key:
            raise ValueError("An API key is required")
        if timeout <= 0 or timeout > 300 or attempts < 1 or attempts > 10 or retry_delay < 0:
            raise ValueError("Use timeout in (0, 300], attempts in [1, 10], and non-negative retry_delay")
        self._url, self._api_key = url, api_key
        self.timeout, self.attempts, self.retry_delay = timeout, attempts, retry_delay

    @classmethod
    def from_environment(cls, **kwargs) -> "HttpServiceAdapter":
        url, api_key = os.getenv("JOB_CLASSIFIER_API_URL", ""), os.getenv("JOB_CLASSIFIER_API_KEY", "")
        if not url or not api_key:
            raise ValueError("HTTP mode requires JOB_CLASSIFIER_API_URL and JOB_CLASSIFIER_API_KEY")
        return cls(url, api_key, **kwargs)

    def _request(self, text: str) -> str:
        body = json.dumps({"message": PROMPT + "\n" + text, "mode": "chat"}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self._url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # Do not forward the credential if the endpoint redirects to another location.
        request.add_unredirected_header("Authorization", "Bearer " + self._api_key)
        # Default urllib TLS verification is preserved. Never log request or response bodies.
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = response.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise ValueError("Response exceeds the configured size limit")
        result = json.loads(payload.decode("utf-8"))
        if not isinstance(result, dict) or not isinstance(result.get("textResponse"), str):
            raise ValueError("Missing textResponse")
        label = result["textResponse"].split("</think>")[-1].strip()
        if label not in LABELS:
            raise ValueError("Response is outside the fixed label set")
        return label

    def classify(self, record: Record) -> dict:
        error = "request_failed"
        for attempt in range(1, self.attempts + 1):
            try:
                prediction = self._request(record.text)
                return public_prediction(record, prediction, status="ok", attempts=attempt)
            except urllib.error.HTTPError as exc:
                error = f"http_{exc.code}"
                # Authentication and other non-transient client errors should not be retried.
                if 400 <= exc.code < 500 and exc.code != 429:
                    return public_prediction(record, None, status="error", attempts=attempt, error=error)
            except (urllib.error.URLError, TimeoutError, OSError):
                error = "network_or_timeout"
            except (ValueError, UnicodeError):
                error = "invalid_response"
            if attempt < self.attempts:
                time.sleep(min(2.0, self.retry_delay * 2 ** (attempt - 1)))
        return public_prediction(record, None, status="error", attempts=self.attempts, error=error)

    def predict(self, records: list[Record], workers: int = 4) -> list[dict]:
        if not 1 <= workers <= 32:
            raise ValueError("workers must be between 1 and 32")
        # executor.map retains input order. No independent progress thread can wait forever.
        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(self.classify, records))
