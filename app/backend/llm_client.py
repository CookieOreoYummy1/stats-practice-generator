import os
import time
from uuid import uuid4

from groq import APIError, APITimeoutError, AuthenticationError, Groq, RateLimitError
from pydantic import BaseModel, ValidationError

from .models import Problem, ProblemRequest
from .prompts import SYSTEM_PROMPT, generation_prompt


class GenerationError(Exception):
    """Safe, user-facing generation failure."""


class _ProblemBatch(BaseModel):
    problems: list[Problem]


class LLMClient:
    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key or api_key == "your_key_here":
            raise RuntimeError("Set GROQ_API_KEY in the environment or .env before starting the backend.")
        self.model = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile").strip()
        if not self.model:
            raise RuntimeError("MODEL_NAME must not be blank.")
        self.client = Groq(api_key=api_key, timeout=30.0, max_retries=0)

    def verify_credentials(self) -> None:
        """Check authentication at startup without generating a completion."""
        try:
            self.client.models.list()
        except AuthenticationError as exc:
            raise RuntimeError("GROQ_API_KEY is invalid; update it before starting the backend.") from exc
        except APIError as exc:
            raise RuntimeError("Could not verify Groq credentials; check connectivity and try again.") from exc

    def close(self) -> None:
        self.client.close()

    def _complete(self, messages: list[dict[str, str]]):
        timeout_retries = 0
        rate_retries = 0
        while True:
            try:
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
            except APITimeoutError as exc:
                if timeout_retries == 1:
                    raise GenerationError("Problem generation timed out. Please try again.") from exc
                timeout_retries += 1
                time.sleep(0.5)
            except RateLimitError as exc:
                if rate_retries == 2:
                    raise GenerationError("Too many requests right now — wait a moment and try again.") from exc
                time.sleep(2 ** (rate_retries + 1))
                rate_retries += 1
            except APIError as exc:
                raise GenerationError("Could not generate problems. Please try again.") from exc

    def generate_problems(self, request: ProblemRequest) -> list[Problem]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": generation_prompt(request)},
        ]
        for attempt in range(2):
            completion = self._complete(messages)
            content = completion.choices[0].message.content if completion.choices else None
            try:
                batch = _ProblemBatch.model_validate_json(content or "")
                if len(batch.problems) != request.count:
                    raise ValueError(f"Expected exactly {request.count} problems.")
                if any(p.topic != request.topic or p.difficulty != request.difficulty for p in batch.problems):
                    raise ValueError("Every problem must use the requested topic and difficulty.")
            except (ValidationError, ValueError) as exc:
                if attempt == 1:
                    raise GenerationError("The model returned invalid problems twice. Please try again.") from exc
                messages.extend([
                    {"role": "assistant", "content": content or ""},
                    {"role": "user", "content": f"Your last response did not match the schema or request because: {exc}. Try again with the complete JSON object."},
                ])
                continue
            # Own IDs server-side so repeated model IDs cannot overwrite cached answers.
            return [p.model_copy(update={"id": str(uuid4())}) for p in batch.problems]
        raise AssertionError("Unreachable")
