from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error, request


class OllamaError(RuntimeError):
    pass


@dataclass(slots=True)
class OllamaSettings:
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model: str = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))


class OllamaClient:
    def __init__(self, settings: OllamaSettings | None = None) -> None:
        self.settings = settings or OllamaSettings()

    def generate_json(self, prompt: str) -> dict:
        payload = {
            "model": self.settings.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.settings.temperature,
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
        return self._get("/api/version")

    def _post(self, path: str, payload: dict) -> dict:
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
                "Failed to reach Ollama. Confirm the Ollama server is running and accessible."
            ) from exc
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned invalid JSON from its HTTP API.") from exc

    def _get(self, path: str) -> dict:
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
                "Failed to reach Ollama. Confirm the Ollama server is running and accessible."
            ) from exc
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned invalid JSON from its HTTP API.") from exc
