from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Topic(str, Enum):
    descriptive_stats = "descriptive_statistics"
    probability = "probability_basics"
    discrete_dist = "discrete_distributions"
    continuous_dist = "continuous_distributions"
    sampling_clt = "sampling_distributions_and_clt"
    confidence_intervals = "confidence_intervals"
    hypothesis_testing = "hypothesis_testing"
    regression = "correlation_and_regression"
    anova = "anova"


Difficulty = Literal["easy", "medium", "hard"]


class ProblemRequest(BaseModel):
    topic: Topic
    difficulty: Difficulty
    count: int = Field(default=1, ge=1, le=5)


class Problem(BaseModel):
    id: str
    topic: Topic
    difficulty: Difficulty
    question: str
    hints: list[str]
    solution_steps: list[str]
    final_answer: str


class ProblemPublic(BaseModel):
    """What the client receives from /api/generate, without the solution."""

    id: str
    topic: Topic
    difficulty: Difficulty
    question: str
    hints: list[str]


class ProblemBatchResponse(BaseModel):
    problems: list[ProblemPublic]


class AnswerCheckRequest(BaseModel):
    problem_id: str
    user_answer: str


class AnswerCheckResponse(BaseModel):
    correct: bool
    feedback: str
    solution_steps: list[str]
    final_answer: str
