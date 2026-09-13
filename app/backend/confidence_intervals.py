"""Deterministic arithmetic for one-sample mean confidence intervals."""

from decimal import Decimal, ROUND_HALF_UP, localcontext

from pydantic import BaseModel, Field

from .models import Problem


class MeanIntervalInputs(BaseModel):
    sample_mean: float = Field(ge=-1e9, le=1e9, allow_inf_nan=False)
    sample_std: float = Field(gt=0, le=1e9, allow_inf_nan=False)
    sample_size: int = Field(ge=2, le=1_000_000)
    confidence_percent: float = Field(gt=0, lt=100, allow_inf_nan=False)
    critical_value: float = Field(gt=0, le=100, allow_inf_nan=False)
    decimal_places: int = Field(ge=0, le=6)


def calculated_interval(problem: Problem, inputs: MeanIntervalInputs) -> Problem:
    """Use the explicitly supplied critical value; do not infer it from prose."""
    with localcontext() as context:
        context.prec = 40
        center = Decimal(str(inputs.sample_mean))
        std = Decimal(str(inputs.sample_std))
        critical = Decimal(str(inputs.critical_value))
        se = std / Decimal(inputs.sample_size).sqrt()
        margin = critical * se
        lower, upper = center - margin, center + margin
        quantum = Decimal(1).scaleb(-inputs.decimal_places)
        bounds = [value.quantize(quantum, rounding=ROUND_HALF_UP) for value in (lower, upper)]
    n = inputs.sample_size
    # Own the numerical question as well as its solution, so the structured
    # values cannot silently disagree with independently generated prose.
    question = (
        f"A random sample of $n={n}$ measurements from an approximately normal "
        f"population has sample mean $\\bar{{x}}={center}$ and sample standard "
        f"deviation $s={std}$. The population standard deviation is unknown. "
        f"Construct a {inputs.confidence_percent:g}% confidence interval for the "
        f"population mean. Use the supplied two-sided critical value "
        f"$t^*={critical}$ with ${n - 1}$ degrees of freedom. "
        f"Treat this supplied value as exact for this exercise, keep intermediate "
        f"calculations unrounded, and round both bounds to {inputs.decimal_places} "
        "decimal places (round halves away from zero)."
    )
    return problem.model_copy(update={
        "question": question,
        "hints": [
            "Use a one-sample t interval because the population standard deviation is unknown.",
            r"Compute the standard error $SE=s/\sqrt{n}$.",
            r"Use $\bar{x}\pm t^*SE$ and round only the final endpoints.",
        ],
        "solution_steps": [
            f"Use a t interval with $df={n - 1}$ and the supplied critical value $t^*={critical}$.",
            f"The standard error is $SE=\\frac{{{std}}}{{\\sqrt{{{n}}}}}\\approx {se:.8f}$.",
            f"The margin of error is $ME={critical}\\times SE\\approx {margin:.8f}$.",
            f"Before rounding, the bounds are approximately $({lower:.8f}, {upper:.8f})$.",
            f"Rounding the unrounded bounds to {inputs.decimal_places} decimal places gives $({bounds[0]}, {bounds[1]})$.",
        ],
        "final_answer": f"$({bounds[0]}, {bounds[1]})$",
    })
