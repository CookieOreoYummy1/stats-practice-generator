from .models import Problem


class ProblemStore:
    """Process-local cache; restarting the backend clears all problems."""

    def __init__(self) -> None:
        self._problems: dict[str, Problem] = {}

    def add_many(self, problems: list[Problem]) -> None:
        self._problems.update({problem.id: problem for problem in problems})

    def get(self, problem_id: str) -> Problem | None:
        return self._problems.get(problem_id)
