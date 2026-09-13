import pytest

from app.frontend.math_formatting import normalize_math


def test_reported_statistics_labels_with_latex_delimiters():
    text = r"Compute: \[ \text{Mean},\; \text{Median},\; \text{Mode},\; \text{Range} \] Round to two decimals."
    result = normalize_math(text)
    assert result == "Compute: \n\n$$\n" + r"\text{Mean},\; \text{Median},\; \text{Mode},\; \text{Range}" + "\n$$\n\n Round to two decimals."


def test_inline_and_display_math():
    assert normalize_math(r"Use \(\bar{x}\) and $$\frac{1}{n}$$.") == "Use $\\bar{x}$ and \n\n$$\n\\frac{1}{n}\n$$\n\n."


@pytest.mark.parametrize("text", [
    r"Ages [22, 19, 22] (in years).",
    r"Use $\frac{1}{2}$ and $\bar{x}$.",
    r"Cost: \$20 and \$30.",
    r"`\[x\]` and `$$x$$` are code examples.",
    "```latex\n\\[x\\]\n```",
    r"Unmatched \[x and $y",
    r"$$unclosed",
    r"$\begin{aligned} a &= b \\ c &= d \end{aligned}$",
])
def test_preserves_non_math_and_existing_inline_math(text):
    assert normalize_math(text) == text


def test_overescaped_reported_mean_formula_and_list():
    text = r"Compute:\n\n- Mean (use $\\displaystyle \\bar{x}=\\frac{1}{n}\\sum_{i=1}^{n}x_i$)\n- Median\n- Mode"
    expected = "Compute:\n\n- Mean (use " + r"$\displaystyle \bar{x}=\frac{1}{n}\sum_{i=1}^{n}x_i$)" + "\n- Median\n- Mode"
    assert normalize_math(text) == expected


def test_preserves_real_row_breaks_while_fixing_commands():
    text = r"$$\\begin{aligned} a &= \\frac{1}{2} \\ b &= 3 \\end{aligned}$$"
    assert normalize_math(text) == "\n\n$$\n" + r"\begin{aligned} a &= \frac{1}{2} \\ b &= 3 \end{aligned}" + "\n$$\n\n"


def test_newline_conversion_preserves_math_and_code():
    text = r"Use $\nu + \neq$ and `\n` or `\\frac`.\nNext"
    assert normalize_math(text) == r"Use $\nu + \neq$ and `\n` or `\\frac`." + "\nNext"


@pytest.mark.parametrize("text", ["Temperature: 20°C.", "$20°$", r"$20^{\circ}\mathrm{C}$"])
def test_degree_notation_is_preserved(text):
    assert normalize_math(text) == text
