import pytest
from pydantic import ValidationError

from app.backend.models import ProblemRequest


def test_default_count():
    assert ProblemRequest(topic="anova", difficulty="easy").count == 1


@pytest.mark.parametrize("changes", [
    {"topic": "unknown"}, {"difficulty": "expert"}, {"count": 0}, {"count": 6},
])
def test_invalid_request(changes):
    with pytest.raises(ValidationError):
        ProblemRequest.model_validate({"topic": "anova", "difficulty": "easy", **changes})
