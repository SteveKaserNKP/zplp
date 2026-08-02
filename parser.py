import re
from dataclasses import dataclass, field
from enum import Enum

KEYWORDS = ['DEF', 'BEGIN_DOCUMENT', 'END_DOCUMENT', 'BEGIN_SECTION', 'END_SECTION', 'BEGIN_FIELD', 'END_FIELD', 'SETUP', 'TEXT', 'LINEAR_BARCODE_CODE39', 'GRAPHIC_BOX']
COMMANDS = ['DPMM', 'DIMENSIONS', 'MARGINS', 'POSITION', 'FONT', 'LINEAR_BARCODE_CONFIG', 'CODE39_CONFIG', 'BOX', 'TYPE', 'VALUE']

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
class AST_Node:
    type: str                     # 'DOCUMENT', 'SECTION', 'FIELD', or 'STATEMENT'
    name: str = ''                # e.g., 'Label/Printer Setup' or 'PART NO. BLOCK'
    children: list['AST_Node'] = field(default_factory=list)
    payload: list[ZPLP_Token] = field(default_factory=list) # Holds key-value parameters

TOKEN_SPECIFICATION = [
    ('DOUBLE_COLON', r'::'),
    ('STAR',         r'\*'),
    ('COMMA',        r','),
    ('OPEN_CURLY',   r'\{'),
    ('CLOSE_CURLY',  r'\}'),
    ('QUOTED_STR',   r'"[^"\\]*(?:\\.[^"\\]*)*"'),
    ('BRACKET_TEXT', r'(?<=\{)[^}:]+|(?<=::)[^}]+(?=\})'),
    ('UNQUOTED_STR', r'(?<=::)[^{}\n\r]+'),
    ('WORD',         r'[a-zA-Z0-9_\./\(\)\-]+'),
]

