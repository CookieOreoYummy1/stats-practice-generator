"""Catch common damaged LaTeX output without guessing at repairs."""

import re


_MATH = re.compile(r"\$\$(.*?)\$\$|(?<![\\$])\$(?!\$)(.*?)(?<!\\)\$(?!\$)|\\\[(.*?)\\\]|\\\((.*?)\\\)", re.DOTALL)
_BARE_COMMAND = re.compile(
    r"(?<![\\A-Za-z])(?:text|frac|sqrt|mathrm|mathbf|overline|bar)\s*\{"
    r"|(?<![\\A-Za-z])(?:textMean|fracsum)(?![a-z])"
    r"|(?<![\\A-Za-z])(?:displaystyle|textstyle|frac|dfrac|tfrac|sum|prod)(?![A-Za-z])"
)


def validate_math(text: str) -> None:
    """Reject clear escaping damage; this is not a full LaTeX parser."""
    if any(ord(char) < 32 and char not in "\n\t" for char in text):
        raise ValueError("Math contains JSON control characters. Double every LaTeX backslash in JSON strings.")
    for match in _MATH.finditer(text):
        body = next(group for group in match.groups() if group is not None)
        # A JSON \t or \n can silently consume the first letter of a command.
        if re.search(r"\text\b|\n(?:u|abla|eq)(?![A-Za-z])", body):
            raise ValueError("Math contains a damaged LaTeX escape. Double LaTeX backslashes in JSON strings.")
        if _BARE_COMMAND.search(body):
            raise ValueError("Math contains LaTeX commands missing backslashes. Use properly escaped commands such as \\text and \\frac.")
