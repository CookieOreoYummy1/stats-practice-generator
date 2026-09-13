import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import httpx
import pytest
from groq import APITimeoutError, RateLimitError

from app.backend.llm_client import GenerationError, LLMClient
from app.backend.models import ProblemRequest


def problem_data():
    return dict(id="model-id", topic="anova", difficulty="easy",
                question="When should ANOVA be used?", hints=["Consider the number of groups."],
                solution_steps=["Compare means across three or more groups."],
                final_answer="To compare three or more population means.")


def completion(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.fixture
def llm(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    sdk = MagicMock()
    monkeypatch.setattr("app.backend.llm_client.Groq", lambda **kwargs: sdk)
    monkeypatch.setattr("app.backend.llm_client.time.sleep", lambda _: None)
    return LLMClient()


def test_batch_uses_one_call_and_server_ids(llm):
    llm.client.chat.completions.create.return_value = completion(json.dumps({"problems": [problem_data()] * 2}))
    problems = llm.generate_problems(ProblemRequest(topic="anova", difficulty="easy", count=2))
    assert len({p.id for p in problems}) == 2
    assert all(UUID(p.id).version == 4 for p in problems)
    llm.client.chat.completions.create.assert_called_once()
    kwargs = llm.client.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["model"] == "test-model"


@pytest.mark.parametrize("bad", ["not JSON", "{}", '{"problems": [{}]}',
    json.dumps({"problems": []}),
    json.dumps({"problems": [{**problem_data(), "topic": "probability_basics"}]}),
    json.dumps({"problems": [{**problem_data(), "difficulty": "hard"}]}), None])
def test_invalid_output_retried_with_feedback(llm, bad):
    create = llm.client.chat.completions.create
    create.side_effect = [completion(bad), completion(json.dumps({"problems": [problem_data()]}))]
    assert len(llm.generate_problems(ProblemRequest(topic="anova", difficulty="easy"))) == 1
    assert create.call_count == 2
    assert "because:" in create.call_args.kwargs["messages"][-1]["content"]


def test_repeated_invalid_output_fails(llm):
    llm.client.chat.completions.create.return_value = completion("bad")
    with pytest.raises(GenerationError, match="invalid problems twice"):
        llm.generate_problems(ProblemRequest(topic="anova", difficulty="easy"))
    assert llm.client.chat.completions.create.call_count == 2


@pytest.mark.parametrize("kind, attempts", [("timeout", 2), ("rate", 3)])
def test_transport_retry_limits(llm, kind, attempts):
    request = httpx.Request("POST", "https://api.groq.com")
    error = (APITimeoutError(request=request) if kind == "timeout" else
             RateLimitError("limited", response=httpx.Response(429, request=request), body=None))
    llm.client.chat.completions.create.side_effect = error
    with pytest.raises(GenerationError):
        llm.generate_problems(ProblemRequest(topic="anova", difficulty="easy"))
    assert llm.client.chat.completions.create.call_count == attempts


def test_missing_key_fails(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Set GROQ_API_KEY"):
        LLMClient()


def test_corrupted_math_triggers_regeneration(llm):
    bad = {**problem_data(), "question": r"Compute $$text{Mean}=frac{sum x_i}{n}$$."}
    good = {**problem_data(), "question": r"Compute $\text{Mean}=\frac{\sum x_i}{n}$."}
    create = llm.client.chat.completions.create
    create.side_effect = [completion(json.dumps({"problems": [bad]})), completion(json.dumps({"problems": [good]}))]
    result = llm.generate_problems(ProblemRequest(topic="anova", difficulty="easy"))
    assert result[0].question == good["question"]
    assert create.call_count == 2
    assert "missing backslashes" in create.call_args.kwargs["messages"][-1]["content"]
