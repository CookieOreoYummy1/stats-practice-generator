import json

from .models import Problem, ProblemRequest, Topic
from .confidence_intervals import MeanIntervalInputs


SYSTEM_PROMPT = """You are an experienced statistics teaching assistant writing practice
problems for an introductory undergraduate statistics course. Every
problem you write must be:
- Mathematically correct — double-check your own arithmetic before
  finalizing the answer.
- Solvable using only intro-stats-course methods (no measure theory, no
  advanced calculus).
- Realistic in framing (plausible scenarios: samples, surveys, experiments).
- Formatted with LaTeX for all math: inline as $...$, display equations as
  $$...$$. Put each opening and closing $$ on its own line, with the
  equation on the lines between them. Use only dollar-sign math delimiters,
  never LaTeX bracket or parenthesis delimiters. Do not put math in backticks
  or code fences. Use plain prose for labels such as Mean, Median, Mode,
  and Range; reserve LaTeX for mathematical expressions.
- Keep LaTeX command backslashes intact. Never output bare text{...} or
  frac{...}{...} inside math. JSON strings must escape every backslash.
- Do not append a generic formula to every question. Put worked formulas
  in solution_steps unless the question explicitly requires a formula.
- Free of trick wording — the difficulty should come from the statistics,
  not from ambiguous phrasing.

You will be asked to generate problems for a specific topic and difficulty
level. Follow the requested output schema exactly.
"""

TOPIC_TAXONOMY = {
    Topic.descriptive_stats: {
        "display_name": "Descriptive statistics",
        "easy": "Mean/median/mode/range from a small dataset",
        "medium": "Weighted mean, outlier effects on mean vs. median",
        "hard": "Comparing skew/spread across two datasets, interpreting boxplots",
    },
    Topic.probability: {
        "display_name": "Probability basics",
        "easy": "Single-event probability",
        "medium": "Conditional probability, independence",
        "hard": "Bayes' theorem, combined events",
    },
    Topic.discrete_dist: {
        "display_name": "Discrete distributions",
        "easy": "Binomial P(X=k)",
        "medium": "Binomial cumulative, expected value",
        "hard": "Poisson approximation, comparing two distributions",
    },
    Topic.continuous_dist: {
        "display_name": "Continuous distributions",
        "easy": "Normal P(X<a) via z-table",
        "medium": "Normal, find x given percentile",
        "hard": "Non-standard normal combined with sampling",
    },
    Topic.sampling_clt: {
        "display_name": "Sampling distributions / CLT",
        "easy": "Standard error of the mean",
        "medium": "CLT applied to non-normal population",
        "hard": "Sampling distribution of a proportion",
    },
    Topic.confidence_intervals: {
        "display_name": "Confidence intervals",
        "easy": "CI for a mean, known σ",
        "medium": "CI for a mean, unknown σ (t-dist)",
        "hard": "CI for a proportion, sample-size determination",
    },
    Topic.hypothesis_testing: {
        "display_name": "Hypothesis testing",
        "easy": "One-sample z-test",
        "medium": "One-sample t-test, p-value interpretation",
        "hard": "Two-sample test, Type I/II error framing",
    },
    Topic.regression: {
        "display_name": "Correlation & regression",
        "easy": "Compute/interpret r",
        "medium": "Simple linear regression equation",
        "hard": "Interpret residuals, R², prediction interval",
    },
    Topic.anova: {
        "display_name": "ANOVA",
        "easy": "Conceptual (when to use ANOVA)",
        "medium": "One-way ANOVA F-statistic",
        "hard": "Interpreting ANOVA table, post-hoc reasoning",
    },
}


def generation_prompt(request: ProblemRequest) -> str:
    rubric = TOPIC_TAXONOMY[request.topic][request.difficulty]
    interval_instructions = ""
    if request.topic == Topic.confidence_intervals and request.difficulty == "medium":
        interval_instructions = (
            "\nFor each problem also include a mean_interval object matching this schema: "
            + json.dumps(MeanIntervalInputs.model_json_schema())
            + "\nChoose plausible one-sample mean inputs and the two-sided t critical value "
            "for the chosen confidence_percent and sample_size minus one degrees of freedom. "
            "The server will construct the numerical question, hints, solution, and final "
            "answer from these inputs, supplying your critical value explicitly in the question."
        )
    return (
        f"Generate exactly {request.count} distinct problems.\n"
        f"Topic: {request.topic.value}\nDifficulty: {request.difficulty}\n"
        f"Difficulty rubric: {rubric}\n"
        'Return only a JSON object of the form {"problems": [problem, ...]}.\n'
        "Every problem must match this JSON schema:\n"
        f"{json.dumps(Problem.model_json_schema(), ensure_ascii=False)}\n"
        "Use the exact requested topic and difficulty in every problem. "
        "Include an id string (the server will assign the final UUID), ordered "
        "progressively revealing hints, a full worked solution_steps list, and "
        "a canonical final_answer. Keep answers out of the question and avoid "
        "giving away the final answer in hints. Escape LaTeX backslashes correctly "
        "in JSON strings. State any necessary assumptions and rounding precision.\n"
        "Example of correctly JSON-escaped math (follow the formatting, not the content):\n"
        + json.dumps({"question": "Compute $\\bar{x}$ using:\n\n$$\n\\bar{x} = \\frac{1}{n}\\sum_{i=1}^{n}x_i\n$$\n"})
        + "\nAfter JSON decoding, each LaTeX command must have exactly ONE backslash, "
        "and paragraph/list breaks must be actual newline characters. Do not "
        "double-encode the text: the decoded question must not contain literal "
        "backslash-n sequences or doubled backslashes before commands. "
        "Use doubled backslashes in decoded LaTeX only for intentional equation row breaks."
        " Every question, hint, solution step, and final_answer must contain complete, "
        "matched math delimiters. Never split an equation across solution_steps entries. "
        "Wrap math in final_answer in $...$ too; leave explanatory prose outside."
        + interval_instructions
    )
