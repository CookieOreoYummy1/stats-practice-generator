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
