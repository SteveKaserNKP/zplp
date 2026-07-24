from utils import *

def lex_file(fp: Path) -> Lexer:
    lex = Lexer(fp)
    lines = get_file_data(fp)
    for i, line in enumerate(lines):
        line = line.strip()
        if len(line) == 0:
            continue
        if line.startswith("DEF"):
            _, var, value = line.split(" ")
            lex.lines.append(Def_Line(Line_Type.DEF, line, i+1, var, value))
        elif line.startswith("BEGIN_"):
            if line.startswith("BEGIN_DOCUMENT"):
                block_type = Block_Type.DOCUMENT
            elif line.startswith("BEGIN_SECTION"):
                block_type = Block_Type.SECTION
            elif line.startswith("BEGIN_FIELD"):
                block_type = Block_Type.FIELD
            else:
                raise ValueError("Unhandled block type: %1", line)
            label = ""
            if ":" in line:
                label = ''.join(line.split(":")[1:])
            lex.lines.append(Block_Begin_Line(Line_Type.BLOCK_BEGIN, line, i+1, block_type, label))
        elif line.startswith("END_"):
            if line.startswith("END_DOCUMENT"):
                block_type = Block_Type.DOCUMENT
            elif line.startswith("END_SECTION"):
                block_type = Block_Type.SECTION
            elif line.startswith("END_FIELD"):
                block_type = Block_Type.FIELD
            else:
                raise ValueError("Unhandled block type: %1", line)
            label = ""
            if ":" in line:
                label = ''.join(line.split(":")[1:])
            lex.lines.append(Block_End_Line(Line_Type.BLOCK_END, line, i+1, block_type, label))
        elif line.startswith("//"):
            lex.lines.append(Line(Line_Type.COMMENT, line, i+1))
        else:
            first_space = line.index(" ")
            param = line[0:first_space]
            value = line[first_space+1:]
            lex.lines.append(Parameter_Line(Line_Type.PARAMETER, line, i+1, param, value))

    return lex