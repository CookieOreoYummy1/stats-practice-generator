import pytest
from pydantic import ValidationError

from app.backend.confidence_intervals import MeanIntervalInputs, calculated_interval
from app.backend.math_validation import validate_math
from app.backend.models import Problem


@pytest.mark.parametrize("mean, expected", [(850, "$(742, 958)$"), (-850, "$(-958, -742)$")])
def test_saved_calcium_interval_rounding(mean, expected):
    inputs = MeanIntervalInputs(sample_mean=mean, sample_std=120, sample_size=12,
                                confidence_percent=99, critical_value=3.106, decimal_places=0)
    problem = Problem(id="ci", topic="confidence_intervals", difficulty="medium",
                      question="Old question", hints=[], solution_steps=["Wrong: (743, 958)"], final_answer="Wrong")
    result = calculated_interval(problem, inputs)
    assert result.final_answer == expected
    assert "Wrong" not in " ".join(result.solution_steps)
    for text in [result.question, *result.hints, *result.solution_steps, result.final_answer]:
        validate_math(text)


@pytest.mark.parametrize("changes", [{"sample_size": 1}, {"sample_std": 0}, {"sample_mean": float("nan")},
                                    {"critical_value": -2}, {"confidence_percent": 100}, {"decimal_places": -1}])
def test_invalid_interval_inputs(changes):
    data = dict(sample_mean=850, sample_std=120, sample_size=12, confidence_percent=99,
                critical_value=3.106, decimal_places=0)
    with pytest.raises(ValidationError):
        MeanIntervalInputs.model_validate({**data, **changes})
