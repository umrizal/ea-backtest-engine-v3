"""Dependency-free pragmatic MQL5 lexer."""
from dataclasses import dataclass
from typing import List

KEYWORDS = {
    "input", "const", "static", "extern", "if", "else", "for", "while",
    "return", "break", "continue", "switch", "case", "default", "new",
    "class", "struct", "enum", "public", "private", "protected", "virtual",
    "override", "true", "false", "NULL"
}
TYPES = {
    "void", "bool", "char", "uchar", "short", "ushort", "int", "uint",
    "long", "ulong", "float", "double", "string", "datetime", "color",
    "ENUM_TIMEFRAMES", "ENUM_ORDER_TYPE", "ENUM_POSITION_TYPE"
}
MULTI_OPS = [
    ">>>=", "<<=", ">>=", "==", "!=", "<=", ">=", "&&", "||", "++", "--",
    "+=", "-=", "*=", "/=", "%=", "->", "<<", ">>", "=>"
]

@dataclass
class Token:
    type: str
    value: str
    line: int
    column: int

class MQL5Lexer:
    def __init__(self, source: str):
        self.source = source
        self.i = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def _advance(self, n=1):
        for _ in range(n):
            if self.i >= len(self.source):
                return
            ch = self.source[self.i]
            self.i += 1
            if ch == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1

    def _peek(self, n=0):
        p = self.i + n
        return self.source[p] if p < len(self.source) else ""

    def tokenize(self) -> List[Token]:
        while self.i < len(self.source):
            ch = self._peek()
            if ch.isspace():
                self._advance()
                continue
            line, col = self.line, self.column

            if ch == "#":
                text = ""
                while self.i < len(self.source) and self._peek() != "\n":
                    text += self._peek()
                    self._advance()
                self.tokens.append(Token("PREPROCESSOR", text.strip(), line, col))
                continue

            if ch == "/" and self._peek(1) == "/":
                text = ""
                while self.i < len(self.source) and self._peek() != "\n":
                    text += self._peek()
                    self._advance()
                self.tokens.append(Token("COMMENT", text, line, col))
                continue

            if ch == "/" and self._peek(1) == "*":
                text = ""
                self._advance(2)
                while self.i < len(self.source) and not (self._peek() == "*" and self._peek(1) == "/"):
                    text += self._peek()
                    self._advance()
                if self.i < len(self.source):
                    self._advance(2)
                self.tokens.append(Token("COMMENT", text, line, col))
                continue

            if ch in ('"', "'"):
                quote = ch
                text = ch
                self._advance()
                while self.i < len(self.source):
                    c = self._peek()
                    text += c
                    self._advance()
                    if c == "\\" and self.i < len(self.source):
                        text += self._peek()
                        self._advance()
                        continue
                    if c == quote:
                        break
                self.tokens.append(Token("STRING" if quote == '"' else "CHAR", text, line, col))
                continue

            if ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
                text = ""
                dot = False
                while self.i < len(self.source):
                    c = self._peek()
                    if c.isdigit():
                        text += c
                        self._advance()
                    elif c == "." and not dot:
                        dot = True
                        text += c
                        self._advance()
                    else:
                        break
                self.tokens.append(Token("FLOAT" if dot else "NUMBER", text, line, col))
                continue

            if ch.isalpha() or ch == "_":
                text = ""
                while self.i < len(self.source) and (self._peek().isalnum() or self._peek() == "_"):
                    text += self._peek()
                    self._advance()
                typ = "KEYWORD" if text in KEYWORDS else "TYPE" if text in TYPES else "IDENTIFIER"
                self.tokens.append(Token(typ, text, line, col))
                continue

            matched = None
            for op in MULTI_OPS:
                if self.source.startswith(op, self.i):
                    matched = op
                    break
            if matched:
                self.tokens.append(Token("OPERATOR", matched, line, col))
                self._advance(len(matched))
                continue

            if ch in "+-*/%=!<>?:&|^~":
                self.tokens.append(Token("OPERATOR", ch, line, col))
            elif ch in "(){}[];,.":
                self.tokens.append(Token("PUNCTUATION", ch, line, col))
            else:
                self.tokens.append(Token("UNKNOWN", ch, line, col))
            self._advance()

        self.tokens.append(Token("EOF", "", self.line, self.column))
        return self.tokens
