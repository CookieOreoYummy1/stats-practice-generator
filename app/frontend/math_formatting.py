"""Adapt common LLM math delimiters to Streamlit's Markdown syntax."""

import re


# Match code first so examples in backticks remain literal. Match existing math
# as a unit so LaTeX commands inside it are never unescaped or rewritten.
_SEGMENTS = re.compile(
    r"(?P<code>(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^(?P=fence)[ \t]*$|`+[^`\n]*`+)"
    r"|(?P<display>(?<![\\$])\$\$(?!\$)(?P<display_body>.*?)(?<!\\)\$\$(?!\$))"
    r"|(?P<inline>(?<![\\$])\$(?!\$)(?:\\.|[^$\n])*?(?<!\\)\$(?!\$))"
    r"|(?P<bracket>(?<!\\)\\\[(?P<bracket_body>.*?)(?<!\\)\\\])"
    r"|(?P<paren>(?<!\\)\\\((?P<paren_body>[^\n]*?)(?<!\\)\\\))",
    re.DOTALL | re.MULTILINE,
)

# Only collapse doubled escapes before known commands, never LaTeX row breaks
# (e.g. "a &= b \\\\ c &= d") or arbitrary backslashes.
_EXTRA_COMMAND_ESCAPE = re.compile(
    r"(?<!\\)\\\\(?=(?:displaystyle|textstyle|text|frac|dfrac|tfrac|sqrt|"
    r"sum|prod|int|bar|overline|hat|widehat|mathrm|mathbf|mathbb|operatorname|"
    r"left|right|begin|end|alpha|beta|gamma|delta|sigma|mu|nu|pi|theta|"
    r"leq|geq|neq|approx|times|cdot|pm|infty|log|ln|exp)(?![A-Za-z]))"
)


def _math_body(body: str) -> str:
    return _EXTRA_COMMAND_ESCAPE.sub(lambda _: "\\", body)


def _prose(text: str) -> str:
    # A literal escaped newline outside math is transport formatting. A word
    # boundary avoids corrupting commands such as \nu, \neq, and \nabla.
    return re.sub(r"(?<!\\)\\n(?![a-z])", "\n", text)


def normalize_math(text: str) -> str:
    """Normalize paired math delimiters; preserve ordinary brackets and escapes."""
    def replace(match: re.Match) -> str:
        if match.group("display") or match.group("bracket"):
            body = match.group("display_body") if match.group("display") else match.group("bracket_body")
            return "\n\n$$\n" + _math_body(body.strip()) + "\n$$\n\n"
        if match.group("paren"):
            return "$" + _math_body(match.group("paren_body").strip()) + "$"
        if match.group("inline"):
            return _math_body(match.group(0))
        return match.group(0)

    parts = []
    end = 0
    for match in _SEGMENTS.finditer(text):
        parts.extend((_prose(text[end:match.start()]), replace(match)))
        end = match.end()
    parts.append(_prose(text[end:]))
    return "".join(parts)
