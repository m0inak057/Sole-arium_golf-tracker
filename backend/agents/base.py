"""Shared Gemini client and JSON-only contract for all agents.

Common infrastructure:
- Builds the Gemini client from ``GEMINI_API_KEY``.
- Enforces JSON-only output via strict system prompts.
- Parses the response; on parse failure retries once with a
  stricter prompt; on second failure marks the session ``failed``
  with reason ``agent_{n}_malformed_output``.
- Logs every prompt + response with ``session_id``.

See agent-prompts.md "Shared implementation rules" and rules.md §4.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from backend.core.config import Settings, get_settings
from backend.core.logging import get_logger, log_event

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    """Abstract base for all 5 pipeline agents.

    Subclasses implement ``agent_number``, ``system_prompt``,
    ``build_user_prompt``, and ``response_model``.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: Any = None  # Lazy-init to avoid import at module level

    @property
    @abstractmethod
    def agent_number(self) -> int:
        """Return the agent number (1–5)."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt enforcing JSON-only output."""
        ...

    @property
    @abstractmethod
    def response_model(self) -> type[BaseModel]:
        """Return the Pydantic model for the expected JSON response."""
        ...

    @property
    def temperature(self) -> float:
        """Return the temperature for this agent.

        Returns:
            0.2 for agents 1–4 (deterministic), 0.5 for agent 5 (expressive).
        """
        return 0.5 if self.agent_number == 5 else 0.2

    @property
    def max_tokens(self) -> int:
        """Return the max token limit for this agent.

        Returns:
            2000 for agent 5, 800 for agents 1–4.
        """
        return 2000 if self.agent_number == 5 else 800

    def _get_client(self) -> Any:
        """Lazily initialise the Gemini client.

        Returns:
            A ``google.genai.Client`` instance.
        """
        if self._client is None:
            try:
                from google import genai
                if not self._settings.gemini_api_key:
                    raise RuntimeError("GEMINI_API_KEY is missing or empty.")
                self._client = genai.Client(api_key=self._settings.gemini_api_key)
            except ImportError as exc:
                raise RuntimeError(
                    "google-genai package is required. Install with: pip install google-genai"
                ) from exc
        return self._client

    @abstractmethod
    def build_user_prompt(self, session_data: dict[str, Any]) -> str:
        """Assemble the user prompt from session data.

        Args:
            session_data: Relevant fields from the session JSON.

        Returns:
            The user prompt string.
        """
        ...

    async def run(
        self,
        session_data: dict[str, Any],
        session_id: str,
        agents_dir: Path,
    ) -> dict[str, Any]:
        """Execute the agent: prompt → parse → retry if needed → return JSON.

        Args:
            session_data: Relevant fields from the session JSON.
            session_id: For logging and debug file persistence.
            agents_dir: Where to persist raw prompt/response for debugging.

        Returns:
            Parsed JSON dict matching the agent's response schema.

        Raises:
            AgentMalformedOutputError: After two failed parse attempts.
        """
        user_prompt = self.build_user_prompt(session_data)
        client = self._get_client()

        # Persist prompt for debugging
        prompt_file = agents_dir / f"agent{self.agent_number}.prompt.txt"
        prompt_file.write_text(
            f"=== SYSTEM ===\n{self.system_prompt}\n\n=== USER ===\n{user_prompt}",
            encoding="utf-8",
        )

        log_event(
            logger,
            f"Agent {self.agent_number} calling Gemini",
            session_id=session_id,
            agent=f"agent{self.agent_number}",
            event="agent_call_started",
        )

        # First attempt
        raw_response = self._call_api(client, user_prompt)
        response_file = agents_dir / f"agent{self.agent_number}.response.txt"
        response_file.write_text(raw_response or "", encoding="utf-8")

        parsed = self._try_parse(raw_response)
        if parsed is not None:
            return parsed

        # Retry with stricter prompt
        log_event(
            logger,
            f"Agent {self.agent_number} malformed output — retrying",
            session_id=session_id,
            agent=f"agent{self.agent_number}",
            event="agent_retry",
        )

        retry_prompt = (
            user_prompt
            + "\n\nReturn ONLY a JSON object matching the schema. No prose, no markdown."
        )
        raw_response = self._call_api(client, retry_prompt)
        response_file_retry = agents_dir / f"agent{self.agent_number}.response_retry.txt"
        response_file_retry.write_text(raw_response or "", encoding="utf-8")

        parsed = self._try_parse(raw_response)
        if parsed is not None:
            return parsed

        raise AgentMalformedOutputError(self.agent_number)

    def _call_api(self, client: Any, user_prompt: str) -> str:
        """Make a synchronous Gemini API call.

        Args:
            client: Gemini client instance.
            user_prompt: The assembled user prompt.

        Returns:
            Raw response text.
        """
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=self.temperature,
        )
        response = client.models.generate_content(
            model=self._settings.gemini_model,
            contents=user_prompt,
            config=config,
        )
        if response.candidates:
            finish_reason = getattr(response.candidates[0], "finish_reason", "UNKNOWN")
            log_event(logger, f"Gemini finish_reason: {finish_reason}")
            if hasattr(response.candidates[0], "safety_ratings"):
                log_event(logger, f"Gemini safety_ratings: {response.candidates[0].safety_ratings}")
        return response.text or ""

    def _try_parse(self, raw: str) -> dict[str, Any] | None:
        """Attempt to parse the raw response as JSON.

        Args:
            raw: Raw response string from the API.

        Returns:
            Parsed dict if valid JSON, else ``None``.
        """
        try:
            # Clean up markdown fences just in case
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.endswith("```"):
                raw = raw[:-3]
            
            data = json.loads(raw.strip())
            # Validate against the Pydantic model
            self.response_model.model_validate(data)
            return data
        except Exception as e:
            logger.error(f"JSON Decode Error or Model Validation Error: {e}")
            return None


class AgentMalformedOutputError(Exception):
    """Raised when an agent fails to produce valid JSON after retry."""

    def __init__(self, agent_number: int) -> None:
        self.agent_number = agent_number
        self.failure_reason = f"agent{agent_number}_malformed_output"
        super().__init__(f"Agent {agent_number} produced malformed output after retry.")
