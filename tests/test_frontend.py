import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from streamlit.testing.v1 import AppTest


@pytest.fixture
def ui(monkeypatch):
    response = Mock()
    response.json.return_value = {"topics": [{"id": "anova", "display_name": "ANOVA"}]}
    monkeypatch.setattr(requests, "get", Mock(return_value=response))
    post = Mock()
    monkeypatch.setattr(requests, "post", post)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app/frontend/streamlit_app.py")).run()
    app.session_state["problems"] = [
        {"id": "one", "question": "Question one", "hints": ["First hint", r"Use $\bar{x}$"],
         "solution_steps": ["Secret solution"], "final_answer": "Secret answer"},
        {"id": "two", "question": "Question two", "hints": ["Other hint"]},
    ]
    app.run()
    assert not app.exception
    return app, post


def http_error(status, detail):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps({"detail": detail}).encode()
    return requests.HTTPError(response=response)


def test_hints_are_progressive_independent_and_do_not_reveal_solutions(ui):
    app, post = ui
    assert not app.expander[0].markdown
    app.button(key="hint_one").click().run()
    assert [m.value for m in app.expander[0].markdown] == ["First hint"]
    assert not app.expander[1].markdown
    app.button(key="hint_one").click().run()
    assert len(app.expander[0].markdown) == 2
    assert app.button(key="hint_one").disabled
    app.button(key="hint_two").click().run()
    assert app.session_state["hints_shown"] == {"one": 2, "two": 1}
    assert all("Secret" not in m.value for m in app.markdown)
    assert app.session_state["score"] == {"correct": 0, "attempted": 0}
    post.assert_not_called()
    assert not app.exception


def test_new_set_clears_practice_and_widgets(ui):
    app, post = ui
    app.text_input(key="answer_one").set_value("typed answer").run()
    app.button(key="hint_one").click().run()
    app.session_state["results"] = {"one": {"correct": True}}
    app.session_state["score"] = {"correct": 1, "attempted": 1}
    next(b for b in app.sidebar.button if b.label == "New Set").click().run()
    assert app.session_state["problems"] == []
    assert app.session_state["results"] == {}
    assert app.session_state["hints_shown"] == {}
    assert app.session_state["score"] == {"correct": 0, "attempted": 0}
    assert "answer_one" not in app.session_state
    assert not app.text_input and not app.expander
    assert app.info and app.sidebar.metric[0].value == "0/0"
    post.assert_not_called()
    assert not app.exception


@pytest.mark.parametrize("answer", ["", "   "])
def test_blank_answers_never_call_backend(ui, answer):
    app, post = ui
    app.text_input(key="answer_one").set_value(answer).run()
    app.button(key="check_one").click().run()
    post.assert_not_called()
    assert app.error[0].value == "Enter an answer before checking."
    assert not app.exception


@pytest.mark.parametrize("operation", ["generate", "check"])
@pytest.mark.parametrize("error, message", [
    (http_error(502, "The model returned invalid output twice."), "The model returned invalid output twice."),
    (http_error(502, "The LLM timed out. Please try again."), "The LLM timed out. Please try again."),
    (requests.Timeout(), "timed out"),
    (requests.ConnectionError(), "Couldn't"),
    (http_error(502, ["unexpected detail"]), "Couldn't"),
])
def test_failures_are_readable_and_preserve_state(ui, operation, error, message):
    app, post = ui
    post.side_effect = error
    app.text_input(key="answer_one").set_value("42").run()
    if operation == "generate":
        next(b for b in app.sidebar.button if b.label == "Generate Problems").click().run()
    else:
        app.button(key="check_one").click().run()
    assert not app.exception
    assert any(message in e.value for e in app.error)
    assert len(app.session_state["problems"]) == 2
    assert app.session_state["score"] == {"correct": 0, "attempted": 0}
    assert app.text_input(key="answer_one").value == "42"


def test_unknown_problem_suggests_new_set(ui):
    app, post = ui
    post.side_effect = http_error(404, "Problem not found")
    app.text_input(key="answer_one").set_value("42").run()
    app.button(key="check_one").click().run()
    assert '"New Set"' in app.error[0].value
    assert not app.exception


def test_empty_hint_list(ui):
    app, _ = ui
    app.session_state["problems"] = [{"id": "empty", "question": "Question", "hints": []}]
    app.run()
    assert app.button(key="hint_empty").disabled
    assert app.expander[0].caption[0].value == "No hints available for this problem."
    assert not app.exception