MASTER_REGEX = re.compile('|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPECIFICATION))

@dataclass
class ZPLP_Tokenizer:
    file_path: str
    file_lines: list[str] = field(default_factory=list)
    lines: list[ZPLP_Line] = field(default_factory=list)
    identifiers: dict[str,list[str]] = field(default_factory=dict)

    def __post_init__(self):
        with open(self.file_path, 'r') as f:
            self.file_lines = f.readlines()

    def tokenize(self) -> None:
        # Ensure self.identifiers is initialized as a dict (e.g., self.identifiers = {})
        for i, line_text in enumerate(self.file_lines):
            l = ZPLP_Line(i + 1, line_text)
            stripped = line_text.strip()
            
            if stripped.startswith("//") or not stripped:
                self.lines.append(l)
                continue

            current_def_identifier = None  # Track the active DEF key on this specific line

            # Run a single parsing pass over the entire raw line
            for match in MASTER_REGEX.finditer(line_text):
                kind = match.lastgroup
                val = match.group(kind).strip()
                if not val:
                    continue
                
                if kind == 'DOUBLE_COLON':
                    l.tokens.append(ZPLP_Token(ZPLP_Token_Type.DOUBLE_COLON, '::'))
                elif kind == 'STAR':
                    l.tokens.append(ZPLP_Token(ZPLP_Token_Type.STAR, val))
                elif kind == 'COMMA':
                    l.tokens.append(ZPLP_Token(ZPLP_Token_Type.COMMA, val))
                elif kind == 'OPEN_CURLY':
                    l.tokens.append(ZPLP_Token(ZPLP_Token_Type.OPEN_CURLY, '{'))
                elif kind == 'CLOSE_CURLY':
                    l.tokens.append(ZPLP_Token(ZPLP_Token_Type.CLOSE_CURLY, '}'))
                elif kind == 'QUOTED_STR':
                    l.tokens.append(ZPLP_Token(ZPLP_Token_Type.LITERAL, val[1:-1]))
                elif kind == 'UNQUOTED_STR' or kind == 'BRACKET_TEXT':
                    l.tokens.append(ZPLP_Token(ZPLP_Token_Type.LITERAL, val))
                    # Capture unquoted text payloads if we are currently building a DEF rule
                    if current_def_identifier:
                        self.identifiers[current_def_identifier] = val
                elif kind == 'WORD':
                    if val in KEYWORDS:
                        l.tokens.append(ZPLP_Token(ZPLP_Token_Type.KEYWORD, val))
                    elif val in COMMANDS:
                        l.tokens.append(ZPLP_Token(ZPLP_Token_Type.COMMAND, val))
                    else:
                        if len(l.tokens) > 0 and l.tokens[-1].value == 'DEF':
                            if val in self.identifiers:
                                raise ValueError(f"Identifier {val} already assigned!")
                            
                            # Initialize the dictionary key mapping
                            self.identifiers[val] = [] 
                            current_def_identifier = val  # Lock the state machine to this key
                            l.tokens.append(ZPLP_Token(ZPLP_Token_Type.IDENTIFIER, val))
                        elif len(l.tokens) > 0 and l.tokens[-1].type == ZPLP_Token_Type.STAR:
                            l.tokens.append(ZPLP_Token(ZPLP_Token_Type.IDENTIFIER, val))
                        else:
                            l.tokens.append(ZPLP_Token(ZPLP_Token_Type.LITERAL, val))
                            # Fallback capture if your master regex groups configuration arrays under WORD
                            if current_def_identifier:
                                self.identifiers[current_def_identifier].append(val)

            self.lines.append(l)

class ZPLP_Parser:
    def __init__(self, lines: list[ZPLP_Line]):
        self.lines = lines
        self.root = AST_Node(type='ROOT')
        self.stack = [self.root]

    def parse(self) -> AST_Node:
        for line in self.lines:
            # Skip empty lines or lines without tokens
            if not line.tokens:
                continue

            first_token = line.tokens[0]

            # Case A: Handling Block Structural Openers
            if first_token.type == ZPLP_Token_Type.KEYWORD and first_token.value.startswith('BEGIN_'):
                block_type = first_token.value.split('_')[1] # DOCUMENT, SECTION, or FIELD
                block_name = ''

                # VALIDATION BLOCK: Prevent nested fields
                if block_type == 'FIELD' and self.stack[-1].type == 'FIELD':
                    raise SyntaxError(
                        f"Line {line.number}: Nesting error! "
                        f"Cannot open a new BEGIN_FIELD inside an unclosed FIELD block."
                    )

                # Extract the trailing descriptive name if a double colon exists
                if len(line.tokens) > 2 and line.tokens[1].type == ZPLP_Token_Type.DOUBLE_COLON:
                    block_name = line.tokens[2].value

                # Create the node and link it to the current active parent container
                new_node = AST_Node(type=block_type, name=block_name)
                self.stack[-1].children.append(new_node)
                self.stack.append(new_node) # Push onto stack as the new active scope

            # Case B: Handling Block Structural Closures
            elif first_token.type == ZPLP_Token_Type.KEYWORD and first_token.value.startswith('END_'):
                expected_type = first_token.value.split('_')[1]
                
                # Structural Validation: Catch mismatched closures
                if self.stack[-1].type != expected_type:
                    raise SyntaxError(
                        f"Line {line.number}: Mismatched block closure! "
                        f"Found END_{expected_type}, but expected END_{self.stack[-1].type}."
                    )
                
                self.stack.pop() # Safely step out of the current scope

            # Case C: Handling Standard Body Variables & Configurations (Statements)
            else:
                statement_node = AST_Node(type='STATEMENT', payload=line.tokens)
                self.stack[-1].children.append(statement_node)

        # Final Validation: Verify all scopes closed cleanly
        if len(self.stack) > 1:
            raise SyntaxError(f"Compilation Error: The following blocks were never closed: {[n.type for n in self.stack[1:]]}")

        return self.root

class ZPL_Generator:
    def __init__(self, root: AST_Node, identifiers: dict[str,str]):
        self.root = root
        self.identifiers = identifiers
        self.zpl_buffer = []

    def generate(self) -> str:
        self._walk(self.root)
        return "\n".join(self.zpl_buffer)

    def _walk(self, node: AST_Node):
        # 1. Document Wrappers
        if node.type == 'DOCUMENT':
            self.zpl_buffer.append("^XA") # Start of Format command
            for child in node.children:
                self._walk(child)
            self.zpl_buffer.append("^XZ") # End of Format command

        # 2. Sections (Act as logical groupings, pass through to children)
        elif node.type == 'SECTION':
            for child in node.children:
                self._walk(child)

        # 3. Fields (Evaluate internal parameter statements)
        elif node.type == 'FIELD':
            field_data = self._evaluate_field(node.children)
            if field_data:
                self.zpl_buffer.append(field_data)

        # Root passthrough
        elif node.type == 'ROOT':
            for child in node.children:
                self._walk(child)

    def _evaluate_field(self, statements: list[AST_Node]) -> str:
        field_buffer = []
        args = []
        for stmt in statements:
            key = stmt.payload[0].value
            value_tokens = stmt.payload[1:]
            #print(f'KEY: {key}: \n\t{value_tokens}')
            if key == 'TYPE' and value_tokens:
                if value_tokens[0].value == 'TEXT':
                    field_buffer.append('^FT')
                elif value_tokens[0].value == 'SETUP':
                    statements = statements[1:]
                    return self._evaluate_setup_field(statements)
                else:
                    field_buffer.append('^FO')
            elif key in ['POSITION', 'FONT'] and value_tokens:
                if key == 'FONT':
                    field_buffer.append('^A')
                for token in value_tokens:
                    if token.type == ZPLP_Token_Type.COMMA:
                        continue
                    if token.type == ZPLP_Token_Type.STAR:
                        continue
                    elif token.type == ZPLP_Token_Type.IDENTIFIER:
                        if token.value not in self.identifiers:
                            raise ValueError(f'Could not find {token.value} in the identfiers dictionary!')
                        for arg in self.identifiers[token.value]:
                            args.append(arg)
                    else:
                        args.append(token.value)
                if len(args):
                    field_buffer[-1] += ','.join(args)
                    args = []
        field_buffer.append('^FS')
        return '\n'.join(field_buffer)

    def _evaluate_setup_field(self, statements: list[AST_node]) -> str:
        args = []
        dpmm = 8
        x_dim = 0
        y_dim = 0
        top = 0
        right = 0
        bottom = 0
        left = 0
        for stmt in statements:
            key = stmt.payload[0].value
            value_tokens = stmt.payload[1:]
            if key == 'DPMM':
                value = int(value_tokens[0].value)
                if value not in [6, 8, 12, 24]:
                    raise ValueError(f'DPMM value is not valid {value}')
                dpmm = value
            elif key in ['DIMENSIONS','MARGINS']:
                for token in value_tokens:
                    if token.type in [ZPLP_Token_Type.COMMA, ZPLP_Token_Type.STAR]:
                        continue
                    elif token.type == ZPLP_Token_Type.IDENTIFIER:
                        if token.value not in self.identifiers:
                            raise ValueError(f'Could not find {token.value} in the identfiers dictionary!')
                        for arg in self.identifiers[token.value]:
                            args.append(arg)
                    else:
                        args.append(token.value)
                if key == 'DIMENSIONS':
                    if len(args) != 2:
                        raise ValueError(f'Expected for DIMENSIONS command to have 2 arguments but found {len(args)}!')
                    x_dim = int(args[0])
                    y_dim = int(args[1])
                    args = []
                else:
                    if len(args) != 4:
                        raise ValueError(f'Expected for MARGINS command to have 4 arguments but found {len(args)}!')
                    top = int(args[0])
                    right = int(args[1])
                    bottom = int(args[2])
                    left = int(args[3])
                    args = []
            else:
                raise ValueError(f'Unhandled SETUP command: {key}')

        pw = (x_dim - (right+left)) * dpmm
        ll = (y_dim - (top+bottom)) * dpmm
        x = int(left * dpmm)
        y = int(top * dpmm)
        commands = []
        commands.append(f'^PW{pw}')
        commands.append(f'^LL{ll}')
        commands.append(f'^LH{x},{y}')
        return '\n'.join(commands)
                

def print_ast(node: AST_Node, indent: int = 0):
    spacing = "    " * indent
    if node.type == 'ROOT':
        print("AST ROOT")
    elif node.type in ['DOCUMENT', 'SECTION', 'FIELD']:
        name_str = f" ('{node.name}')" if node.name else ""
        print(f"{spacing}└── [{node.type}]{name_str}")
    elif node.type == 'STATEMENT':
        token_strs = [f"{t.value if t.value else t.type.name}" for t in node.payload]
        print(f"{spacing}├── STATEMENT: {' '.join(token_strs)}")
        
    for child in node.children:
        print_ast(child, indent + 1)

def print_tokenizer(t: ZPLP_Tokenizer):
    for line in t.lines:
        print(f"{line.number}:")
        for token in line.tokens:
            print(f"\t{token.type} => {token.value}")

# Execution Pipeline Execution Bridge
tokenizer = ZPLP_Tokenizer('./test.zplp')
tokenizer.tokenize()

parser = ZPLP_Parser(tokenizer.lines)
abstract_tree = parser.parse()

# Print the final compiled hierarchical outline
#print_ast(abstract_tree)

#print_tokenizer(tokenizer)

generator = ZPL_Generator(abstract_tree, tokenizer.identifiers)
zpl = generator.generate()
print(zpl)

