import json
from unittest.mock import MagicMock

import pytest

from app.backend.grading import GradingError, grade_answer
from app.backend.models import Problem


@pytest.fixture
def problem():
    return Problem(id="p", topic="probability_basics", difficulty="easy",
                   question="Find the probability.", hints=[],
                   solution_steps=["Compute $842/1000$."], final_answer="0.842")


@pytest.mark.parametrize("correct", [True, False])
def test_grade_uses_problem_context_and_cached_solution(problem, correct):
    llm = MagicMock()
    llm.complete_json.return_value = json.dumps({"correct": correct, "feedback": "Reason"})
    result = grade_answer(problem, "84.2%", llm)
    assert result.correct is correct
    assert result.solution_steps == problem.solution_steps
    assert result.final_answer == problem.final_answer
    messages = llm.complete_json.call_args.args[0]
    assert json.loads(messages[1]["content"]) == {
        "question": problem.question, "final_answer": "0.842", "user_answer": "84.2%"}
    llm.complete_json.assert_called_once()


@pytest.mark.parametrize("invalid", ["not json", "{}", '{"correct":"false","feedback":"x"}',
                                    '{"correct":false,"feedback":" "}'])
def test_invalid_grade_retries_once(problem, invalid):
    llm = MagicMock()
    llm.complete_json.side_effect = [invalid, '{"correct":false,"feedback":"Try reviewing the formula."}']
    assert grade_answer(problem, "wrong", llm).correct is False
    assert llm.complete_json.call_count == 2
    assert "failed validation" in llm.complete_json.call_args.args[0][-1]["content"]


def test_repeated_invalid_grade_fails(problem):
    llm = MagicMock()
    llm.complete_json.return_value = "bad"
    with pytest.raises(GradingError):
        grade_answer(problem, "42", llm)
    assert llm.complete_json.call_count == 2
