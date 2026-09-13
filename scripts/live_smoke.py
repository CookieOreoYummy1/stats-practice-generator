"""Opt-in live Groq checks: python -m scripts.live_smoke (uses API quota)."""

import json
from pathlib import Path
from statistics import mean
from time import perf_counter

from fastapi.testclient import TestClient

from app.backend.main import app
from app.backend.models import Problem, Topic
from app.frontend.math_formatting import normalize_math


def main():
    report = {"generation": [], "grading": [], "limitations": [
        "Browser LaTeX rendering is not checked.",
        "Generated mathematics requires independent review; schema success is not a correctness verdict.",
    ]}
    output = Path("artifacts/live-smoke.json")
    output.parent.mkdir(exist_ok=True)

    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        with TestClient(app) as client:
            report["model"] = app.state.llm_client.model
            for topic in Topic:
                started = perf_counter()
                response = client.post("/api/generate", json={"topic": topic.value, "difficulty": "medium", "count": 1})
                entry = {"topic": topic.value, "status": response.status_code, "seconds": round(perf_counter() - started, 2)}
                if response.status_code == 200:
                    public = response.json()["problems"][0]
                    entry["public_hides_solution"] = not ({"solution_steps", "final_answer"} & public.keys())
                    problem = app.state.store.get(public["id"])
                    entry["problem"] = problem.model_dump(mode="json")
                    entry["rendered_text"] = {"question": normalize_math(problem.question),
                                              "solution_steps": [normalize_math(s) for s in problem.solution_steps],
                                              "final_answer": normalize_math(problem.final_answer)}
                else:
                    entry["error"] = response.json()
                report["generation"].append(entry)
                save()
                print(f"Generation {topic.value}: HTTP {response.status_code}", flush=True)

            # Known answers computed independently, not accepted from generated output.
            numeric = Problem(id="controlled-mean", topic=Topic.descriptive_stats, difficulty="easy",
                              question="Compute the mean of 2, 4, 6, 8. Give a numerical answer.", hints=[],
                              solution_steps=["(2 + 4 + 6 + 8) / 4 = 5"], final_answer=str(mean([2, 4, 6, 8])))
            probability = Problem(id="controlled-probability", topic=Topic.probability, difficulty="easy",
                                  question="A bag contains 3 red and 9 blue balls. What is the probability of drawing a red ball?",
                                  hints=[], solution_steps=["3 / 12 = 0.25"], final_answer=str(3 / 12))
            app.state.store.add_many([numeric, probability])
            for problem, answer, expected in [(numeric, "5", True), (numeric, "100", False),
                                              (probability, "25%", True), (probability, "1/4", True)]:
                response = client.post("/api/check", json={"problem_id": problem.id, "user_answer": answer})
                result = response.json()
                passed = response.status_code == 200 and result.get("correct") is expected
                report["grading"].append({"problem_id": problem.id, "answer": answer, "expected": expected,
                                          "status": response.status_code, "passed": passed, "result": result})
                save()
                print(f"Grading {problem.id} / {answer}: {'PASS' if passed else 'FAIL'}", flush=True)
    except Exception as exc:
        # Do not serialize provider exception details, which may contain request data.
        report["run_error"] = type(exc).__name__
        save()
        print(f"Live test stopped: {type(exc).__name__}. See {output}.", flush=True)
        raise SystemExit(1) from None
    failed = any(e["status"] != 200 for e in report["generation"]) or any(not e["passed"] for e in report["grading"])
    print(f"Report: {output}", flush=True)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
