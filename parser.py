from dataclasses import dataclass, field
from enum import Enum

KEYWORDS = [
    'DEF',
    'BEGIN_DOCUMENT',
    'END_DOCUMENT',
    'BEGIN_SECTION',
    'END_SECTION',
    'BEGIN_FIELD',
    'END_FIELD',
    'SETUP',
    'TEXT',
    'LINEAR_BARCODE_CODE39',
    'GRAPHIC_BOX'
]

COMMANDS = [
    'DPMM',
    'DIMENSIONS',
    'MARGINS',
    'POSITION',
    'FONT',
    'LINEAR_BARCODE_CONFIG',
    'CODE39_CONFIG',
    'BOX'
]

class ZPLP_Token_Type(Enum):
    KEYWORD = 0
    COMMAND = 1
    IDENTIFIER = 2
    LITERAL = 3
    DOUBLE_COLON = 4
    STAR = 5
    OPEN_CURLY = 6
    CLOSE_CURLY = 7
    COMMA = 8

@dataclass
class ZPLP_Token:
    type: ZPLP_Token_Type
    value: str = ''

@dataclass
class ZPLP_Line:
    number: int
    text: str
    tokens: list[ZPLP_Token] = field(default_factory=list)

@dataclass
class ZPLP_Tokenizer:
    file_path: str
    file_lines: list[str] = field(default_factory=list)
    lines: list[ZPLP_Line] = field(default_factory=list)
    identifiers: list[str] = field(default_factory=list)

    def __post_init__(self):
        with open(self.file_path, 'r') as f:
            self.file_lines = f.readlines()

    def tokenize(self) -> None:
        for i, line in enumerate(self.file_lines):
            text = line
            l = ZPLP_Line(i+1, text)
            value = ''
            while len(text) > 0:
                c = text[0]
                if c.isalnum() or c == '_' or c == '/':
                    value += c
                else:
                    if len(value) > 0:
                        if value in KEYWORDS:
                            l.tokens.append(ZPLP_Token(ZPLP_Token_Type.KEYWORD, value))
                        elif value in COMMANDS:
                            l.tokens.append(ZPLP_Token(ZPLP_Token_Type.COMMAND, value))
                        else:
                            if len(l.tokens) > 0:
                                if l.tokens[-1].value == 'DEF':
                                    l.tokens.append(ZPLP_Token(ZPLP_Token_Type.IDENTIFIER, value))
                                    if value in self.identifiers:
                                        raise ValueError(f"{self.file_path}:{l.number}: Identifier {value} has already been assigned!")
                                    self.identifiers.append(value)
                                else:
                                    l.tokens.append(ZPLP_Token(ZPLP_Token_Type.LITERAL, value))
                            else:
                                l.tokens.append(ZPLP_Token(ZPLP_Token_Type.LITERAL, value))
                        value = ''
                    if c == '*':
                        l.tokens.append(ZPLP_Token(ZPLP_Token_Type.STAR))
                    elif c == ',':
                        l.tokens.append(ZPLP_Token(ZPLP_Token_Type.COMMA))
                    elif c == '{':
                        l.tokens.append(ZPLP_Token(ZPLP_Token_Type.OPEN_CURLY))
                    if c == '}':
                        l.tokens.append(ZPLP_Token(ZPLP_Token_Type.CLOSE_CURLY))
                    if c == ':':
                        if text[1] == ':':
                            l.tokens.append(ZPLP_Token(ZPLP_Token_Type.DOUBLE_COLON))
                            text = text[1:]
                text = text[1:]
            self.lines.append(l)

t = ZPLP_Tokenizer('./test.zplp')
t.tokenize()

for i in t.identifiers:
    print(i)
    
for line in t.lines:
    for token in line.tokens:
        print(token)