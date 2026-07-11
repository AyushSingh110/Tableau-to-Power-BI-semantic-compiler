"""Tokenizer for the Tableau calculation language.

Produces a flat token stream for the Pratt parser. Comments are stripped here.
Unknown characters raise ``TokenizeError`` so the caller can fall back to a
``parse_error`` AST node rather than crashing the pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class TokenizeError(ValueError):
    """Raised for a character the tokenizer cannot classify."""


@dataclass
class Token:
    kind: str      # NUMBER STRING FIELD IDENT KW OP LBRace RBrace ...
    value: str
    pos: int


# Keywords are matched case-insensitively but normalized to upper case.
KEYWORDS = {
    "IF", "THEN", "ELSEIF", "ELSE", "END", "CASE", "WHEN",
    "AND", "OR", "NOT", "IN",
    "TRUE", "FALSE", "NULL",
    "FIXED", "INCLUDE", "EXCLUDE",
}

# Multi-char operators first so they win over single-char prefixes.
_OPERATORS = ["<=", ">=", "<>", "!=", "==", "=", "<", ">", "+", "-", "*", "/", "%", "^", "(", ")", ",", ":"]

_WS_RE = re.compile(r"\s+")
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_FIELD_RE = re.compile(r"\[[^\]]*\]")


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]

        m = _WS_RE.match(text, i)
        if m:
            i = m.end()
            continue

        # Comments — handled in-loop so `//` inside a string literal is safe.
        if text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j == -1 else j + 1
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i)
            i = n if j == -1 else j + 2
            continue

        if ch in "{}":
            tokens.append(Token("LBrace" if ch == "{" else "RBrace", ch, i))
            i += 1
            continue

        # Field reference, possibly datasource-qualified: [DS].[Field]
        if ch == "[":
            m = _FIELD_RE.match(text, i)
            if not m:
                raise TokenizeError(f"unterminated field reference at {i}")
            parts = [m.group(0)]
            j = m.end()
            while j < n and text[j] == "." and j + 1 < n and text[j + 1] == "[":
                m2 = _FIELD_RE.match(text, j + 1)
                if not m2:
                    break
                parts.append(m2.group(0))
                j = m2.end()
            # The field's own name is the last bracketed segment.
            name = parts[-1][1:-1]
            tokens.append(Token("FIELD", name, i))
            i = j
            continue

        # String literal (double or single quoted).
        if ch in "\"'":
            quote = ch
            j = i + 1
            buf = []
            while j < n and text[j] != quote:
                buf.append(text[j])
                j += 1
            if j >= n:
                raise TokenizeError(f"unterminated string at {i}")
            tokens.append(Token("STRING", "".join(buf), i))
            i = j + 1
            continue

        m = _NUMBER_RE.match(text, i)
        if m:
            tokens.append(Token("NUMBER", m.group(0), i))
            i = m.end()
            continue

        m = _IDENT_RE.match(text, i)
        if m:
            word = m.group(0)
            up = word.upper()
            if up in KEYWORDS:
                tokens.append(Token("KW", up, i))
            else:
                tokens.append(Token("IDENT", word, i))
            i = m.end()
            continue

        matched = False
        for op in _OPERATORS:
            if text.startswith(op, i):
                tokens.append(Token("OP", op, i))
                i += len(op)
                matched = True
                break
        if matched:
            continue

        raise TokenizeError(f"unexpected character {ch!r} at {i}")

    tokens.append(Token("EOF", "", n))
    return tokens
