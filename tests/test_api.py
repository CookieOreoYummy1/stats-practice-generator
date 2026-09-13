from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.backend.llm_client import GenerationError
from app.backend.main import app
from app.backend.models import Problem, Topic


@pytest.fixture
def client(monkeypatch):
    llm = MagicMock()
    llm.generate_problems.return_value = [Problem(
        id="test-id", topic="anova", difficulty="easy", question="Question",
        hints=["Hint"], solution_steps=["Private solution"], final_answer="Private answer",
    )]
    monkeypatch.setattr("app.backend.main.LLMClient", lambda: llm)
    with TestClient(app) as client:
        yield client, llm
    llm.close.assert_called_once()


def test_topics(client):
    response = client[0].get("/api/topics")
    assert response.status_code == 200
    topics = response.json()["topics"]
    assert {t["id"] for t in topics} == {t.value for t in Topic}
    assert all(all(t[key] for key in ("display_name", "easy", "medium", "hard")) for t in topics)


def test_generation_hides_and_caches_solutions(client):
    response = client[0].post("/api/generate", json={"topic": "anova", "difficulty": "easy"})
    assert response.status_code == 200
    public = response.json()["problems"][0]
    assert set(public) == {"id", "topic", "difficulty", "question", "hints"}
    assert app.state.store.get(public["id"]).final_answer == "Private answer"
    assert app.state.store.get("unknown") is None


def test_invalid_input_does_not_call_llm(client):
    assert client[0].post("/api/generate", json={"topic": "anova", "difficulty": "easy", "count": 6}).status_code == 422
    client[1].generate_problems.assert_not_called()


def test_generation_failure_does_not_cache(client):
    client[1].generate_problems.side_effect = GenerationError("Please try again.")
    response = client[0].post("/api/generate", json={"topic": "anova", "difficulty": "easy"})
    assert response.status_code == 502
    assert response.json() == {"detail": "Please try again."}
    assert app.state.store.get("test-id") is None


def test_only_phase_one_routes(client):
    assert client[0].get("/api/health").status_code == 404
    assert client[0].post("/api/check", json={}).status_code == 404
