"""
ollama_client.py  —  Ollama HTTP client for local LLM inference
================================================================
Provides a thin wrapper around Ollama's REST API (generate, chat, version).
Supports two dedicated Mac machines:
  - Mac 1 (172.16.40.120): gpt-oss model for summarisation
  - Mac 2 (172.16.40.122): deepseek-r1:8b model for quiz generation

Cross-references:
  - ai_service.py instantiates two OllamaClient instances (one for each Mac).
  - pptx_service.py uses OllamaClient for per-slide summarisation.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error, request


class OllamaError(RuntimeError):
    """Raised when Ollama API calls fail (network, empty response, or bad JSON)."""
    pass


# ── Settings dataclasses ──────────────────────────────────────────────────────

@dataclass(slots=True)
class OllamaSettings:
    """Default single-machine settings (falls back to env vars).

    Used as a base when no dedicated machine is configured.
    """
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model: str = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
    num_predict: int = int(os.getenv("OLLAMA_NUM_PREDICT", "1200"))


@dataclass(slots=True)
class SummaryOllamaSettings:
    """Mac 1 (172.16.40.120) — gpt-oss, handles summarisation & analysis."""
    base_url: str = os.getenv("SUMMARY_OLLAMA_URL", "http://172.16.40.120:11434").rstrip("/")
    model: str = os.getenv("SUMMARY_MODEL", "gpt-oss:120b-cloud")
    timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
    num_predict: int = int(os.getenv("SUMMARY_NUM_PREDICT", os.getenv("OLLAMA_NUM_PREDICT", "900")))


@dataclass(slots=True)
class QuizOllamaSettings:
    """Mac 2 (172.16.40.122) — deepseek-r1:8b, handles quiz generation (faster for structured output)."""
    base_url: str = os.getenv("QUIZ_OLLAMA_URL", "http://172.16.40.122:11434").rstrip("/")
    model: str = os.getenv("QUIZ_MODEL", "deepseek-r1:8b")
    timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))
    temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
    num_predict: int = int(os.getenv("QUIZ_NUM_PREDICT", os.getenv("OLLAMA_NUM_PREDICT", "1400")))


# ── HTTP Client ────────────────────────────────────────────────────────────────

class OllamaClient:
    """Low-level HTTP client for Ollama's /api/generate and /api/version endpoints.

    Each instance targets a specific Ollama server (model + URL).
    The two dedicated instances are:
      - client (summary/analysis) → gpt-oss on Mac 1
      - quiz_client (quiz gen)    → deepseek on Mac 2
    """

    def __init__(self, settings: OllamaSettings | SummaryOllamaSettings | QuizOllamaSettings | None = None) -> None:
        """Initialise with a settings object. Falls back to OllamaSettings (localhost)."""
        self.settings = settings or OllamaSettings()

    def generate_json(self, prompt: str) -> dict:
        """Send a prompt to Ollama and parse the response as a JSON object.

        The request uses format="json" and think=False so that reasoning
        models skip chain-of-thought and return a structured JSON payload.

        Args:
            prompt: The full prompt string for the model.

        Returns:
            A parsed JSON dict from the model response.

        Raises:
            OllamaError: If the response is empty, not valid JSON, or not a dict.
        """
        payload = {
            "model": self.settings.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "think": False,
            "options": {
                "temperature": self.settings.temperature,
                "num_predict": 4096,
                "num_ctx": 8192,
            },
        }
        raw = self._post("/api/generate", payload)
        response_text = raw.get("response", "").strip()
        if not response_text:
            raise OllamaError("Ollama returned an empty response payload.")
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned invalid JSON content.") from exc
        if not isinstance(parsed, dict):
            raise OllamaError("Ollama JSON response must be an object.")
        return parsed

    def health(self) -> dict:
        """Check Ollama server health by hitting the /api/version endpoint."""
        return self._get("/api/version")

    def _post(self, path: str, payload: dict) -> dict:
        """Send an HTTP POST to Ollama and parse the JSON response.

        Args:
            path:    API path (e.g. "/api/generate").
            payload: JSON-serialisable dict sent as the request body.

        Returns:
            Parsed JSON response dict.

        Raises:
            OllamaError: On network failure or malformed JSON from the server.
        """
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.settings.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.settings.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise OllamaError(
                f"Failed to reach Ollama at {self.settings.base_url}. "
                "Confirm the Ollama server is running with OLLAMA_HOST=0.0.0.0."
            ) from exc
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned invalid JSON from its HTTP API.") from exc

    def _get(self, path: str) -> dict:
        """Send an HTTP GET to Ollama and parse the JSON response.

        Used primarily for health checks (/api/version).

        Args:
            path: API path (e.g. "/api/version").

        Returns:
            Parsed JSON response dict.
        """
        req = request.Request(
            f"{self.settings.base_url}{path}",
            headers={"Content-Type": "application/json"},
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=self.settings.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise OllamaError(
                f"Failed to reach Ollama at {self.settings.base_url}. "
                "Confirm the Ollama server is running with OLLAMA_HOST=0.0.0.0."
            ) from exc
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned invalid JSON from its HTTP API.") from exc


def _repair_truncated_json(text: str) -> str:
    """Attempt to repair truncated JSON by closing open braces, brackets, and strings.

    Some Ollama responses get cut off mid-JSON (e.g. due to token limits).
    This function appends the minimal closing characters needed to produce
    valid JSON, then removes trailing commas before closing brackets.

    Args:
        text: Potentially truncated JSON string from the model.

    Returns:
        Repaired JSON string that should parse without error.
    """
    text = text.rstrip()
    stack = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()
    if in_string:
        text += '"'
    for opener in reversed(stack):
        text += "}" if opener == "{" else "]"
    import re
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text