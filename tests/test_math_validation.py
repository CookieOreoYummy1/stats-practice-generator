import pytest

from app.backend.math_validation import validate_math


@pytest.mark.parametrize("text", [
    r"$$text{Mean}=frac{sum x_i}{n}$$",
    r"$$textMean=fracsum x_i n$$",
    r"$displaystyle barx=frac1n sum_{i=1}^n x_i$",
    "$\text{Mean}=\frac{x}{n}$",
    "$\nu=2$",
    "A damaged \bar{x}",
])
def test_rejects_damaged_math(text):
    with pytest.raises(ValueError):
        validate_math(text)


@pytest.mark.parametrize("text", [
    r"$$\text{Mean}=\frac{\sum x_i}{n}$$",
    r"$\nu=2$",
    "Mean, median, mode, and range.",
    "$$\n x_i + y_i\n$$",
    r"$\begin{aligned}x &= 2 \\ y &= 3\end{aligned}$",
])
def test_accepts_valid_math_and_prose(text):
    validate_math(text)


@pytest.mark.parametrize("text", [
    "$$", r"\(x=2$$", r"$x=2$$", r"\[x=2\)",
    r"P(D\mid C)=0.5; the events are not independent.",
    r"F \approx 5.81; we reject $H_0$.",
])
def test_rejects_unmatched_delimiters_and_unwrapped_commands(text):
    with pytest.raises(ValueError):
        validate_math(text)


@pytest.mark.parametrize("text", [
    r"$P(D\mid C)=0.5$; the events are not independent.",
    r"$F \approx 5.81$; we reject $H_0$.",
    r"\[x=2\] followed by \(y=3\).",
    r"Cost: \$20 and \$30.",
])
def test_accepts_complete_mixed_prose_and_math(text):
    validate_math(text)
